from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_simulation_engine_returns_clustered_updates():
    from services.runtime.simulation_engine import SimulationEngine

    out = SimulationEngine.run_simulation(
        scenario="What if we switch payment providers?",
        population_size=24,
        rounds=3,
        agent_roles=["architect", "backend", "security"],
        priors={"cost_sensitive": 0.3, "security_first": 0.4, "speed_first": 0.3},
        seed=7,
    )

    assert out["population_size"] == 24
    assert out["rounds_executed"] >= 1
    assert isinstance(out["updates"], list) and out["updates"]
    u0 = out["updates"][0]
    assert "clusters" in u0 and isinstance(u0["clusters"], list)
    assert "sentiment_shift" in u0 and isinstance(u0["sentiment_shift"], dict)
    assert "recommendation" in out and isinstance(out["recommendation"], dict)
    assert out["recommendation"]["recommended_action"]


@pytest.mark.asyncio
async def test_spawn_simulate_endpoint_returns_success(monkeypatch):
    from backend.routes import crucib_workspace_adapter as route

    class _Runtime:
        def set_pool(self, _pool):
            return None

        async def get_job(self, _job_id):
            return {"id": "job-1", "user_id": "user-1"}

    monkeypatch.setattr(route, "_get_auth", lambda: (lambda: {"id": "user-1"}))
    monkeypatch.setattr(route, "_load_job_with_fallback", lambda _job_id, _user: _Runtime().get_job(_job_id))

    async def _pool():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_pg_pool=_pool))
    monkeypatch.setitem(
        __import__("sys").modules,
        "server",
        SimpleNamespace(
            _get_orchestration=lambda: (_Runtime(), None, None, None),
            _assert_job_owner_match=lambda _owner, _user: None,
        ),
    )

    emitted = []

    from backend.services import events as events_module

    monkeypatch.setattr(events_module.event_bus, "emit", lambda event_type, payload=None: emitted.append((event_type, payload or {})))

    body = route.SpawnSimulateBody(jobId="job-1", scenario="What if we replace PayPal?")
    result = await route.spawn_simulate(body, user={"id": "user-1"})

    assert result["success"] is True
    assert result["jobId"] == "job-1"
    assert isinstance(result.get("updates"), list)
    assert isinstance(result.get("recommendation"), dict)
    assert any(t == "simulation.started" for t, _ in emitted)
    assert any(t == "simulation.completed" for t, _ in emitted)


@pytest.mark.asyncio
async def test_spawn_simulate_stream_endpoint_returns_ndjson(monkeypatch):
    from backend.routes import crucib_workspace_adapter as route

    class _Runtime:
        def set_pool(self, _pool):
            return None

        async def get_job(self, _job_id):
            return {"id": "job-1", "user_id": "user-1"}

    monkeypatch.setattr(route, "_get_auth", lambda: (lambda: {"id": "user-1"}))
    monkeypatch.setattr(route, "_load_job_with_fallback", lambda _job_id, _user: _Runtime().get_job(_job_id))

    async def _pool():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_pg_pool=_pool))
    monkeypatch.setitem(
        __import__("sys").modules,
        "server",
        SimpleNamespace(
            _get_orchestration=lambda: (_Runtime(), None, None, None),
            _assert_job_owner_match=lambda _owner, _user: None,
        ),
    )

    body = route.SpawnSimulateBody(
        jobId="job-1",
        scenario="What if we replace PayPal?",
        population_size=12,
        rounds=2,
    )
    response = await route.spawn_simulate_stream(body, user={"id": "user-1"})

    assert response.media_type == "application/x-ndjson"

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)

    lines = [line for chunk in chunks for line in chunk.strip().split("\n") if line]
    assert lines

    import json

    payloads = [json.loads(line) for line in lines]
    assert any(p.get("type") == "simulation.update" for p in payloads)
    assert payloads[-1].get("type") == "simulation.completed"
    assert payloads[-1].get("jobId") == "job-1"
