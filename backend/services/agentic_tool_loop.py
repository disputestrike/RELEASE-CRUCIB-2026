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
# LLM dispatcher (Cerebras primary → Anthropic fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _get_cerebras_key() -> Optional[str]:
    try:
        from ..cerebras_roundrobin import get_next_cerebras_key  # type: ignore[import]
        return get_next_cerebras_key()
    except Exception:
        pass
    try:
        from ..llm_router import get_cerebras_key  # type: ignore[import]
        return get_cerebras_key()
    except Exception:
        pass
    return os.environ.get("CEREBRAS_API_KEY") or None


def _get_anthropic_key() -> Optional[str]:
    return os.environ.get("ANTHROPIC_API_KEY") or None


async def _llm_call(
    prompt: str,
    history: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Cerebras (primary) → Anthropic (fallback) and return a parsed turn dict.

    Returns a dict with one of:
      {"thought": str, "tool_call": {"name": str, "args": dict, "id": str}}
      {"thought": str, "final": str}
      {"final": str}
    """
    import httpx

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    for h in history:
        messages.append(h)

    cerebras_key = _get_cerebras_key()
    if cerebras_key:
        try:
            model = (os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip()
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {cerebras_key}"},
                    json={"model": model, "messages": messages, "max_tokens": 2048},
                )
            if resp.status_code == 200:
                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                content = msg.get("content") or ""
                return _parse_llm_text(content)
        except Exception as exc:
            logger.warning("agentic_tool_loop: Cerebras failed: %s", exc)

    anthropic_key = _get_anthropic_key()
    if anthropic_key:
        try:
            model = (os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest").strip()
            clean = [m for m in messages if m["role"] in ("user", "assistant")]
            body: Dict[str, Any] = {
                "model": model,
                "max_tokens": 2048,
                "messages": clean,
            }
            if system_prompt:
                body["system"] = system_prompt
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=body,
                )
            if resp.status_code == 200:
                data = resp.json()
                blocks = data.get("content") or []
                text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
                return _parse_llm_text(text)
        except Exception as exc:
            logger.warning("agentic_tool_loop: Anthropic failed: %s", exc)

    return {"final": "[No LLM available — check API keys in Settings]"}


def _parse_llm_text(text: str) -> Dict[str, Any]:
    """Parse free-form LLM text into a structured turn dict.

    Looks for JSON blocks or structured markers; falls back to treating the
    whole response as a final answer.
    """
    text = text.strip()
    # Try to extract a JSON block
    for start_marker in ("```json", "```"):
        if start_marker in text:
            try:
                inner = text.split(start_marker, 1)[1].split("```", 1)[0].strip()
                parsed = json.loads(inner)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    # Try bare JSON
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    # Plain text → final answer
    return {"final": text}


# ─────────────────────────────────────────────────────────────────────────────
# Phase helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_observe_prompt(goal: str, memory: Dict[str, Any], step: int) -> str:
    mem_summary = json.dumps(memory, default=str)[:1000] if memory else "{}"
    return (
        f"OBSERVE phase — step {step}.\n"
        f"Goal: {goal}\n"
        f"Working memory: {mem_summary}\n\n"
        "Summarise the current situation in JSON: "
        '{"observation": {"status": "...", "next_action": "...", "context": "..."}}'
    )


def _build_act_prompt(goal: str, observation: Dict[str, Any], tools: Dict[str, ToolFn], step: int) -> str:
    tool_names = list(tools.keys())
    obs_text = json.dumps(observation, default=str)[:800]
    return (
        f"ACT phase — step {step}.\n"
        f"Goal: {goal}\n"
        f"Observation: {obs_text}\n"
        f"Available tools: {tool_names}\n\n"
        "Select a tool to call and respond in JSON:\n"
        '{"thought": "...", "tool_call": {"name": "<tool>", "args": {...}}}\n'
        "Or if no tool is needed, respond:\n"
        '{"thought": "...", "final": "<answer>"}'
    )


def _build_inspect_prompt(goal: str, tool_results: List[Dict[str, Any]], step: int) -> str:
    results_text = json.dumps(tool_results, default=str)[:1200]
    return (
        f"INSPECT phase — step {step}.\n"
        f"Goal: {goal}\n"
        f"Tool results: {results_text}\n\n"
        "Analyse the results and respond in JSON:\n"
        '{"findings": {"errors": [...], "facts": [...], "memory_update": {...}}}'
    )


def _build_review_prompt(goal: str, memory: Dict[str, Any], step: int) -> str:
    mem_text = json.dumps(memory, default=str)[:1000]
    return (
        f"REVIEW phase — step {step}.\n"
        f"Goal: {goal}\n"
        f"Current memory: {mem_text}\n\n"
        "Evaluate progress and respond in JSON:\n"
        '{"verdict": "continue" | "terminate", "reasoning": "...", "answer": "..."}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────

async def agentic_tool_stream(
    goal: str,
    *,
    tools: Optional[Dict[str, ToolFn]] = None,
    llm_fn: Optional[LlmFn] = None,
    system_prompt: Optional[str] = None,
    max_steps: int = 8,
    thinking_budget: int = 8000,
    run_id: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive the Observe → Act → Inspect → Review loop, yielding structured events.

    Args:
        goal: Natural-language goal for the agent.
        tools: Dict of tool name → async callable.  Defaults to get_tools().
        llm_fn: Optional custom LLM coroutine (prompt, history, system) → dict.
        system_prompt: Optional system prompt prepended to every LLM call.
        max_steps: Maximum loop iterations before forced termination.
        thinking_budget: Token budget hint passed to the LLM.
        run_id: Optional trace identifier included in every event.

    Yields:
        Structured event dicts (see module docstring for shapes).
    """
    if tools is None:
        try:
            from .tools import get_tools  # type: ignore[import]
            tools = get_tools()
        except Exception:
            tools = {}

    _llm = llm_fn or _llm_call
    run_id = run_id or uuid.uuid4().hex[:12]
    memory: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []
    t0 = time.monotonic()
    tokens_used = 0

    for step in range(max_steps):
        # ── OBSERVE ──────────────────────────────────────────────────────────
        try:
            obs_prompt = _build_observe_prompt(goal, memory, step)
            obs_turn = await _llm(obs_prompt, history, system_prompt)
            observation = obs_turn.get("observation") or {"status": "unknown", "next_action": "proceed"}
        except Exception as exc:
            observation = {"status": "error", "next_action": "proceed"}
            logger.warning("agentic_tool_loop observe error step %d: %s", step, exc)

        yield {"type": "observe", "step": step, "run_id": run_id, "observation": observation}

        # ── ACT ──────────────────────────────────────────────────────────────
        try:
            act_prompt = _build_act_prompt(goal, observation, tools, step)
            act_turn = await _llm(act_prompt, history, system_prompt)
        except Exception as exc:
            yield {"type": "error", "step": step, "run_id": run_id, "message": f"ACT phase error: {exc}"}
            break

        # Early termination if LLM returned a final answer in ACT phase
        if "final" in act_turn:
            final_text = act_turn["final"]
            elapsed = int((time.monotonic() - t0) * 1000)
            yield {
                "type": "final",
                "step": step,
                "run_id": run_id,
                "content": str(final_text),
                "tokens_used": tokens_used,
                "elapsed_ms": elapsed,
                "iterations": step + 1,
            }
            return

        tc = act_turn.get("tool_call") or {}
        tool_name = tc.get("name", "")
        tool_args = tc.get("args") or {}
        tool_id = tc.get("id") or f"tc_{step}_{uuid.uuid4().hex[:6]}"

        yield {
            "type": "act",
            "step": step,
            "run_id": run_id,
            "tool_call": {"id": tool_id, "name": tool_name, "args": tool_args},
        }

        # ── Execute tool ──────────────────────────────────────────────────────
        tool_results: List[Dict[str, Any]] = []
        if tool_name:
            fn = tools.get(tool_name)
            if fn is None:
                result = {"error": f"unknown tool {tool_name!r}"}
                ok = False
            else:
                try:
                    result = await fn(tool_name, tool_args)
                    ok = True
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}
                    ok = False

            yield {
                "type": "tool_result",
                "step": step,
                "run_id": run_id,
                "id": tool_id,
                "ok": ok,
                "result": result,
            }
            tool_results.append({"id": tool_id, "name": tool_name, "ok": ok, "result": result})

            # Update history
            history.append({
                "role": "assistant",
                "content": act_turn.get("thought") or "",
            })
            history.append({
                "role": "user",
                "content": f"Tool {tool_name!r} result: {json.dumps(result, default=str)[:800]}",
            })

        # ── INSPECT ───────────────────────────────────────────────────────────
        try:
            inspect_prompt = _build_inspect_prompt(goal, tool_results, step)
            inspect_turn = await _llm(inspect_prompt, history, system_prompt)
            findings = inspect_turn.get("findings") or {}
        except Exception as exc:
            findings = {"errors": [str(exc)], "facts": [], "memory_update": {}}
            logger.warning("agentic_tool_loop inspect error step %d: %s", step, exc)

        # Merge memory updates
        mem_update = findings.get("memory_update") or {}
        if isinstance(mem_update, dict):
            memory.update(mem_update)

        yield {"type": "inspect", "step": step, "run_id": run_id, "findings": findings}

        # ── REVIEW ────────────────────────────────────────────────────────────
        try:
            review_prompt = _build_review_prompt(goal, memory, step)
            review_turn = await _llm(review_prompt, history, system_prompt)
            verdict = review_turn.get("verdict", "continue")
            reasoning = review_turn.get("reasoning", "")
            answer = review_turn.get("answer", "")
        except Exception as exc:
            verdict = "continue"
            reasoning = f"Review error: {exc}"
            answer = ""
            logger.warning("agentic_tool_loop review error step %d: %s", step, exc)

        yield {
            "type": "review",
            "step": step,
            "run_id": run_id,
            "verdict": verdict,
            "reasoning": reasoning,
        }

        if verdict == "terminate":
            elapsed = int((time.monotonic() - t0) * 1000)
            yield {
                "type": "final",
                "step": step,
                "run_id": run_id,
                "content": answer or reasoning,
                "tokens_used": tokens_used,
                "elapsed_ms": elapsed,
                "iterations": step + 1,
            }
            return

    # Max steps exhausted
    elapsed = int((time.monotonic() - t0) * 1000)
    yield {
        "type": "final",
        "step": max_steps,
        "run_id": run_id,
        "content": memory.get("last_answer", ""),
        "tokens_used": tokens_used,
        "elapsed_ms": elapsed,
        "iterations": max_steps,
        "note": "max_steps reached",
    }
