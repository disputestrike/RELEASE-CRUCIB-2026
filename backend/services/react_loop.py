"""
WS-B: ReAct-style reasoning loop emitting structured events.

async generator `react_stream(prompt, tools, *, thinking_budget=8000)` yields
dicts of the following shapes (same structure used by SSE endpoint):

    {"type": "thought", "content": "..."}
    {"type": "tool_call", "id": "...", "name": "...", "args": {...}}
    {"type": "tool_result", "id": "...", "ok": bool, "result": any}
    {"type": "text", "content": "..."}
    {"type": "final", "content": "...", "tokens_used": int, "budget": int}

This is a pure-Python mock loop intended to exercise the event contract
without coupling to a specific LLM vendor; real integration hooks can be
layered by passing a non-None `llm_call` coroutine with the same signature.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

ToolCall = Callable[[str, Dict[str, Any]], Awaitable[Any]]
LlmCall = Callable[[str, List[Dict[str, Any]]], Awaitable[Dict[str, Any]]]


async def _default_llm(prompt: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic stand-in for an LLM — emits a thought then a final text.

    Real callers should pass their own `llm_call`.
    """
    await asyncio.sleep(0)
    return {
        "thought": f"plan: answer '{prompt[:60]}' directly",
        "tool_call": None,
        "final": f"[stub] answer to: {prompt[:120]}",
    }


async def react_stream(
    prompt: str,
    *,
    tools: Optional[Dict[str, ToolCall]] = None,
    llm_call: Optional[LlmCall] = None,
    thinking_budget: int = 8000,
    max_steps: int = 6,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive a ReAct loop, yielding structured events."""
    tools = tools or {}
    llm_call = llm_call or _default_llm
    history: List[Dict[str, Any]] = []
    used = 0
    t0 = time.monotonic()

    for step in range(max_steps):
        turn = await llm_call(prompt, history)
        # Thinking narration
        thought = turn.get("thought")
        if thought:
            yield {"type": "thought", "content": str(thought), "step": step}
            used += len(str(thought))

        # Optional tool call
        tc = turn.get("tool_call")
        if tc:
            name = tc.get("name", "")
            args = tc.get("args", {}) or {}
            call_id = tc.get("id") or f"tc_{step}"
            yield {"type": "tool_call", "id": call_id, "name": name, "args": args}
            fn = tools.get(name)
            if fn is None:
                result = {"error": f"unknown tool {name!r}"}
                ok = False
            else:
                try:
                    result = await fn(name, args)
                    ok = True
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}
                    ok = False
            yield {"type": "tool_result", "id": call_id, "ok": ok, "result": result}
            history.append({"tool": name, "args": args, "result": result})
            continue  # let the model incorporate tool result next step

        # Final answer
        final = turn.get("final") or turn.get("text") or ""
        if final:
            yield {"type": "text", "content": str(final)}
            yield {
                "type": "final",
                "content": str(final),
                "tokens_used": used,
                "budget": thinking_budget,
                "steps": step + 1,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            }
            return

    # Exhausted steps without a final
    yield {
        "type": "final",
        "content": "",
        "tokens_used": used,
        "budget": thinking_budget,
        "steps": max_steps,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "note": "max_steps reached",
    }
