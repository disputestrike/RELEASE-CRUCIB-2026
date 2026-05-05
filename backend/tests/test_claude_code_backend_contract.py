from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.job_event_service import get_job_steps_service
from backend.services.job_service import create_job_service
from backend.routes import orchestrator


class _RuntimeState:
    def __init__(self):
        self.steps_created = []
        self.events = []
        self.steps = []
        self.job = {
            "id": "job-claude-1",
            "project_id": "proj-1",
            "status": "planned",
            "mode": "auto",
            "goal": "Build a store",
            "user_id": "user-1",
        }

    def set_pool(self, pool):
        self.pool = pool

    async def ensure_job_fk_prerequisites(self, project_id, user_id):
        return None

    async def create_job(self, **kwargs):
        self.job.update(kwargs)
        self.job["id"] = "job-claude-1"
        return dict(self.job)

    async def create_step(self, **kwargs):
        self.steps_created.append(kwargs)
        return {"id": "step-1", **kwargs}

    async def append_job_event(self, job_id, event_type, payload=None, **kwargs):
        event = {"job_id": job_id, "event_type": event_type, "payload": payload or {}, **kwargs}
        self.events.append(event)
        return event

    async def get_job(self, job_id):
        return dict(self.job) if job_id == self.job["id"] else None

    async def get_steps(self, job_id):
        return list(self.steps)

    async def get_job_events(self, job_id, since_id=None, limit=200):
        return list(self.events)[-limit:]


@pytest.mark.asyncio
async def test_create_job_defaults_to_claude_code_without_legacy_steps(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_LEGACY_JOB_STEPS", raising=False)
    state = _RuntimeState()

    async def generate_plan_should_not_run(*args, **kwargs):
        raise AssertionError("legacy planner should not run for default job creation")

    async def pool_getter():
        return object()

    result = await create_job_service(
        body=SimpleNamespace(project_id="proj-1", goal="Build an e-commerce store", mode="auto"),
        user={"id": "user-1"},
        runtime_state_getter=lambda: state,
        pool_getter=pool_getter,
        generate_plan=generate_plan_should_not_run,
    )

    assert result["plan"]["engine"] == "claude_code_tool_loop"
    assert result["plan"]["legacy_job_steps"] is False
    assert state.steps_created == []
    assert any(event["event_type"] == "claude_code_backend_selected" for event in state.events)


@pytest.mark.asyncio
async def test_steps_endpoint_filters_legacy_agents_when_claude_runtime_is_active():
    state = _RuntimeState()
    state.steps = [
        {"id": "old-1", "step_key": "agents.planner", "agent_name": "Planner", "phase": "orchestration"},
        {"id": "new-1", "step_key": "runtime.proof", "agent_name": "Claude Code", "phase": "claude_code_runtime"},
    ]
    state.events = [{"event_type": "pipeline_started", "payload": {"engine": "claude_code_tool_loop"}}]

    async def pool_getter():
        return object()

    result = await get_job_steps_service(
        job_id="job-claude-1",
        user={"id": "user-1"},
        runtime_state_getter=lambda: state,
        pool_getter=pool_getter,
        assert_owner=lambda owner, user: None,
    )

    assert result["steps"] == [state.steps[1]]


@pytest.mark.asyncio
async def test_orchestrator_plan_route_does_not_seed_legacy_dag(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_LEGACY_JOB_STEPS", raising=False)
    state = _RuntimeState()

    async def no_pool():
        return None

    async def generate_plan_should_not_run(*args, **kwargs):
        raise AssertionError("orchestrator plan should not run the legacy planner")

    planner = SimpleNamespace(
        generate_plan=generate_plan_should_not_run,
        estimate_tokens=lambda plan: {"estimated_tokens": 0},
    )

    monkeypatch.setattr(orchestrator, "_get_orchestration", lambda: (state, None, planner, None, None))
    monkeypatch.setattr(orchestrator, "_get_server_helpers", lambda: (None, None, None, None))
    monkeypatch.setattr(orchestrator, "_update_last_build_state", lambda plan: None)

    import backend.db_pg as db_pg

    monkeypatch.setattr(db_pg, "get_pg_pool", no_pool)

    result = await orchestrator.create_plan(
        orchestrator.PlanRequest(project_id="proj-1", goal="Build an e-commerce store", mode="auto"),
        user={"id": "user-1"},
    )

    assert result["step_count"] == 0
    assert result["plan"]["engine"] == "claude_code_tool_loop"
    assert state.steps_created == []
    assert any(event["event_type"] == "claude_code_backend_selected" for event in state.events)
