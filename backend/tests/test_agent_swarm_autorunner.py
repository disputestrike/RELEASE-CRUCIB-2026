import tempfile

import pytest

from agent_dag import AGENT_DAG
from orchestration.executor import _get_handler, handle_agent_swarm_step
from orchestration.planner import generate_plan
from orchestration.swarm_agent_runner import (
    build_agent_swarm_phases,
    run_swarm_agent_step,
    swarm_step_key,
    uses_agent_swarm,
)


FULL_SYSTEM_PROMPT = (
    "Build a multi-tenant SaaS with React frontend, Node backend, PostgreSQL, Redis caching, "
    "RabbitMQ queues, Stripe payments, SendGrid email, real-time WebSockets, Kubernetes deployment."
)

HELIOS_PROMPT = (
    "Build Helios Aegis Command: a multi-tenant operations SaaS with CRM, quote workflow, "
    "project workflow, policy engine, immutable audit, analytics, background jobs, and tenant isolation."
)


@pytest.mark.asyncio
async def test_generate_plan_uses_agent_swarm_for_multistack_prompt():
    plan = await generate_plan(FULL_SYSTEM_PROMPT)

    assert plan["orchestration_mode"] == "agent_swarm"
    assert uses_agent_swarm(FULL_SYSTEM_PROMPT, plan["stack_contract"]) is True
    flat_keys = [step["key"] for phase in plan["phases"] for step in phase["steps"]]
    assert swarm_step_key("Frontend Generation") in flat_keys
    assert swarm_step_key("Backend Generation") in flat_keys
    assert "frontend.scaffold" not in flat_keys


@pytest.mark.asyncio
async def test_generate_plan_uses_agent_swarm_for_helios_prompt():
    plan = await generate_plan(HELIOS_PROMPT)

    assert plan["orchestration_mode"] == "agent_swarm"
    flat_keys = [step["key"] for phase in plan["phases"] for step in phase["steps"]]
    assert swarm_step_key("Planner") in flat_keys
    assert swarm_step_key("Design Agent") in flat_keys
    assert swarm_step_key("Queue Agent") in flat_keys


def test_build_agent_swarm_phases_cover_every_agent_once():
    phases = build_agent_swarm_phases()
    flat_agents = [step["agent"] for phase in phases for step in phase["steps"]]

    assert len(flat_agents) == len(AGENT_DAG)
    assert len(flat_agents) == len(set(flat_agents))
    assert set(flat_agents) == set(AGENT_DAG.keys())


def test_get_handler_routes_agents_prefix_to_swarm_handler():
    assert _get_handler("agents.frontend_generation") is handle_agent_swarm_step


@pytest.mark.asyncio
async def test_run_swarm_agent_step_rejects_core_fallback(monkeypatch):
    async def fake_server_runner(**kwargs):
        return {"status": "failed_with_fallback", "reason": "llm failed", "output": "placeholder"}

    monkeypatch.setattr(
        "orchestration.swarm_agent_runner._run_server_swarm_agent",
        fake_server_runner,
    )

    step = {
        "id": "step-1",
        "step_key": swarm_step_key("Frontend Generation"),
        "agent_name": "Frontend Generation",
        "order_index": 1,
    }
    job = {"id": "job-1", "project_id": "proj-1", "user_id": "user-1", "goal": FULL_SYSTEM_PROMPT}

    with tempfile.TemporaryDirectory() as workspace:
        with pytest.raises(RuntimeError, match="swarm_agent_failed:Frontend Generation"):
            await run_swarm_agent_step(step, job, workspace)
