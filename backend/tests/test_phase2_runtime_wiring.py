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
        result={"output": {"ok": True}, "metadata": {"skill": "build", "provider": {"alias": "haiku"}}},
    )

    assert snapshot["task_id"] == "task-phase2-1"
    assert snapshot["step_id"] == "task-phase2-1-step-1"
    assert snapshot["memory"]["last_step_id"] == "task-phase2-1-step-1"
    assert snapshot["last_skill"] == "build"
    assert snapshot["last_provider"]["alias"] == "haiku"

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
async def test_spawn_engine_returns_none_when_context_cancelled():
    engine = RuntimeEngine()
    context = SimpleNamespace(project_id="p1", user_id="u1", depth=0, cancelled=True)

    out = await spawn_engine.maybe_spawn(
        runtime_engine=engine,
        task_id="t1",
        context=context,
        decision={"spawn": True, "spawn_agent": "WorkerAgent"},
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


@pytest.mark.asyncio
async def test_phase_select_provider_returns_chain(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase2-task", user_id="phase2-user")

    monkeypatch.setattr(
        "services.runtime.runtime_engine.classifier.classify",
        lambda *_args, **_kwargs: "simple",
    )
    monkeypatch.setattr(
        "services.runtime.runtime_engine.llm_router.get_model_chain",
        lambda **_kwargs: [("haiku", "claude-haiku-4-5-20251001", "anthropic")],
    )

    out = await engine._phase_select_provider(
        task_id="phase2-task",
        context=context,
        skill="build",
        step_id="phase2-task-step-1",
    )
    assert out is not None
    assert out["alias"] == "haiku"
    assert out["type"] == "anthropic"
    assert isinstance(out["chain"], list)


@pytest.mark.asyncio
async def test_spawn_agent_blocked_when_parent_task_killed():
    engine = RuntimeEngine()
    from services.runtime.task_manager import task_manager

    project_id = "phase2-parent-killed"
    task = task_manager.create_task(project_id=project_id, description="parent task")
    task_id = task["task_id"]
    task_manager.kill_task(project_id, task_id, reason="test")

    out = await engine.spawn_agent(
        project_id=project_id,
        task_id=task_id,
        parent_message="spawn",
        agent_name="WorkerAgent",
        context={},
        depth=1,
    )
    assert out["success"] is False
    assert out["error"] == "parent_task_cancelled"


@pytest.mark.asyncio
async def test_phase_update_memory_links_previous_node(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase8-task", user_id="phase8-user")
    context.project_id = "phase8-proj"
    context.memory["last_memory_node"] = "n_prev"

    captured = {"edges": []}

    def fake_add_node(project_id, **kwargs):
        return "n_new"

    def fake_add_edge(project_id, *, from_id, to_id, relation="caused_by"):
        captured["edges"].append({"from": from_id, "to": to_id, "relation": relation})

    monkeypatch.setattr("services.runtime.runtime_engine.memory_add_node", fake_add_node)
    monkeypatch.setattr("services.runtime.runtime_engine.memory_add_edge", fake_add_edge)

    await engine._phase_update_memory(
        task_id="phase8-task",
        context=context,
        result={"success": True, "output": {"ok": True}, "metadata": {"skill": "inspect"}},
        step_id="phase8-task-step-2",
    )

    assert context.memory["last_memory_node"] == "n_new"
    assert len(captured["edges"]) == 1
    assert captured["edges"][0]["from"] == "n_prev"
    assert captured["edges"][0]["to"] == "n_new"
    assert captured["edges"][0]["relation"] == "next_step"


@pytest.mark.asyncio
async def test_phase_check_permission_allows_known_skill_when_policy_allows(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase2-task", user_id="phase2-user")
    context.project_id = "runtime-phase2"

    class _Allow:
        allowed = True
        ask = False
        reason = "allowed"

    monkeypatch.setattr("services.runtime.runtime_engine.evaluate_tool_call", lambda *args, **kwargs: _Allow())

    out = await engine._phase_check_permission(
        task_id="phase2-task",
        context=context,
        skill="build",
        step_id="phase2-task-step-1",
    )
    assert out is True


@pytest.mark.asyncio
async def test_phase_check_permission_blocks_when_policy_denies(monkeypatch):
    engine = RuntimeEngine()
    context = ExecutionContext(task_id="phase2-task", user_id="phase2-user")
    context.project_id = "runtime-phase2"

    class _Deny:
        allowed = False
        ask = False
        reason = "project override denied"

    monkeypatch.setattr("services.runtime.runtime_engine.evaluate_tool_call", lambda *args, **kwargs: _Deny())

    out = await engine._phase_check_permission(
        task_id="phase2-task",
        context=context,
        skill="build",
        step_id="phase2-task-step-1",
    )
    assert out is False
