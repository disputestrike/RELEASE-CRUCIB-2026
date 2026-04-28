"""
backend/services/agentic_tool_loop.py
──────────────────────────────────────
Agentic tool-using loop: Observe → Act → Inspect → Review

This module implements a structured four-phase agentic loop that drives an LLM
through a controlled tool-using cycle.  Each iteration of the loop runs:

  1. OBSERVE  — gather context: read memory, inspect runtime state, summarise
                the current situation into a structured observation payload.
  2. ACT      — the LLM selects and calls one or more tools based on the
                observation; tool results are collected.
  3. INSPECT  — analyse the tool results: detect errors, extract key facts,
                update the working memory with new findings.
  4. REVIEW   — the LLM evaluates progress against the original goal and
                decides whether to continue (next iteration) or terminate
                with a final answer.

The loop emits structured SSE-compatible events at each phase transition so
callers can stream progress to the UI.

Event shapes
────────────
  {"type": "observe",  "step": int, "observation": dict}
  {"type": "act",      "step": int, "tool_call": dict}
  {"type": "tool_result", "step": int, "id": str, "ok": bool, "result": any}
  {"type": "inspect",  "step": int, "findings": dict}
  {"type": "review",   "step": int, "verdict": str, "reasoning": str}
  {"type": "final",    "step": int, "content": str, "tokens_used": int,
                        "elapsed_ms": int, "iterations": int}
  {"type": "error",    "step": int, "message": str}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

ToolFn = Callable[[str, Dict[str, Any]], Any]
LlmFn = Callable[[str, List[Dict[str, Any]], Optional[str]], Any]


# ─────────────────────────────────────────────────────────────────────────────
# Default LLM backend (OpenAI-compatible)
# ─────────────────────────────────────────────────────────────────────────────

async def _default_llm(
    prompt: str,
    history: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Call the configured LLM and return a structured response dict.

    Returns one of:
      {"thought": str, "tool_call": {"id": str, "name": str, "args": dict}}
      {"thought": str, "final": str}
      {"final": str}
    """
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "sk-placeholder")
        client = AsyncOpenAI(
            base_url=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
            api_key=api_key,
        )

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for h in history:
            if h.get("role") == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": h.get("tool_call_id", ""),
                    "content": json.dumps(h.get("result", {})),
                })
            else:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
            messages=messages,
            stream=False,
        )
        choice = response.choices[0].message
        content = choice.content or ""
        return {"thought": content[:200] if len(content) > 200 else content, "final": content}
    except Exception as exc:
        logger.warning("[agentic_tool_loop] LLM call failed: %s", exc)
        return {"final": f"[LLM unavailable: {exc}]"}


# ─────────────────────────────────────────────────────────────────────────────
# Phase implementations
# ─────────────────────────────────────────────────────────────────────────────

async def _phase_observe(
    *,
    step: int,
    goal: str,
    history: List[Dict[str, Any]],
    memory: Dict[str, Any],
    tools: Dict[str, ToolFn],
) -> Dict[str, Any]:
    """OBSERVE phase: build a structured snapshot of the current situation."""
    observation: Dict[str, Any] = {
        "step": step,
        "goal": goal,
        "history_length": len(history),
        "memory_keys": list(memory.keys()),
        "available_tools": list(tools.keys()),
    }

    # Attempt a lightweight runtime inspection if the tool is available.
    if "inspect_runtime" in tools:
        try:
            rt = await tools["inspect_runtime"]("inspect_runtime", {})
            observation["runtime"] = rt
        except Exception as exc:
            observation["runtime_error"] = str(exc)

    # Summarise the last tool result if present.
    if history:
        last = history[-1]
        if last.get("role") == "tool":
            observation["last_tool_result"] = last.get("result")

    return observation


async def _phase_act(
    *,
    step: int,
    goal: str,
    observation: Dict[str, Any],
    history: List[Dict[str, Any]],
    tools: Dict[str, ToolFn],
    llm: LlmFn,
    system_prompt: Optional[str],
) -> Dict[str, Any]:
    """ACT phase: ask the LLM which tool to call (or produce a final answer)."""
    act_prompt = (
        f"Goal: {goal}\n\n"
        f"Current observation (step {step}):\n{json.dumps(observation, indent=2, default=str)}\n\n"
        f"Available tools: {', '.join(tools.keys())}\n\n"
        "Decide: call a tool to make progress, or produce a final answer.\n"
        "If calling a tool, respond with JSON: "
        '{"thought": "...", "tool_call": {"name": "<tool>", "args": {...}}}\n'
        'If done, respond with JSON: {"thought": "...", "final": "<answer>"}'
    )
    turn = await llm(act_prompt, history, system_prompt)
    return turn


async def _phase_inspect(
    *,
    step: int,
    tool_name: str,
    tool_result: Any,
    memory: Dict[str, Any],
) -> Dict[str, Any]:
    """INSPECT phase: analyse tool result and update working memory."""
    findings: Dict[str, Any] = {
        "step": step,
        "tool": tool_name,
        "ok": not (isinstance(tool_result, dict) and "error" in tool_result),
    }

    if isinstance(tool_result, dict):
        if "error" in tool_result:
            findings["error"] = tool_result["error"]
            findings["action"] = "retry_or_pivot"
        else:
            findings["summary"] = {k: v for k, v in list(tool_result.items())[:5]}
            findings["action"] = "continue"
            # Persist key facts into working memory.
            for k, v in tool_result.items():
                if isinstance(v, (str, int, float, bool)):
                    memory[f"step_{step}_{k}"] = v
    else:
        findings["raw"] = str(tool_result)[:500]
        findings["action"] = "continue"

    return findings


async def _phase_review(
    *,
    step: int,
    goal: str,
    findings: Dict[str, Any],
    history: List[Dict[str, Any]],
    llm: LlmFn,
    system_prompt: Optional[str],
    max_steps: int,
) -> Dict[str, Any]:
    """REVIEW phase: evaluate progress and decide whether to continue."""
    if step >= max_steps - 1:
        return {
            "verdict": "terminate",
            "reasoning": f"Reached maximum iterations ({max_steps}).",
        }

    if findings.get("action") == "retry_or_pivot":
        return {
            "verdict": "continue",
            "reasoning": f"Tool error at step {step}; will try a different approach.",
        }

    review_prompt = (
        f"Goal: {goal}\n\n"
        f"Step {step} findings:\n{json.dumps(findings, indent=2, default=str)}\n\n"
        "Has the goal been fully achieved? "
        'Respond with JSON: {"verdict": "continue"|"terminate", "reasoning": "..."}'
    )
    try:
        turn = await llm(review_prompt, history, system_prompt)
        raw = (turn.get("final") or turn.get("thought") or "").strip()
        # Try to parse JSON from the response.
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            verdict = parsed.get("verdict", "continue")
            reasoning = parsed.get("reasoning", "")
            return {"verdict": verdict, "reasoning": reasoning}
    except Exception:
        pass

    return {"verdict": "continue", "reasoning": "Continuing by default."}


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────

async def agentic_tool_stream(
    goal: str,
    *,
    tools: Optional[Dict[str, ToolFn]] = None,
    llm: Optional[LlmFn] = None,
    system_prompt: Optional[str] = None,
    max_steps: int = 8,
    thinking_budget: int = 8000,
    run_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive the observe-act-inspect-review agentic loop, yielding events.

    Args:
        goal:           Natural-language goal for the agent.
        tools:          Dict of tool_name → async callable(name, args) → result.
        llm:            Async callable(prompt, history, system_prompt) → dict.
        system_prompt:  Optional system prompt injected into every LLM call.
        max_steps:      Maximum number of observe-act-inspect-review iterations.
        thinking_budget: Token budget hint passed through to the final event.
        run_id:         Optional run identifier for tracing.

    Yields:
        Structured event dicts (see module docstring for shapes).
    """
    from backend.services.tools import get_tools as _get_default_tools

    tools = tools if tools is not None else _get_default_tools()
    llm = llm or _default_llm
    run_id = run_id or str(uuid.uuid4())

    history: List[Dict[str, Any]] = []
    memory: Dict[str, Any] = {"run_id": run_id, "goal": goal}
    tokens_used = 0
    t0 = time.monotonic()

    logger.info("[agentic_tool_loop] run_id=%s goal=%r max_steps=%d", run_id, goal[:80], max_steps)

    for step in range(max_steps):
        # ── 1. OBSERVE ────────────────────────────────────────────────────────
        try:
            observation = await _phase_observe(
                step=step,
                goal=goal,
                history=history,
                memory=memory,
                tools=tools,
            )
        except Exception as exc:
            yield {"type": "error", "step": step, "phase": "observe", "message": str(exc)}
            break

        yield {"type": "observe", "step": step, "observation": observation}

        # ── 2. ACT ───────────────────────────────────────────────────────────
        try:
            turn = await _phase_act(
                step=step,
                goal=goal,
                observation=observation,
                history=history,
                tools=tools,
                llm=llm,
                system_prompt=system_prompt,
            )
        except Exception as exc:
            yield {"type": "error", "step": step, "phase": "act", "message": str(exc)}
            break

        thought = turn.get("thought", "")
        tokens_used += len(thought)

        # Check for final answer from ACT phase.
        if "final" in turn and not turn.get("tool_call"):
            final_content = turn["final"]
            yield {
                "type": "final",
                "step": step,
                "content": final_content,
                "tokens_used": tokens_used,
                "budget": thinking_budget,
                "iterations": step + 1,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "run_id": run_id,
            }
            return

        tc = turn.get("tool_call")
        if not tc:
            # No tool call and no final — treat as done.
            yield {
                "type": "final",
                "step": step,
                "content": thought,
                "tokens_used": tokens_used,
                "budget": thinking_budget,
                "iterations": step + 1,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "run_id": run_id,
            }
            return

        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {}) or {}
        call_id = tc.get("id") or f"tc_{step}_{uuid.uuid4().hex[:6]}"

        yield {
            "type": "act",
            "step": step,
            "thought": thought,
            "tool_call": {"id": call_id, "name": tool_name, "args": tool_args},
        }

        # Execute the tool.
        fn = tools.get(tool_name)
        if fn is None:
            tool_result: Any = {"error": f"unknown tool {tool_name!r}"}
            tool_ok = False
        else:
            try:
                tool_result = await fn(tool_name, tool_args)
                tool_ok = not (isinstance(tool_result, dict) and "error" in tool_result)
            except Exception as exc:
                tool_result = {"error": f"{type(exc).__name__}: {exc}"}
                tool_ok = False

        yield {
            "type": "tool_result",
            "step": step,
            "id": call_id,
            "name": tool_name,
            "ok": tool_ok,
            "result": tool_result,
        }

        history.append({
            "role": "tool",
            "tool_call_id": call_id,
            "result": tool_result,
        })

        # ── 3. INSPECT ───────────────────────────────────────────────────────
        try:
            findings = await _phase_inspect(
                step=step,
                tool_name=tool_name,
                tool_result=tool_result,
                memory=memory,
            )
        except Exception as exc:
            yield {"type": "error", "step": step, "phase": "inspect", "message": str(exc)}
            break

        yield {"type": "inspect", "step": step, "findings": findings}

        # ── 4. REVIEW ────────────────────────────────────────────────────────
        try:
            review = await _phase_review(
                step=step,
                goal=goal,
                findings=findings,
                history=history,
                llm=llm,
                system_prompt=system_prompt,
                max_steps=max_steps,
            )
        except Exception as exc:
            yield {"type": "error", "step": step, "phase": "review", "message": str(exc)}
            break

        yield {
            "type": "review",
            "step": step,
            "verdict": review.get("verdict", "continue"),
            "reasoning": review.get("reasoning", ""),
        }

        if review.get("verdict") == "terminate":
            # Produce a final summary from memory.
            summary = memory.get("final_answer") or f"Goal achieved after {step + 1} iteration(s)."
            yield {
                "type": "final",
                "step": step,
                "content": summary,
                "tokens_used": tokens_used,
                "budget": thinking_budget,
                "iterations": step + 1,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "run_id": run_id,
            }
            return

    # Exhausted max_steps without a terminal review.
    yield {
        "type": "final",
        "step": max_steps - 1,
        "content": "",
        "tokens_used": tokens_used,
        "budget": thinking_budget,
        "iterations": max_steps,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "run_id": run_id,
        "note": "max_steps reached without terminal review",
    }
