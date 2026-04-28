"""
Tests for the agentic tool-using loop (observe-act-inspect-review).

Covers:
  - Full loop with a mock LLM that terminates after one tool call.
  - Loop that reaches max_steps without a terminal review.
  - Tool error handling in the INSPECT phase.
  - Review verdict "terminate" stops the loop early.
  - Phase event ordering: observe → act → tool_result → inspect → review.
"""

from __future__ import annotations

import asyncio
import pytest
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _collect(coro_or_gen):
    """Collect all events from an async generator into a list."""
    async def _run():
        return [e async for e in coro_or_gen]
    return asyncio.get_event_loop().run_until_complete(_run())


def _make_llm(responses: List[Dict[str, Any]]):
    """Return a mock LLM that pops responses in order."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_loop_emits_observe_act_inspect_review_then_final():
    """Happy path: one tool call, then LLM terminates."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([
        # ACT step 0: call a tool
        {"thought": "I'll check the files", "tool_call": {"name": "list_files", "args": {"directory": "."}}},
        # REVIEW step 0: terminate
        {"final": '{"verdict": "terminate", "reasoning": "Goal achieved."}'},
    ])
    tools = {"list_files": _make_tool({"entries": [], "count": 0})}

    events = _collect(agentic_tool_stream("list the files", tools=tools, llm=llm, max_steps=4))
    types = [e["type"] for e in events]

    assert "observe" in types
    assert "act" in types
    assert "tool_result" in types
    assert "inspect" in types
    assert "review" in types
    assert types[-1] == "final"


def test_loop_terminates_on_final_answer_without_tool_call():
    """If the LLM returns a final answer in ACT (no tool_call), loop ends immediately."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([
        {"thought": "I know the answer", "final": "The answer is 42."},
    ])

    events = _collect(agentic_tool_stream("what is the answer?", tools={}, llm=llm, max_steps=4))
    types = [e["type"] for e in events]

    assert types[0] == "observe"
    assert types[-1] == "final"
    final = events[-1]
    assert "42" in final["content"]
    assert final["iterations"] == 1


def test_loop_reaches_max_steps():
    """Loop emits a final event with note='max_steps reached' when steps are exhausted."""
    from services.agentic_tool_loop import agentic_tool_stream

    # LLM always calls a tool, review always says continue.
    llm = _make_llm([
        {"thought": "step", "tool_call": {"name": "noop", "args": {}}},
        {"final": '{"verdict": "continue", "reasoning": "keep going"}'},
        {"thought": "step", "tool_call": {"name": "noop", "args": {}}},
        {"final": '{"verdict": "continue", "reasoning": "keep going"}'},
        {"thought": "step", "tool_call": {"name": "noop", "args": {}}},
        {"final": '{"verdict": "continue", "reasoning": "keep going"}'},
    ])
    tools = {"noop": _make_tool({"ok": True})}

    events = _collect(agentic_tool_stream("run forever", tools=tools, llm=llm, max_steps=3))
    final = events[-1]

    assert final["type"] == "final"
    assert final.get("note") == "max_steps reached without terminal review"
    assert final["iterations"] == 3


def test_loop_handles_tool_error_gracefully():
    """A tool that raises an exception produces a tool_result with ok=False."""
    from services.agentic_tool_loop import agentic_tool_stream

    async def _failing_tool(name, args):
        raise ValueError("disk full")

    llm = _make_llm([
        {"thought": "try tool", "tool_call": {"name": "bad_tool", "args": {}}},
        {"final": "done"},
    ])
    tools = {"bad_tool": _failing_tool}

    events = _collect(agentic_tool_stream("do something", tools=tools, llm=llm, max_steps=4))
    tool_results = [e for e in events if e["type"] == "tool_result"]

    assert len(tool_results) == 1
    assert tool_results[0]["ok"] is False
    assert "disk full" in str(tool_results[0]["result"])


def test_loop_handles_unknown_tool():
    """Calling an unknown tool produces a tool_result with ok=False and an error message."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([
        {"thought": "try unknown", "tool_call": {"name": "ghost_tool", "args": {}}},
        {"final": "done"},
    ])

    events = _collect(agentic_tool_stream("use ghost tool", tools={}, llm=llm, max_steps=4))
    tool_results = [e for e in events if e["type"] == "tool_result"]

    assert len(tool_results) == 1
    assert tool_results[0]["ok"] is False
    assert "unknown tool" in str(tool_results[0]["result"])


def test_loop_review_terminate_stops_early():
    """A 'terminate' verdict in REVIEW stops the loop before max_steps."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([
        # step 0 ACT: call tool
        {"thought": "check", "tool_call": {"name": "inspect_runtime", "args": {}}},
        # step 0 REVIEW: terminate immediately
        {"final": '{"verdict": "terminate", "reasoning": "All done."}'},
    ])
    tools = {"inspect_runtime": _make_tool({"active_tasks": [], "recent_events": []})}

    events = _collect(agentic_tool_stream("inspect and stop", tools=tools, llm=llm, max_steps=10))
    final = events[-1]

    assert final["type"] == "final"
    # Should have terminated after step 0, not run all 10 steps.
    assert final["iterations"] == 1


def test_loop_event_ordering_per_step():
    """Within each step, events must appear in observe→act→tool_result→inspect→review order."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([
        {"thought": "go", "tool_call": {"name": "noop", "args": {}}},
        {"final": '{"verdict": "terminate", "reasoning": "done"}'},
    ])
    tools = {"noop": _make_tool({"ok": True})}

    events = _collect(agentic_tool_stream("ordered test", tools=tools, llm=llm, max_steps=4))
    step0 = [e for e in events if e.get("step") == 0]
    step0_types = [e["type"] for e in step0]

    expected_order = ["observe", "act", "tool_result", "inspect", "review"]
    for expected, actual in zip(expected_order, step0_types):
        assert actual == expected, f"Expected {expected!r} but got {actual!r} in {step0_types}"


def test_loop_run_id_propagated():
    """The run_id passed in appears in the final event."""
    from services.agentic_tool_loop import agentic_tool_stream

    llm = _make_llm([{"final": "done"}])
    events = _collect(agentic_tool_stream("test run_id", tools={}, llm=llm, run_id="test-run-42"))
    final = events[-1]

    assert final["type"] == "final"
    assert final.get("run_id") == "test-run-42"


def test_inspect_phase_updates_memory():
    """INSPECT phase should persist scalar values from tool results into memory."""
    from services.agentic_tool_loop import _phase_inspect

    async def _run():
        memory: dict = {}
        findings = await _phase_inspect(
            step=0,
            tool_name="read_file",
            tool_result={"path": "foo.py", "size": 1234, "content": "x" * 100},
            memory=memory,
        )
        return findings, memory

    findings, memory = asyncio.get_event_loop().run_until_complete(_run())

    assert findings["ok"] is True
    assert findings["action"] == "continue"
    # Scalar values should be in memory.
    assert memory.get("step_0_size") == 1234
    assert memory.get("step_0_path") == "foo.py"


def test_inspect_phase_error_result():
    """INSPECT phase marks action as retry_or_pivot when tool result contains an error."""
    from services.agentic_tool_loop import _phase_inspect

    async def _run():
        memory: dict = {}
        findings = await _phase_inspect(
            step=1,
            tool_name="bad_tool",
            tool_result={"error": "not found"},
            memory=memory,
        )
        return findings

    findings = asyncio.get_event_loop().run_until_complete(_run())

    assert findings["ok"] is False
    assert findings["action"] == "retry_or_pivot"
    assert findings["error"] == "not found"
