from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_simulation_orchestrator_includes_personas(monkeypatch):
    from services.runtime.simulation_orchestrator import SimulationOrchestrator

    async def _noop(*_args, **_kwargs):
        return None

    orch = SimulationOrchestrator(job_id="job-1", user_id="user-1")
    monkeypatch.setattr(orch, "_persist_log", _noop)

    out = await orch.run(
        scenario="What if we switch providers?",
        population_size=16,
        rounds=3,
        agent_roles=["architect", "backend", "security"],
    )

    assert out["simulationId"].startswith("sim_")
    assert out["population_size"] == 16
    assert isinstance(out["personas"], list)
    assert len(out["personas"]) == 16
    assert out["recommendation"]["recommended_action"]


@pytest.mark.asyncio
async def test_simulation_orchestrator_stream_ndjson(monkeypatch):
    from services.runtime.simulation_orchestrator import SimulationOrchestrator

    async def _noop(*_args, **_kwargs):
        return None

    orch = SimulationOrchestrator(job_id="job-2", user_id="user-2")
    monkeypatch.setattr(orch, "_persist_log", _noop)

    chunks = []
    async for line in orch.stream_ndjson(
        scenario="What if we remove PayPal?",
        population_size=12,
        rounds=2,
        agent_roles=["architect", "backend", "security"],
    ):
        chunks.append(line)

    assert chunks
    payloads = [json.loads(c.strip()) for c in chunks if c.strip()]
    assert any(p.get("type") == "simulation.update" for p in payloads)
    assert payloads[-1].get("type") == "simulation.completed"
    assert isinstance(payloads[-1].get("personas"), list)
