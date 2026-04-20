from __future__ import annotations

import asyncio

import pytest


def _make_brain(monkeypatch, agent_instances, agent_configs):
    """Return a minimal brain mock that satisfies run_task_loop's interface."""
    from services.brain_layer import BrainLayer

    brain = object.__new__(BrainLayer)

    def _decide(session, message):
        return {
            "intent": "test",
            "intent_confidence": 1.0,
            "status": "ready",
            "selected_agents": list(agent_instances.keys()),
            "selected_agent_configs": agent_configs,
        }

    def _get_agent_instances():
        return agent_instances

    def _build_agent_context(cfg, message, session, extra):
        ctx = dict(cfg)
        ctx.update(extra)
        ctx["message"] = message
        return ctx

    def _summarize_execution(assessment, execution):
        return "done"

    brain.decide = _decide
    brain._get_agent_instances = _get_agent_instances
    brain._build_agent_context = _build_agent_context
    brain._summarize_execution = _summarize_execution
    return brain


# ---------------------------------------------------------------------------
# Test 1: agent result with spawn_request triggers spawn_agent and records it
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_task_loop_spawn_request_from_agent(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    emitted: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "emit", lambda t, p=None: emitted.append((t, p or {})))

    spawned: list[dict] = []

    class _SpawningAgent:
        async def run(self, context):
            return {"text": "agent done", "spawn_request": {"agent": "ChildAgent", "context": {"key": "val"}}}

    class _ChildAgent:
        async def run(self, context):
            return {"text": "child done"}

    agent_configs = [{"agent": "SpawningAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {"SpawningAgent": _SpawningAgent()},
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)

    # Capture spawn_agent calls without actually spawning.
    async def _fake_spawn(*, project_id, task_id, parent_message, agent_name, context, depth=1, **_kw):
        spawned.append({"agent": agent_name, "context": context, "depth": depth})
        return {"success": True, "result": {"text": "child done"}, "workspace": "/tmp/fake"}

    monkeypatch.setattr(engine, "spawn_agent", _fake_spawn)

    # Also stub _select_provider_chain so it doesn't need a real router.
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    project_id = "proj-rtl-spawn-1"
    task = task_manager.create_task(project_id=project_id, description="spawn test")
    session = ContextManager().create_session("sess-rtl-spawn-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task["task_id"],
        user_message="do spawn test",
        planner=brain,
    )

    assert out["status"] == "executed"
    execution = out["execution"]

    # One primary output + one spawned output.
    assert execution["spawned_tasks"] == 1
    assert any(o.get("spawned") for o in execution["agent_outputs"])

    # spawn_agent received the right arguments.
    assert len(spawned) == 1
    assert spawned[0]["agent"] == "ChildAgent"
    assert spawned[0]["context"]["key"] == "val"
    assert spawned[0]["depth"] == 1

    # Execution loop emitted expected lifecycle events.
    event_names = [e for e, _ in emitted]
    assert "brain.execution.started" in event_names
    assert "brain.execution.completed" in event_names


# ---------------------------------------------------------------------------
# Test 2: task killed mid-loop raises CancelledError → status execution_cancelled
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_task_loop_cancelled_after_step(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    monkeypatch.setattr(event_bus, "emit", lambda *a, **kw: None)

    project_id = "proj-rtl-cancel-1"
    task = task_manager.create_task(project_id=project_id, description="cancel test")
    task_id = task["task_id"]

    class _KillingAgent:
        """Agent that marks its own task as killed during execution."""

        async def run(self, context):
            task_manager.kill_task(project_id, task_id, reason="killed_mid_step")
            return {"text": "about to be cancelled"}

    agent_configs = [{"agent": "KillingAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {"KillingAgent": _KillingAgent()},
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    session = ContextManager().create_session("sess-rtl-cancel-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task_id,
        user_message="cancel me",
        planner=brain,
    )

    assert out["status"] == "execution_cancelled"
    assert out["execution"].get("cancelled") is True


# ---------------------------------------------------------------------------
# Test 3: no spawn_request → spawned_tasks == 0 in execution summary
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_task_loop_no_spawn_request(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    monkeypatch.setattr(event_bus, "emit", lambda *a, **kw: None)

    class _PlainAgent:
        async def run(self, context):
            return {"text": "plain result"}

    agent_configs = [{"agent": "PlainAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {"PlainAgent": _PlainAgent()},
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    project_id = "proj-rtl-no-spawn-1"
    task = task_manager.create_task(project_id=project_id, description="plain run")
    session = ContextManager().create_session("sess-rtl-no-spawn-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task["task_id"],
        user_message="just run",
        planner=brain,
    )

    assert out["status"] == "executed"
    assert out["execution"]["spawned_tasks"] == 0
    assert all(not o.get("spawned") for o in out["execution"]["agent_outputs"])


@pytest.mark.asyncio
async def test_run_task_loop_retries_and_recovers(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    monkeypatch.setattr(event_bus, "emit", lambda *a, **kw: None)

    calls = {"n": 0}

    class _FlakyAgent:
        async def run(self, context):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("network timeout")
            return {"text": "recovered"}

    agent_configs = [{"agent": "FlakyAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {"FlakyAgent": _FlakyAgent()},
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    project_id = "proj-rtl-retry-1"
    task = task_manager.create_task(project_id=project_id, description="retry run")
    session = ContextManager().create_session("sess-rtl-retry-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task["task_id"],
        user_message="retry please",
        planner=brain,
    )

    assert out["status"] == "executed"
    assert calls["n"] >= 2
    assert any(o.get("runtime_meta") for o in out["execution"]["agent_outputs"])


@pytest.mark.asyncio
async def test_run_task_loop_repair_path_recovers(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    emitted: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "emit", lambda t, p=None: emitted.append((t, p or {})))
    monkeypatch.setenv("CRUCIB_AGENT_MAX_RETRIES", "1")

    state = {"repaired": False, "attempts": 0}

    class _AlwaysFailUntilRepairAgent:
        async def run(self, context):
            state["attempts"] += 1
            if not state["repaired"]:
                raise RuntimeError("network timeout")
            return {"text": "recovered after repair"}

    class _RepairAgent:
        async def run(self, context):
            assert context.get("repair") is True
            assert context.get("failed_agent") == "FlakyAgent"
            state["repaired"] = True
            return {"action": "patched"}

    agent_configs = [{"agent": "FlakyAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {
            "FlakyAgent": _AlwaysFailUntilRepairAgent(),
            "CodeAnalysisAgent": _RepairAgent(),
        },
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    project_id = "proj-rtl-repair-success-1"
    task = task_manager.create_task(project_id=project_id, description="repair success run")
    session = ContextManager().create_session("sess-rtl-repair-success-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task["task_id"],
        user_message="recover with repair",
        planner=brain,
    )

    assert out["status"] == "executed"
    assert state["attempts"] >= 2
    assert any(o.get("runtime_meta") for o in out["execution"]["agent_outputs"])

    retry_events = [payload for name, payload in emitted if name == "brain.agent.retry_scheduled"]
    assert retry_events
    assert retry_events[0].get("failure_kind") == "timeout"
    assert retry_events[0].get("attempt") == 1
    assert "max_retries" in retry_events[0]
    assert "delay_s" in retry_events[0]

    assert any(name == "brain.agent.repair.started" for name, _ in emitted)
    assert any(name == "brain.agent.repair.completed" for name, _ in emitted)


@pytest.mark.asyncio
async def test_run_task_loop_repair_path_fails_with_contract(monkeypatch):
    from services.conversation_manager import ContextManager
    from services.events import event_bus
    from services.runtime.runtime_engine import RuntimeEngine
    from services.runtime.task_manager import task_manager

    emitted: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "emit", lambda t, p=None: emitted.append((t, p or {})))
    monkeypatch.setenv("CRUCIB_AGENT_MAX_RETRIES", "1")

    class _FailingAgent:
        async def run(self, context):
            raise RuntimeError("network timeout")

    class _BrokenRepairAgent:
        async def run(self, context):
            raise RuntimeError("repair planning failed")

    agent_configs = [{"agent": "FlakyAgent", "params": {}}]
    brain = _make_brain(
        monkeypatch,
        {
            "FlakyAgent": _FailingAgent(),
            "CodeAnalysisAgent": _BrokenRepairAgent(),
        },
        agent_configs,
    )

    engine = RuntimeEngine()
    monkeypatch.setattr(engine, "_brain_factory", lambda: brain)
    monkeypatch.setattr(engine, "_select_provider_chain", lambda *_: [])

    project_id = "proj-rtl-repair-fail-1"
    task = task_manager.create_task(project_id=project_id, description="repair fail run")
    session = ContextManager().create_session("sess-rtl-repair-fail-1")

    out = await engine.run_task_loop(
        session=session,
        project_id=project_id,
        task_id=task["task_id"],
        user_message="repair should fail",
        planner=brain,
    )

    assert out["status"] == "execution_failed"
    error = str((out.get("execution") or {}).get("error") or "")
    assert "agent_failed:FlakyAgent:timeout" in error

    assert any(name == "brain.agent.repair.started" for name, _ in emitted)
    assert any(name == "brain.agent.repair.failed" for name, _ in emitted)
    fail_event = next(payload for name, payload in emitted if name == "brain.agent.repair.failed")
    assert fail_event.get("failure_kind") == "timeout"
    assert fail_event.get("failed_agent") == "FlakyAgent"
