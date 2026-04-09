import pytest
from fastapi import HTTPException

from api.routes import job_progress


@pytest.mark.asyncio
async def test_job_progress_bootstrap_uses_runtime_state(monkeypatch):
    async def fake_get_job(job_id):
        return {"id": job_id, "status": "running"}

    async def fake_get_steps(job_id):
        return [
            {"id": "1", "step_key": "planning.analyze", "agent_name": "Planner", "phase": "planning", "status": "completed", "order_index": 1},
            {"id": "2", "step_key": "agents.frontend_generation", "agent_name": "Frontend Generation", "phase": "agents.phase_01", "status": "running", "order_index": 2},
        ]

    async def fake_get_events(job_id, limit=250):
        return [
            {"event_type": "step_started", "created_at": "2026-04-09T00:00:00+00:00", "payload": {"agent_name": "Frontend Generation"}}
        ]

    monkeypatch.setattr(job_progress, "get_job", fake_get_job)
    monkeypatch.setattr(job_progress, "get_steps", fake_get_steps)
    monkeypatch.setattr(job_progress, "get_job_events", fake_get_events)

    payload = await job_progress.get_job_progress("job-123")

    assert payload["job_id"] == "job-123"
    assert payload["total_progress"] == 50
    assert payload["phases"][0]["id"] == "planning"
    assert payload["phases"][1]["id"] == "agents.phase_01"
    assert payload["logs"][0]["agent"] == "Frontend Generation"


@pytest.mark.asyncio
async def test_job_progress_404_when_job_missing(monkeypatch):
    async def fake_get_job(job_id):
        return None

    monkeypatch.setattr(job_progress, "get_job", fake_get_job)

    with pytest.raises(HTTPException) as exc:
        await job_progress.get_job_progress("missing-job")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_broadcast_event_includes_live_snapshot(monkeypatch):
    sent = {}

    async def fake_get_job(job_id):
        return {"id": job_id, "status": "running"}

    async def fake_get_steps(job_id):
        return [
            {"id": "1", "step_key": "planning.analyze", "agent_name": "Planner", "phase": "planning", "status": "completed", "order_index": 1},
        ]

    async def fake_get_events(job_id, limit=250):
        return []

    async def fake_broadcast(job_id, message):
        sent["job_id"] = job_id
        sent["message"] = message

    monkeypatch.setattr(job_progress, "get_job", fake_get_job)
    monkeypatch.setattr(job_progress, "get_steps", fake_get_steps)
    monkeypatch.setattr(job_progress, "get_job_events", fake_get_events)
    monkeypatch.setattr(job_progress.manager, "broadcast", fake_broadcast)

    await job_progress.broadcast_event("job-123", "step_completed", payload={"agent_name": "Planner"})

    assert sent["job_id"] == "job-123"
    assert sent["message"]["type"] == "step_completed"
    assert sent["message"]["snapshot"]["job_id"] == "job-123"
    assert sent["message"]["snapshot"]["phases"][0]["id"] == "planning"
