from unittest.mock import AsyncMock

import pytest


class _UnavailableVectorMemory:
    def is_available(self):
        return False


def _no_post_step(agent_name, project_id, previous_outputs, result):
    return result


@pytest.mark.asyncio
async def test_agent_cache_input_handles_structured_previous_outputs(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")

    import server

    rendered = server._agent_cache_input(
        "ML Model Definition Agent",
        "Build an ML recommendation engine",
        {
            "ML Framework Selector Agent": {
                "output": {
                    "recommended_framework": "tensorflow",
                    "reasoning": "GPU support",
                }
            }
        },
    )

    assert isinstance(rendered, str)
    assert "tensorflow" in rendered


@pytest.mark.asyncio
async def test_run_single_agent_with_context_repairs_invalid_python_output(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")

    import server

    monkeypatch.setattr(server, "REAL_AGENT_NAMES", set())
    monkeypatch.setattr(
        server,
        "_call_llm_with_fallback",
        AsyncMock(
            return_value=(
                "async def create_job(data: dict)\n    job = data\n    return job\n",
                {},
            )
        ),
    )
    monkeypatch.setattr(server, "persist_agent_output", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "run_agent_real_behavior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        server, "run_real_post_step", AsyncMock(side_effect=_no_post_step)
    )
    monkeypatch.setattr(server, "_init_agent_learning", AsyncMock(return_value=None))
    monkeypatch.setattr(server, "_vector_memory", _UnavailableVectorMemory())
    monkeypatch.setattr(server, "_pgvector_memory", _UnavailableVectorMemory())

    result = await server._run_single_agent_with_context(
        project_id="proj-ml-1",
        user_id="user-1",
        agent_name="ML Model Definition Agent",
        project_prompt="Build an ML recommendation engine with TensorFlow",
        previous_outputs={},
        effective={"anthropic": "test-key"},
        model_chain=[{"provider": "anthropic", "model": "claude-sonnet"}],
        build_kind="fullstack",
    )

    assert result["status"] == "completed"
    assert result["repair_metadata"]["status"] == "repaired"
    assert result["repair_metadata"]["strategy"] in {
        "add_missing_colons",
        "ensure_block_body",
        "llm_repair",
    }
    assert "async def create_job(data: dict):" in result["output"]
