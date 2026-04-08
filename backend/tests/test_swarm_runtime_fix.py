from unittest.mock import AsyncMock

import pytest


class _UnavailableVectorMemory:
    def is_available(self):
        return False


@pytest.mark.asyncio
async def test_run_single_agent_with_context_returns_completed_result_for_planner(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
    import server

    monkeypatch.setattr(server, "REAL_AGENT_NAMES", set())
    monkeypatch.setattr(server, "_call_llm_with_fallback", AsyncMock(return_value=("Planner output", {})))
    monkeypatch.setattr(server, "persist_agent_output", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "run_agent_real_behavior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        server,
        "run_real_post_step",
        AsyncMock(side_effect=lambda agent_name, project_id, previous_outputs, result: result),
    )
    monkeypatch.setattr(server, "_init_agent_learning", AsyncMock(return_value=None))
    monkeypatch.setattr(server, "_vector_memory", _UnavailableVectorMemory())
    monkeypatch.setattr(server, "_pgvector_memory", _UnavailableVectorMemory())

    result = await server._run_single_agent_with_context(
        project_id="proj-1",
        user_id="user-1",
        agent_name="Planner",
        project_prompt="Build 3D product visualizer with Three.js and animations",
        previous_outputs={},
        effective={"anthropic": "test-key"},
        model_chain=[{"provider": "anthropic", "model": "claude-sonnet"}],
        build_kind="fullstack",
    )

    assert result["status"] == "completed"
    assert result["output"] == "Planner output"
    assert result["result"] == "Planner output"
    assert result["tokens_used"] >= 100
