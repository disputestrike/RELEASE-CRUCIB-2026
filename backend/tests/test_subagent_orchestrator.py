from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_subagent_orchestrator_runs_parallel_branches(monkeypatch):
    import backend.services.runtime.runtime_engine as runtime_engine_module
    from backend.services.runtime.subagent_orchestrator import SubagentOrchestrator

    calls = []

    async def _fake_call_model_for_request(**kwargs):
        calls.append(kwargs)
        role = (kwargs.get("agent_name") or "").split(":")[-1]
        return (f"recommendation from {role}", "fake-model")

    monkeypatch.setattr(
        runtime_engine_module.runtime_engine,
        "call_model_for_request",
        _fake_call_model_for_request,
    )

    orch = SubagentOrchestrator(job_id="job-123", user_id="user-123")
    out = await orch.run(
        task="Decide rollout strategy",
        config={"branches": 5, "mode": "swan", "strategy": "diverse_priors"},
        context={"project": "alpha"},
    )

    assert out["jobId"] == "job-123"
    assert out["actualBranches"] == 5
    assert len(out["subagentResults"]) == 5
    assert len(calls) == 5
    assert out["consensus"]["decision"]
    assert 0 <= out["confidence"] <= 1


@pytest.mark.asyncio
async def test_subagent_orchestrator_falls_back_without_model(monkeypatch):
    import backend.services.runtime.runtime_engine as runtime_engine_module
    from backend.services.runtime.subagent_orchestrator import SubagentOrchestrator

    async def _fail(**_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(runtime_engine_module.runtime_engine, "call_model_for_request", _fail)

    orch = SubagentOrchestrator(job_id="job-xyz", user_id="user-xyz")
    out = await orch.run(task="Analyze payment migration", config={"branches": 3}, context={})

    assert len(out["subagentResults"]) == 3
    for row in out["subagentResults"]:
        assert row["status"] == "complete"
        assert row["result"]["model"] == "fallback"
        assert "guarded rollout" in row["result"]["recommendation"]
