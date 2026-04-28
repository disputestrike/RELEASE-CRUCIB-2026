"""
WS-B: ReAct-style reasoning loop emitting structured events.

async generator `react_stream(prompt, tools, *, thinking_budget=8000)` yields
dicts of the following shapes (same structure used by SSE endpoint):

    {"type": "thought", "content": "..."}
    {"type": "tool_call", "id": "...", "name": "...", "args": {...}}
    {"type": "tool_result", "id": "...", "ok": bool, "result": any}
    {"type": "text", "content": "..."}
    {"type": "final", "content": "...", "tokens_used": int, "budget": int}

Uses Cerebras (primary, near-zero cost) with Anthropic Claude as fallback.
No OpenAI dependency — callers may still inject a custom llm_call coroutine.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ToolCall = Callable[[str, Dict[str, Any]], Awaitable[Any]]
LlmCall = Callable[[str, List[Dict[str, Any]]], Awaitable[Dict[str, Any]]]

# ── Model defaults (overridable via env) ──────────────────────────────────────
_CEREBRAS_MODEL = (os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip()
_ANTHROPIC_MODEL = (os.environ.get("ANTHROPIC_REACT_MODEL") or "claude-haiku-4-5-20251001").strip()
_CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def _get_cerebras_key() -> Optional[str]:
    """Round-robin Cerebras key if the router is available; fall back to env."""
    try:
        from backend.llm_router import get_cerebras_key  # type: ignore
        return get_cerebras_key()
    except Exception:
        pass
    # Try round-robin module directly
    try:
        from backend.cerebras_roundrobin import get_next_cerebras_key  # type: ignore
        return get_next_cerebras_key()
    except Exception:
        pass
    return os.environ.get("CEREBRAS_API_KEY") or None


def _normalize_anthropic_model(model: str) -> str:
    try:
        from backend.anthropic_models import normalize_anthropic_model  # type: ignore
        return normalize_anthropic_model(model)
    except Exception:
        return model


def _build_tool_specs(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert {name: callable} tool map to OpenAI-compatible tool specs."""
    specs = []
    for name, fn in tools.items():
        desc = (getattr(fn, "__doc__", None) or f"Tool: {name}").strip().splitlines()[0]
        specs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Tool input / arguments as JSON string or plain text"},
                    },
                    "required": [],
                },
            },
        })
    return specs


async def _call_cerebras(
    messages: List[Dict[str, Any]],
    tool_specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Call Cerebras (OpenAI-compatible) with optional tool specs."""
    key = _get_cerebras_key()
    if not key:
        raise ValueError("No Cerebras API key available")

    body: Dict[str, Any] = {
        "model": _CEREBRAS_MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7,
    }
    if tool_specs:
        body["tools"] = tool_specs
        body["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            _CEREBRAS_API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=body,
        )
        if resp.status_code == 429:
            # Try key rotation once
            rotated = _get_cerebras_key()
            if rotated and rotated != key:
                resp2 = await client.post(
                    _CEREBRAS_API_URL,
                    headers={"Authorization": f"Bearer {rotated}"},
                    json=body,
                )
                if resp2.status_code == 200:
                    return resp2.json()
            raise ValueError(f"Cerebras rate limited (429)")
        if resp.status_code != 200:
            raise ValueError(f"Cerebras returned {resp.status_code}: {resp.text[:300]}")
        return resp.json()


async def _call_anthropic(
    messages: List[Dict[str, Any]],
    system: Optional[str],
) -> Dict[str, Any]:
    """Call Anthropic Claude as fallback (no tool-use in fallback path)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("No ANTHROPIC_API_KEY available")

    model = _normalize_anthropic_model(_ANTHROPIC_MODEL)
    # Filter to user/assistant roles only (strip system injections)
    clean: List[Dict[str, Any]] = [m for m in messages if m["role"] in ("user", "assistant")]

    body: Dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "messages": clean,
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            _ANTHROPIC_API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            json=body,
        )
        if resp.status_code != 200:
            raise ValueError(f"Anthropic returned {resp.status_code}: {resp.text[:300]}")
        return resp.json()


def _parse_cerebras_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Cerebras/OpenAI-compatible response into react_stream turn dict."""
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    finish = choice.get("finish_reason", "")

    # Tool call path
    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        tc = tool_calls[0]
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments", "{}")
        try:
            args = json.loads(raw_args)
        except Exception:
            args = {"input": raw_args}
        return {
            "thought": msg.get("content") or "Using tool…",
            "tool_call": {
                "id": tc.get("id", f"tc_{int(time.monotonic()*1000)}"),
                "name": fn.get("name", ""),
                "args": args,
            },
        }

    # Text / final path
    content = msg.get("content") or ""
    return {"final": content}


def _parse_anthropic_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Anthropic Messages API response into react_stream turn dict."""
    blocks = data.get("content") or []
    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    content = "\n".join(text_parts).strip()
    return {"final": content}


async def _crucibai_llm_call(
    messages: List[Dict[str, Any]],
    system: Optional[str],
    tool_specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Primary LLM dispatcher: Cerebras first, Anthropic fallback."""
    # ── Cerebras ──────────────────────────────────────────────────────────────
    try:
        data = await _call_cerebras(messages, tool_specs)
        return _parse_cerebras_response(data)
    except Exception as cerebras_err:
        logger.warning("react_loop: Cerebras failed (%s), falling back to Anthropic", cerebras_err)

    # ── Anthropic fallback ────────────────────────────────────────────────────
    try:
        data = await _call_anthropic(messages, system)
        return _parse_anthropic_response(data)
    except Exception as anthropic_err:
        logger.error("react_loop: Anthropic fallback also failed: %s", anthropic_err)
        return {"thought": "Processing request...", "final": f"[LLM unavailable: {anthropic_err}]"}


async def react_stream(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    tools: Optional[Dict[str, ToolCall]] = None,
    llm_call: Optional[LlmCall] = None,
    thinking_budget: int = 8000,
    max_steps: int = 6,
) -> AsyncIterator[Dict[str, Any]]:
    """Drive a ReAct loop, yielding structured events.

    Uses Cerebras (primary) → Anthropic (fallback) unless a custom llm_call
    is injected.  Event shapes match the SSE contract consumed by the frontend.
    """
    tools = tools or {}
    tool_specs = _build_tool_specs(tools)

    # Build initial message list
    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    used_chars = 0
    t0 = time.monotonic()

    for step in range(max_steps):
        # ── Call LLM ──────────────────────────────────────────────────────────
        if llm_call is not None:
            # Legacy / custom hook: keep backward-compat (prompt + history list)
            history_compat: List[Dict[str, Any]] = []
            for m in messages[1:]:  # skip system
                item: Dict[str, Any] = {"prompt": m.get("content", ""), "role": m["role"]}
                if m["role"] == "tool":
                    try:
                        item["result"] = json.loads(m.get("content", "null"))
                    except Exception:
                        item["result"] = m.get("content", "")
                history_compat.append(item)
            turn = await llm_call(prompt, history_compat)
        else:
            turn = await _crucibai_llm_call(messages, system_prompt, tool_specs)

        # ── Emit thought (if present) ──────────────────────────────────────────
        thought = turn.get("thought")
        if thought:
            yield {"type": "thought", "content": str(thought), "step": step}
            used_chars += len(str(thought))

        # ── Tool call path ─────────────────────────────────────────────────────
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

            # Feed result back into message history so model can react
            messages.append({
                "role": "assistant",
                "content": thought or "",
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result),
            })
            continue  # next step: model incorporates tool result

        # ── Final answer ───────────────────────────────────────────────────────
        final = turn.get("final") or turn.get("text") or ""
        if final:
            yield {"type": "text", "content": str(final)}
            yield {
                "type": "final",
                "content": str(final),
                "tokens_used": used_chars,
                "budget": thinking_budget,
                "steps": step + 1,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            }
            return

        # Model returned empty — treat as done
        logger.debug("react_loop: empty turn at step %d, treating as final", step)
        break

    # Exhausted max_steps without a clean final
    yield {
        "type": "final",
        "content": "",
        "tokens_used": used_chars,
        "budget": thinking_budget,
        "steps": max_steps,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "note": "max_steps reached",
    }
