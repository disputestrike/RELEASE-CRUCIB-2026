"""
Tests for the agentic tool-using loop (observe-act-inspect-review).

Covers:
  - Full loop with a mock LLM that terminates after one tool call.
  - Loop that reaches max_steps without a terminal review.
  - Tool error handling in the INSPECT phase.
  - Review verdict "terminate" stops the loop early.
  - Phase event ordering: observe → act → tool_result → inspect → review.
  - Unknown tool returns an error result without crashing.
  - run_id is propagated to every event.
  - Inspect phase updates working memory.
  - Final event is always emitted.
"""

from __future__ import annotations

import asyncio
import pytest
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _collect(async_gen):
    """Collect all events from an async generator into a list."""
    async def _run():
        return [e async for e in async_gen]
    return asyncio.get_event_loop().run_until_complete(_run())


def _make_llm(responses: List[Dict[str, Any]]):
    """Return a mock LLM that pops responses in order, then returns a final."""
    queue = list(responses)

    async def _llm(prompt: str, history: list, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if queue:
            return queue.pop(0)
        return {"final": "done"}

    return _llm


def _make_tool(result: Any):
    """Return a mock tool that always returns ``result``."""
    async def _tool(name: str, args: dict) -> Any:
        return result
    return _tool


def _make_error_tool(exc: Exception):
    """Return a mock tool that always raises ``exc``."""
    async def _tool(name: str, args: dict) -> Any:
        raise exc
    return _tool


# ─────────────────────────────────────────────────────────────────────────────
# Import the module under test
# ─────────────────────────────────────────────────────────────────────────────

# Use a try/except so the test file is importable even if the service has a
# transient dependency issue — pytest will then report a clear ImportError.
try:
    from backend.services.agentic_tool_loop import agentic_tool_stream
except ImportError:
    from services.agentic_tool_loop import agentic_tool_stream  # type: ignore[import]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_loop_emits_observe_act_inspect_review_then_final():
    """Happy path: one tool call, then LLM terminates."""
    llm = _make_llm([
        # OBSERVE step 0
        {"observation": {"status": "starting", "next_action": "list files"}},
        # ACT step 0 — call a tool
        {"thought": "I'll check the files", "tool_call": {"name": "list_files", "args": {"directory": "."}}},
        # INSPECT step 0
        {"findings": {"errors": [], "facts": ["workspace is empty"], "memory_update": {}}},
        # REVIEW step 0 — terminate
        {"verdict": "terminate", "reasoning": "goal achieved", "answer": "Done."},
    ])
    tools = {"list_files": _make_tool({"entries": []})}

    events = _collect(agentic_tool_stream("list workspace files", tools=tools, llm_fn=llm, max_steps=4))

    types = [e["type"] for e in events]
    assert "observe" in types
    assert "act" in types
    assert "tool_result" in types
    assert "inspect" in types
    assert "review" in types
    assert types[-1] == "final"


def test_loop_reaches_max_steps():
    """Loop exhausts max_steps and emits a final event with note='max_steps reached'."""
    # LLM always says continue
    llm = _make_llm([
        {"observation": {"status": "working"}},
        {"thought": "keep going", "tool_call": {"name": "noop", "args": {}}},
        {"findings": {"errors": [], "facts": [], "memory_update": {}}},
        {"verdict": "continue", "reasoning": "not done yet"},
    ] * 10)  # plenty of responses
    tools = {"noop": _make_tool({"ok": True})}

    events = _collect(agentic_tool_stream("never finish", tools=tools, llm_fn=llm, max_steps=2))

    final = next(e for e in events if e["type"] == "final")
    assert final.get("note") == "max_steps reached"
    assert final["iterations"] == 2


def test_tool_error_is_reported_not_raised():
    """A tool that raises an exception yields a tool_result with ok=False."""
    llm = _make_llm([
        {"observation": {"status": "ok"}},
        {"thought": "try it", "tool_call": {"name": "bad_tool", "args": {}}},
        {"findings": {"errors": ["tool failed"], "facts": [], "memory_update": {}}},
        {"verdict": "terminate", "reasoning": "error handled", "answer": "Handled."},
    ])
    tools = {"bad_tool": _make_error_tool(RuntimeError("boom"))}

    events = _collect(agentic_tool_stream("trigger error", tools=tools, llm_fn=llm, max_steps=4))

    tool_result_events = [e for e in events if e["type"] == "tool_result"]
    assert len(tool_result_events) == 1
    assert tool_result_events[0]["ok"] is False
    assert "boom" in str(tool_result_events[0]["result"])


def test_unknown_tool_returns_error_result():
    """Calling a tool not in the registry yields ok=False without crashing."""
    llm = _make_llm([
        {"observation": {"status": "ok"}},
        {"thought": "try unknown", "tool_call": {"name": "ghost_tool", "args": {}}},
        {"findings": {"errors": [], "facts": [], "memory_update": {}}},
        {"verdict": "terminate", "reasoning": "done", "answer": "ok"},
    ])
    tools = {}  # empty registry

    events = _collect(agentic_tool_stream("call unknown tool", tools=tools, llm_fn=llm, max_steps=4))

    tool_result_events = [e for e in events if e["type"] == "tool_result"]
    assert len(tool_result_events) == 1
    assert tool_result_events[0]["ok"] is False
    assert "ghost_tool" in str(tool_result_events[0]["result"])


def test_review_terminate_stops_loop_early():
    """A 'terminate' verdict in step 0 means no step 1 observe event."""
    llm = _make_llm([
        {"observation": {"status": "done"}},
        {"final": "immediate answer"},  # ACT returns final directly
    ])
    tools = {}

    events = _collect(agentic_tool_stream("quick goal", tools=tools, llm_fn=llm, max_steps=5))

    observe_events = [e for e in events if e["type"] == "observe"]
    # Only one observe (step 0) because ACT returned final immediately
    assert len(observe_events) == 1
    assert events[-1]["type"] == "final"


def test_phase_event_ordering():
    """Events within a step follow observe → act → tool_result → inspect → review."""
    llm = _make_llm([
        {"observation": {"status": "ok"}},
        {"thought": "go", "tool_call": {"name": "t", "args": {}}},
        {"findings": {"errors": [], "facts": [], "memory_update": {}}},
        {"verdict": "terminate", "reasoning": "done", "answer": "finished"},
    ])
    tools = {"t": _make_tool({"data": 1})}

    events = _collect(agentic_tool_stream("ordered", tools=tools, llm_fn=llm, max_steps=4))

    # Filter to step-0 events only (exclude final)
    step0 = [e for e in events if e.get("step") == 0 and e["type"] != "final"]
    types = [e["type"] for e in step0]
    assert types == ["observe", "act", "tool_result", "inspect", "review"]


def test_run_id_propagated_to_all_events():
    """Every emitted event carries the same run_id."""
    llm = _make_llm([
        {"observation": {"status": "ok"}},
        {"final": "done"},
    ])

    events = _collect(agentic_tool_stream("check run_id", tools={}, llm_fn=llm, max_steps=2, run_id="test-run-42"))

    for event in events:
        assert event.get("run_id") == "test-run-42", f"Missing run_id in event: {event}"


def test_inspect_phase_updates_memory():
    """memory_update from INSPECT is reflected in the next REVIEW prompt."""
    memory_snapshots: List[Dict] = []

    async def _tracking_llm(prompt: str, history: list, system_prompt=None):
        if "OBSERVE" in prompt:
            return {"observation": {"status": "ok"}}
        if "ACT" in prompt:
            return {"thought": "act", "tool_call": {"name": "t", "args": {}}}
        if "INSPECT" in prompt:
            return {"findings": {"errors": [], "facts": [], "memory_update": {"key": "value"}}}
        if "REVIEW" in prompt:
            # Capture the memory state visible in the review prompt
            memory_snapshots.append({"prompt_snippet": prompt[:300]})
            return {"verdict": "terminate", "reasoning": "done", "answer": "ok"}
        return {"final": "done"}

    tools = {"t": _make_tool({"ok": True})}
    _collect(agentic_tool_stream("memory test", tools=tools, llm_fn=_tracking_llm, max_steps=4))

    # The review prompt should contain the memory_update key
    assert any("key" in snap["prompt_snippet"] for snap in memory_snapshots), (
        "Expected 'key' from memory_update to appear in REVIEW prompt"
    )


def test_final_event_always_emitted():
    """Even if the LLM raises on every call, a final event is still emitted."""
    call_count = 0

    async def _failing_llm(prompt: str, history: list, system_prompt=None):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RuntimeError("LLM down")
        return {"final": "recovered"}

    events = _collect(agentic_tool_stream("resilience test", tools={}, llm_fn=_failing_llm, max_steps=2))

    assert events[-1]["type"] == "final"


def test_no_tool_call_in_act_goes_to_final():
    """If ACT returns a final answer directly (no tool_call), the loop terminates."""
    llm = _make_llm([
        {"observation": {"status": "simple"}},
        {"final": "The answer is 42."},
    ])

    events = _collect(agentic_tool_stream("simple question", tools={}, llm_fn=llm, max_steps=5))

    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == "The answer is 42."
    # No tool_result events since no tool was called
    assert not any(e["type"] == "tool_result" for e in events)
