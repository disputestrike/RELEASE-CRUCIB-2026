from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_agent_loop_run_calls_runtime_engine_with_expected_contract(monkeypatch):
    from services.agent_loop import AgentLoop, ExecutionMode

    captured = {}

    class _Engine:
        async def execute_with_control(self, *, task_id, user_id, request, conversation_id=None, parent_task_id=None, progress_callback=None):
            captured["task_id"] = task_id
            captured["user_id"] = user_id
            captured["request"] = request
            captured["conversation_id"] = conversation_id
            return {"ok": True, "task_id": task_id}

    loop = AgentLoop()
    loop._engine = _Engine()

    out = await loop.run(
        mode=ExecutionMode.BUILD,
        goal="Build a health endpoint",
        user_id="u-test",
        thread_id="thread-123",
        dry_run=True,
    )

    assert out["status"] == "completed"
    assert captured["user_id"] == "u-test"
    assert captured["conversation_id"] == "thread-123"
    assert "Build a health endpoint" in captured["request"]
    assert "[RUNTIME_HINTS]" in captured["request"]


@pytest.mark.asyncio
async def test_agent_loop_control_methods_use_runtime_control_fallbacks():
    from services.agent_loop import AgentLoop

    class _Engine:
        async def cancel_task_controlled(self, run_id):
            return run_id == "run-1"

        async def pause_task_controlled(self, run_id):
            return run_id == "run-1"

        async def resume_task_controlled(self, run_id):
            return run_id == "run-1"

    loop = AgentLoop()
    loop._engine = _Engine()

    assert await loop.cancel("run-1") is True
    assert await loop.pause("run-1") is True
    resumed = await loop.resume("run-1")
    assert resumed["status"] == "resumed"

    assert await loop.cancel("run-2") is False
    assert await loop.pause("run-2") is False
    resumed2 = await loop.resume("run-2")
    assert resumed2["status"] == "not_found"


@pytest.mark.asyncio
async def test_agent_loop_invalid_mode_defaults_to_build(monkeypatch):
    from services.agent_loop import AgentLoop

    class _Engine:
        async def execute_with_control(self, *, task_id, user_id, request, conversation_id=None, parent_task_id=None, progress_callback=None):
            return {"ok": True}

    loop = AgentLoop()
    loop._engine = _Engine()

    out = await loop.run(mode="nonexistent-mode", goal="hello", user_id="u1")
    assert out["mode"] == "build"
    assert out["status"] == "completed"
