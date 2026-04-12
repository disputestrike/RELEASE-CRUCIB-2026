"""
Tests for agents & automation: executor (T-1), schedule (T-2), webhook (T-3), CRUD (T-4), runs (T-5), credits (T-6).
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# Ensure env before importing server (PostgreSQL via DATABASE_URL when needed)


@pytest.mark.asyncio
async def test_schedule_next_run_at():
    """T-2: next_run_at from cron '0 9 * * *' is next 9am."""
    from automation.schedule import next_run_at
    from croniter import croniter

    now = datetime(2026, 2, 18, 8, 0, 0, tzinfo=timezone.utc)
    next_ = next_run_at(cron_expression="0 9 * * *", from_time=now)
    assert next_ is not None
    assert next_.hour == 9
    assert next_.day == 18


@pytest.mark.asyncio
async def test_executor_http_action():
    """T-1: Executor with one HTTP action (mock)."""
    from automation.executor import run_actions

    agent_doc = {
        "id": "test-agent",
        "user_id": "user-1",
        "actions": [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://httpbin.org/get"},
            }
        ],
    }
    status, output_summary, log_lines, _ = await run_actions(
        agent_doc, "user-1", "run-1", []
    )
    assert status in ("success", "failed")
    assert isinstance(log_lines, list)
    assert "steps" in output_summary or "error" in output_summary


@pytest.mark.asyncio
async def test_executor_run_agent_action_uses_callback_with_substituted_prompt():
    """T-1: Executor run_agent action bridges automation steps into the agent DAG."""
    from automation.executor import run_actions

    calls = []

    async def fake_run_agent(user_id, agent_name, prompt):
        calls.append({"user_id": user_id, "agent_name": agent_name, "prompt": prompt})
        return {"result": "Summarized: shipped bridge proof"}

    agent_doc = {
        "id": "test-agent",
        "user_id": "user-1",
        "actions": [
            {
                "type": "run_agent",
                "config": {
                    "agent_name": "Content Agent",
                    "prompt": "Summarize {{steps.0.output}}",
                },
            }
        ],
    }

    status, output_summary, log_lines, _ = await run_actions(
        agent_doc,
        "user-1",
        "run-1",
        [{"output": "CrucibAI builds apps and automates workflows."}],
        run_agent_callback=fake_run_agent,
    )

    assert status == "success"
    assert calls == [
        {
            "user_id": "user-1",
            "agent_name": "Content Agent",
            "prompt": "Summarize CrucibAI builds apps and automates workflows.",
        }
    ]
    assert (
        output_summary["steps"][1]["output"]["result"]
        == "Summarized: shipped bridge proof"
    )
    assert any("[RUN_AGENT] Content Agent" in line for line in log_lines)


@pytest.mark.asyncio
async def test_webhook_invalid_secret_401(app_client, auth_headers):
    """T-3: POST webhook with invalid secret returns 401."""
    # Create agent with webhook trigger
    create = {
        "name": "Webhook test",
        "description": "Test",
        "trigger": {"type": "webhook", "webhook_secret": "my-secret-123"},
        "actions": [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://httpbin.org/get"},
            }
        ],
    }
    r = await app_client.post(
        "/api/agents", json=create, headers=auth_headers, timeout=10
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    agent_id = data["id"]
    # Call webhook with wrong secret
    r2 = await app_client.post(
        f"/api/agents/webhook/{agent_id}?secret=wrong", timeout=10
    )
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_agents_crud_create_get_list(app_client, auth_headers):
    """T-4: Create agent, get, list; auth required."""
    create = {
        "name": "Test schedule agent",
        "description": "Cron daily",
        "trigger": {"type": "schedule", "cron_expression": "0 9 * * *"},
        "actions": [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://httpbin.org/get"},
            }
        ],
    }
    r = await app_client.post(
        "/api/agents", json=create, headers=auth_headers, timeout=10
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["id"]
    assert data["name"] == create["name"]
    agent_id = data["id"]
    r2 = await app_client.get(
        f"/api/agents/{agent_id}", headers=auth_headers, timeout=10
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == agent_id
    r3 = await app_client.get("/api/agents/mine", headers=auth_headers, timeout=10)
    assert r3.status_code == 200
    assert "items" in r3.json()
    # No auth -> 403 or 401
    r4 = await app_client.get(f"/api/agents/{agent_id}", timeout=10)
    assert r4.status_code in (401, 403)


@pytest.mark.asyncio
async def test_agents_runs_and_logs(app_client, auth_headers):
    """T-5: Trigger run, get run, get runs list, get logs."""
    create = {
        "name": "Run test",
        "trigger": {"type": "webhook", "webhook_secret": "s1"},
        "actions": [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://httpbin.org/get"},
            }
        ],
    }
    r = await app_client.post(
        "/api/agents", json=create, headers=auth_headers, timeout=10
    )
    assert r.status_code in (200, 201), r.text
    agent_id = r.json()["id"]
    r2 = await app_client.post(
        f"/api/agents/{agent_id}/run", headers=auth_headers, timeout=30
    )
    assert r2.status_code != 402, r2.text
    assert r2.status_code == 200
    run_id = r2.json()["run_id"]
    r3 = await app_client.get(
        f"/api/agents/{agent_id}/runs", headers=auth_headers, timeout=10
    )
    assert r3.status_code == 200
    assert any(x["id"] == run_id for x in r3.json().get("items", []))
    r4 = await app_client.get(
        f"/api/agents/runs/{run_id}", headers=auth_headers, timeout=10
    )
    assert r4.status_code == 200
    r5 = await app_client.get(
        f"/api/agents/runs/{run_id}/logs", headers=auth_headers, timeout=10
    )
    assert r5.status_code == 200
    assert "log_lines" in r5.json()


@pytest.mark.asyncio
async def test_agents_templates_list(app_client):
    """Templates API: list (no auth)."""
    r = await app_client.get("/api/agents/templates", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "templates" in data
    assert len(data["templates"]) >= 5
