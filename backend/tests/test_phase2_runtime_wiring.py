from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.runtime.context_manager import runtime_context_manager
from services.runtime.spawn_engine import spawn_engine
from services.runtime.runtime_engine import RuntimeEngine, ExecutionContext


def test_runtime_context_manager_persists_and_loads_snapshot():
    context = SimpleNamespace(
        project_id="runtime-test-user",
        user_id="test-user",
        memory={},
        executed_steps=[{"id": 1}],
        depth=1,
        cancelled=False,
        pause_requested=False,
        cost_used=0.0,
    )

    snapshot = runtime_context_manager.update_from_step(
        context=context,
        task_id="task-phase2-1",
        step_id="task-phase2-1-step-1",
        result={"output": {"ok": True}},
    )

    assert snapshot["task_id"] == "task-phase2-1"
    assert snapshot["step_id"] == "task-phase2-1-step-1"
    assert snapshot["memory"]["last_step_id"] == "task-phase2-1-step-1"

    loaded = runtime_context_manager.load_latest(
        project_id="runtime-test-user",
        task_id="task-phase2-1",
    )
    assert loaded is not None
    assert loaded["task_id"] == "task-phase2-1"


@pytest.mark.asyncio
async def test_spawn_engine_returns_none_when_spawn_not_requested():
    engine = RuntimeEngine()
    context = SimpleNamespace(project_id="p1", user_id="u1", depth=0)

    out = await spawn_engine.maybe_spawn(
        runtime_engine=engine,
        task_id="t1",
        context=context,
        decision={"spawn": False},
    )
    assert out is None


@pytest.mark.asyncio
async def test_spawn_engine_delegates_to_runtime_spawn(monkeypatch):
    engine = RuntimeEngine()
    context = SimpleNamespace(project_id="p1", user_id="u1", depth=2)

    called = {}

    async def fake_spawn_agent(**kwargs):
        called.update(kwargs)
        return {"success": True, "workspace": "x"}

    monkeypatch.setattr(engine, "spawn_agent", fake_spawn_agent)

    out = await spawn_engine.maybe_spawn(
        runtime_engine=engine,
        task_id="task-xyz",
        context=context,
        decision={
            "spawn": True,
            "spawn_agent": "WorkerAgent",
            "spawn_context": {"foo": "bar"},
            "skill": "inspect",
            "max_depth": 5,
        },
    )

    assert out is not None
    assert out["success"] is True
    assert called["agent_name"] == "WorkerAgent"
    assert called["task_id"] == "task-xyz"
    assert called["depth"] == 3
    assert called["max_depth"] == 5


@pytest.mark.asyncio
async def test_runtime_engine_update_context_phase_uses_context_manager(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase2-task", user_id="phase2-user")

    captured = {}

    def fake_update_from_step(*, context, task_id, step_id, result):
        captured["task_id"] = task_id
        captured["step_id"] = step_id
        return {"step_id": step_id}

    monkeypatch.setattr("services.runtime.runtime_engine.runtime_context_manager.update_from_step", fake_update_from_step)

    await engine._phase_update_context(
        task_id="phase2-task",
        context=context,
        result={"output": "ok"},
        step_id="phase2-task-step-1",
    )

    assert captured["task_id"] == "phase2-task"
    assert captured["step_id"] == "phase2-task-step-1"


@pytest.mark.asyncio
async def test_runtime_engine_spawn_phase_uses_spawn_engine(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase2-task", user_id="phase2-user")

    called = {"count": 0}

    async def fake_maybe_spawn(*, runtime_engine, task_id, context, decision):
        called["count"] += 1
        return {"success": True}

    monkeypatch.setattr("services.runtime.runtime_engine.spawn_engine.maybe_spawn", fake_maybe_spawn)

    await engine._phase_spawn_subagent(
        task_id="phase2-task",
        context=context,
        decision={"spawn": True, "spawn_agent": "WorkerAgent"},
        step_id="phase2-task-step-1",
    )

    assert called["count"] == 1
