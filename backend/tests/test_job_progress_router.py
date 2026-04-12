import pytest
from api.routes import job_progress
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_job_progress_bootstrap_uses_runtime_state(monkeypatch):
    async def fake_get_job(job_id):
        return {"id": job_id, "status": "running"}

    async def fake_get_steps(job_id):
        return [
            {
                "id": "1",
                "step_key": "planning.analyze",
                "agent_name": "Planner",
                "phase": "planning",
                "status": "completed",
                "order_index": 1,
            },
            {
                "id": "2",
                "step_key": "agents.frontend_generation",
                "agent_name": "Frontend Generation",
                "phase": "agents.phase_01",
                "status": "running",
                "order_index": 2,
            },
        ]

    async def fake_get_events(job_id, limit=250):
        return [
            {
                "event_type": "step_started",
                "created_at": "2026-04-09T00:00:00+00:00",
                "payload": {"agent_name": "Frontend Generation"},
            }
        ]

    class FakeMemoryService:
        async def build_context_packet(self, **kwargs):
            return {
                "provider": "memory",
                "project_id": "proj-1",
                "job_id": kwargs.get("job_id"),
                "phase": kwargs.get("phase"),
                "query": kwargs.get("query"),
                "relevant_memories": [
                    {"id": "mem-1", "agent": "Planner", "text": "Plan summary"}
                ],
                "recent_memories": [
                    {
                        "id": "mem-2",
                        "agent": "Frontend Generation",
                        "text": "Built shell",
                    }
                ],
                "token_usage": 42,
            }

    async def fake_get_memory_service():
        return FakeMemoryService()

    monkeypatch.setattr(job_progress, "get_job", fake_get_job)
    monkeypatch.setattr(job_progress, "get_steps", fake_get_steps)
    monkeypatch.setattr(job_progress, "get_job_events", fake_get_events)
    monkeypatch.setattr("memory.service.get_memory_service", fake_get_memory_service)

    payload = await job_progress.get_job_progress("job-123")

    assert payload["job_id"] == "job-123"
    assert payload["total_progress"] == 50
    assert payload["phases"][0]["id"] == "planning"
    assert payload["phases"][1]["id"] == "agents.phase_01"
    assert payload["logs"][0]["agent"] == "Frontend Generation"
    assert payload["controller"]["active_agent_count"] == 1
    assert payload["controller"]["recommended_focus"] == "Watch Frontend Generation"
    assert payload["memory"]["provider"] == "memory"
    assert payload["memory"]["token_usage"] == 42
    assert payload["memory"]["recent_memories"][0]["agent"] == "Frontend Generation"


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
            {
                "id": "1",
                "step_key": "planning.analyze",
                "agent_name": "Planner",
                "phase": "planning",
                "status": "completed",
                "order_index": 1,
            },
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

    await job_progress.broadcast_event(
        "job-123", "step_completed", payload={"agent_name": "Planner"}
    )

    assert sent["job_id"] == "job-123"
    assert sent["message"]["type"] == "step_completed"
    assert sent["message"]["snapshot"]["job_id"] == "job-123"
    assert sent["message"]["snapshot"]["phases"][0]["id"] == "planning"


@pytest.mark.asyncio
async def test_job_progress_truncates_large_log_and_memory_payloads(monkeypatch):
    async def fake_get_job(job_id):
        return {"id": job_id, "status": "running", "goal": "Build giant payload test"}

    async def fake_get_steps(job_id):
        return [
            {
                "id": "1",
                "step_key": "agents.security_checker",
                "agent_name": "Security Checker",
                "phase": "agents.phase_01",
                "status": "failed",
                "order_index": 1,
                "error_message": "X" * 500,
            }
        ]

    async def fake_get_events(job_id, limit=250):
        return [
            {
                "event_type": "step_failed",
                "created_at": "2026-04-09T00:00:00+00:00",
                "payload": {"agent_name": "Security Checker", "error": "Y" * 500},
            }
        ]

    class FakeMemoryService:
        async def build_context_packet(self, **kwargs):
            return {
                "provider": "memory",
                "project_id": "proj-1",
                "job_id": kwargs.get("job_id"),
                "phase": kwargs.get("phase"),
                "query": "Q" * 500,
                "relevant_memories": [
                    {"id": "mem-1", "agent": "Planner", "text": "R" * 500}
                ],
                "recent_memories": [
                    {"id": "mem-2", "agent": "Planner", "text": "S" * 500}
                ],
                "token_usage": 99,
            }

    async def fake_get_memory_service():
        return FakeMemoryService()

    monkeypatch.setattr(job_progress, "get_job", fake_get_job)
    monkeypatch.setattr(job_progress, "get_steps", fake_get_steps)
    monkeypatch.setattr(job_progress, "get_job_events", fake_get_events)
    monkeypatch.setattr("memory.service.get_memory_service", fake_get_memory_service)

    payload = await job_progress.get_job_progress("job-oversized")

    assert len(payload["logs"][0]["message"]) <= 220
    assert len(payload["controller"]["blockers"][0]["error"]) <= 180
    assert len(payload["memory"]["query"]) <= 180
    assert len(payload["memory"]["relevant_memories"][0]["text"]) <= 160
    assert len(payload["memory"]["recent_memories"][0]["text"]) <= 160
