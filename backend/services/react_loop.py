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
import json
import os
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

from openai import AsyncOpenAI

# Configure OpenAI client to use local/compatible API
client = AsyncOpenAI(
    base_url=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY"),
)

ToolCall = Callable[[str, Dict[str, Any]], Awaitable[Any]]
LlmCall = Callable[[str, List[Dict[str, Any]]], Awaitable[Dict[str, Any]]]


async def _openai_llm_call(prompt: str, history: List[Dict[str, Any]], system_prompt: Optional[str] = None, tools: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for h in history:
        if "tool" in h:
            messages.append({"role": "tool", "tool_call_id": h["tool_call_id"], "content": json.dumps(h["result"])})
        else:
            messages.append({"role": "user", "content": h["prompt"]})
    messages.append({"role": "user", "content": prompt})

    tool_specs = []
    if tools:
        for tool_name, tool_func in tools.items():
            tool_specs.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_func.__doc__,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query"},
                            "max_results": {"type": "integer", "description": "Maximum number of search results"},
                        },
                        "required": ["query"],
                    },
                },
            })

    try:
        response = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
            messages=messages,
            tools=tool_specs if tool_specs else None,
            tool_choice="auto" if tool_specs else None,
            stream=False,
        )

        choice = response.choices[0].message
        if choice.tool_calls:
            tool_call = choice.tool_calls[0]
            return {
                "thought": choice.content or "Calling tool",
                "tool_call": {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "args": json.loads(tool_call.function.arguments),
                },
            }
        else:
            return {"final": choice.content}
    except Exception as e:
        return {"final": f"Error calling LLM: {e}"}


async def react_stream(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    tools: Optional[Dict[str, ToolCall]] = None,
    llm_call: Optional[LlmCall] = None,
    thinking_budget: int = 8000,
    max_steps: int = 6,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive a ReAct loop, yielding structured events."""
    tools = tools or {}
    llm_call = llm_call or _openai_llm_call
    history: List[Dict[str, Any]] = []
    # Pass system_prompt and tools to the llm_call if it's our default
    if llm_call == _openai_llm_call:
        _llm_call_with_context = lambda p, h: _openai_llm_call(p, h, system_prompt, tools)
    else:
        _llm_call_with_context = llm_call

    used = 0
    t0 = time.monotonic()

    for step in range(max_steps):
        turn = await _llm_call_with_context(prompt, history)
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
            history.append({"tool": name, "args": args, "result": result, "tool_call_id": call_id})
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
