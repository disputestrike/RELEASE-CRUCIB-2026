"""
10/10 Roadmap: E2E tests for agent orchestration.
- Full build with mocked LLM ? quality score computed.
- Agent failure recovery ? fallback or skip.
No real API keys required for these tests (mocks used).
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def test_quality_score_computed_after_fake_build():
    """After a build, quality_score has overall_score and breakdown (frontend, backend, database, tests)."""
    from code_quality import score_generated_code

    frontend = "import React from 'react';\nconst App = () => <div className='root'>Hi</div>;\nexport default App;"
    backend = "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef root(): return {'ok': True}"
    database = "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));"
    tests = "def test_root(): assert True"

    result = score_generated_code(
        frontend_code=frontend,
        backend_code=backend,
        database_schema=database,
        test_code=tests,
    )
    assert "overall_score" in result
    assert "breakdown" in result
    assert "verdict" in result
    assert result["overall_score"] >= 0
    assert result["overall_score"] <= 100
    assert "frontend" in result["breakdown"]
    assert "backend" in result["breakdown"]
    assert "database" in result["breakdown"]
    assert "tests" in result["breakdown"]
    assert result["breakdown"]["frontend"]["score"] >= 0
    assert result["verdict"] in ("excellent", "good", "needs_work")


def test_quality_score_accepts_empty_inputs():
    """score_generated_code handles missing inputs (empty strings)."""
    from code_quality import score_generated_code

    result = score_generated_code()
    assert result["overall_score"] >= 0
    assert result["verdict"] in ("excellent", "good", "needs_work")


@pytest.mark.asyncio
async def test_agent_failure_recovery_returns_fallback_or_skip():
    """When an agent fails after retries, we get failed_with_fallback (high) or skipped (low)."""
    from server import _run_single_agent_with_retry

    project_id = "test-proj-001"
    user_id = "test-user-001"
    agent_name = "Performance Analyzer"  # low criticality
    project_prompt = "Build a todo app"
    previous_outputs = {}
    effective = {"openai": "sk-mock", "anthropic": None}
    model_chain = [{"provider": "openai", "model": "claude-haiku-4-5-20251001"}]

    with patch("server.db") as mock_db:
        mock_db.projects.update_one = AsyncMock()
        mock_db.agent_status.update_one = AsyncMock()
        mock_db.project_logs.insert_one = AsyncMock()
        mock_db.token_usage.insert_one = AsyncMock()

        with patch(
            "server._run_single_agent_with_context", new_callable=AsyncMock
        ) as mock_run:
            mock_run.side_effect = Exception("Simulated API failure")

            result = await _run_single_agent_with_retry(
                project_id,
                user_id,
                agent_name,
                project_prompt,
                previous_outputs,
                effective,
                model_chain,
                max_retries=2,
            )

    assert result.get("status") in ("skipped", "failed_with_fallback", "failed")
    assert "reason" in result or "output" in result
    if result.get("status") == "skipped":
        assert result.get("recoverable") is True


@pytest.mark.asyncio
async def test_high_agent_failure_returns_fallback():
    """High-criticality agent failure returns failed_with_fallback and fallback output."""
    from server import _run_single_agent_with_retry

    project_id = "test-proj-002"
    user_id = "test-user-002"
    agent_name = "Frontend Generation"  # high criticality
    project_prompt = "Build a todo app"
    previous_outputs = {}
    effective = {"openai": "sk-mock", "anthropic": None}
    model_chain = [{"provider": "openai", "model": "claude-haiku-4-5-20251001"}]

    with patch("server.db") as mock_db:
        mock_db.projects.update_one = AsyncMock()
        mock_db.agent_status.update_one = AsyncMock()
        mock_db.project_logs.insert_one = AsyncMock()

        with patch(
            "server._run_single_agent_with_context", new_callable=AsyncMock
        ) as mock_run:
            mock_run.side_effect = Exception("Simulated failure")

            result = await _run_single_agent_with_retry(
                project_id,
                user_id,
                agent_name,
                project_prompt,
                previous_outputs,
                effective,
                model_chain,
                max_retries=2,
            )

    assert result.get("status") == "failed_with_fallback"
    assert result.get("recoverable") is True
    out = result.get("output") or result.get("result") or ""
    assert out and (
        ("React" in out)
        or ("frontend" in out.lower())
        or ("placeholder" in out.lower())
    )


def test_dag_phases_include_all_agents():
    """Execution phases from DAG include all 20 agents exactly once."""
    from agent_dag import AGENT_DAG, get_execution_phases

    phases = get_execution_phases(AGENT_DAG)
    all_in_phases = [a for p in phases for a in p]
    assert len(all_in_phases) == len(AGENT_DAG)
    assert set(all_in_phases) == set(AGENT_DAG.keys())


def test_context_truncation():
    """build_context_from_previous_agents truncates long outputs."""
    from agent_dag import build_context_from_previous_agents, get_context_max_chars

    max_chars = get_context_max_chars()
    long_output = "x" * (max_chars + 500)
    previous = {"Planner": {"output": long_output}}
    out = build_context_from_previous_agents(
        "Stack Selector", previous, "Build a todo app"
    )
    assert "truncated" in out
    assert len(out) <= len("Build a todo app") + max_chars + 100
