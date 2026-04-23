from __future__ import annotations

import pytest

from services.runtime.runtime_engine import ExecutionContext, RuntimeEngine


@pytest.mark.asyncio
async def test_execution_loop_continues_when_decision_requests_continue(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="task-loop-1", user_id="user-loop-1")

    decisions = [
        {"action": "default", "skill": "default", "continue": True, "spawn": False},
        {"action": "default", "skill": "default", "continue": False, "spawn": False},
    ]

    async def fake_decide(*_args, **_kwargs):
        return decisions.pop(0)

    async def fake_resolve(*_args, **_kwargs):
        return "file"

    async def fake_permission(*_args, **_kwargs):
        return True

    async def fake_provider(*_args, **_kwargs):
        return {"type": "test"}

    async def fake_execute(*_args, **_kwargs):
        return {"success": True, "output": {"ok": True}, "duration_ms": 1.0}

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(engine, "_phase_decide", fake_decide)
    monkeypatch.setattr(engine, "_phase_resolve_skill", fake_resolve)
    monkeypatch.setattr(engine, "_phase_check_permission", fake_permission)
    monkeypatch.setattr(engine, "_phase_select_provider", fake_provider)
    monkeypatch.setattr(engine, "_phase_execute", fake_execute)
    monkeypatch.setattr(engine, "_phase_update_memory", noop)
    monkeypatch.setattr(engine, "_phase_update_context", noop)
    monkeypatch.setattr(engine, "_phase_spawn_subagent", noop)

    out = await engine._execution_loop("task-loop-1", context, "run loop")

    assert out["success"] is True
    assert out["steps"] == 2
    assert len(context.executed_steps) == 2


@pytest.mark.asyncio
async def test_execution_loop_invokes_spawn_phase_when_requested(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="task-loop-2", user_id="user-loop-2")

    async def fake_decide(*_args, **_kwargs):
        return {
            "action": "default",
            "skill": "default",
            "continue": False,
            "spawn": True,
            "spawn_agent": "WorkerAgent",
        }

    async def fake_resolve(*_args, **_kwargs):
        return "file"

    async def fake_permission(*_args, **_kwargs):
        return True

    async def fake_provider(*_args, **_kwargs):
        return {"type": "test"}

    async def fake_execute(*_args, **_kwargs):
        return {"success": True, "output": {"ok": True}, "duration_ms": 1.0}

    async def noop(*_args, **_kwargs):
        return None

    spawn_called = {"count": 0}

    async def fake_spawn(*_args, **_kwargs):
        spawn_called["count"] += 1
        return None

    monkeypatch.setattr(engine, "_phase_decide", fake_decide)
    monkeypatch.setattr(engine, "_phase_resolve_skill", fake_resolve)
    monkeypatch.setattr(engine, "_phase_check_permission", fake_permission)
    monkeypatch.setattr(engine, "_phase_select_provider", fake_provider)
    monkeypatch.setattr(engine, "_phase_execute", fake_execute)
    monkeypatch.setattr(engine, "_phase_update_memory", noop)
    monkeypatch.setattr(engine, "_phase_update_context", noop)
    monkeypatch.setattr(engine, "_phase_spawn_subagent", fake_spawn)

    out = await engine._execution_loop("task-loop-2", context, "run loop")

    assert out["success"] is True
    assert out["steps"] == 1
    assert spawn_called["count"] == 1
