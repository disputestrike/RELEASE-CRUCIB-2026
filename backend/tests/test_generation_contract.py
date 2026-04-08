import json
import os
import tempfile

import pytest

from orchestration.generation_contract import parse_generation_contract
from orchestration.planner import generate_plan
from orchestration.executor import handle_backend_route, handle_db_migration, handle_frontend_generate


FULL_SYSTEM_PROMPT = (
    "Build a multi-tenant SaaS with React frontend, Node backend, PostgreSQL, Redis caching, "
    "RabbitMQ queues, Stripe payments, SendGrid email, real-time WebSockets, Kubernetes deployment, "
    "Playwright tests, and API docs."
)


def test_parse_generation_contract_extracts_multistack_requirements():
    contract = parse_generation_contract(FULL_SYSTEM_PROMPT)

    assert contract["requires_full_system_builder"] is True
    assert "react" in contract["frontend_frameworks"]
    assert "node.js" in contract["backend_languages"]
    assert "postgresql" in contract["sql_databases"]
    assert "redis" in contract["cache"]
    assert "rabbitmq" in contract["queues"]
    assert "stripe" in contract["payments"]
    assert "sendgrid" in contract["notifications"]
    assert "websockets" in contract["realtime"]
    assert "kubernetes" in contract["deployment"]
    assert contract["recommended_build_target"] == "full_system_generator"


@pytest.mark.asyncio
async def test_generate_plan_includes_stack_contract_and_generation_mode():
    plan = await generate_plan(FULL_SYSTEM_PROMPT)

    assert plan["generation_mode"] == "full_system_builder"
    assert plan["recommended_build_target"] == "full_system_generator"
    assert plan["stack_contract"]["requires_full_system_builder"] is True
    assert any("Requested stack components" in row for row in plan["acceptance_criteria"])


@pytest.mark.asyncio
async def test_full_system_builder_writes_integrated_workspace(monkeypatch):
    import orchestration.plan_context as plan_context
    from agents.builder_agent import BuilderAgent

    async def fake_fetch_build_target(job_id):
        return "full_system_generator"

    async def fake_execute(self, context):
        return {
            "files": {
                "frontend/package.json": json.dumps({"name": "full-system-ui", "private": True}),
                "frontend/src/App.tsx": "export default function App(){ return <div>Ops Center</div>; }",
                "backend/server.js": "const express = require('express'); const app = express(); app.get('/health', (_req,res)=>res.json({status:'ok'})); module.exports = app;",
                "backend/routes/payments.js": "module.exports = {};",
                "db/migrations/001_init.sql": "create table accounts(id text primary key);",
                "infra/kubernetes/deployment.yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: ops-center\n",
                "tests/payments.test.js": "test('ok', () => expect(true).toBe(true));",
                "docs/API.md": "# API",
            },
            "api_spec": {"endpoints": [{"method": "GET", "path": "/health"}]},
            "setup_instructions": ["npm install", "node backend/server.js"],
            "_agent": "BuilderAgent",
            "_build_target": "full_system_generator",
        }

    monkeypatch.setattr(plan_context, "fetch_build_target_for_job", fake_fetch_build_target)
    monkeypatch.setattr(BuilderAgent, "execute", fake_execute)

    with tempfile.TemporaryDirectory() as d:
        result = await handle_frontend_generate(
            {"step_key": "frontend.scaffold"},
            {"id": "job-full-system", "goal": FULL_SYSTEM_PROMPT},
            d,
        )

        assert "frontend/src/App.tsx" in result["output_files"]
        assert "backend/server.js" in result["output_files"]
        assert "infra/kubernetes/deployment.yaml" in result["output_files"]
        manifest_path = os.path.join(d, ".crucibai", "full_system_build.json")
        assert os.path.isfile(manifest_path)

        backend = await handle_backend_route(
            {"step_key": "backend.routes"},
            {"id": "job-full-system", "goal": FULL_SYSTEM_PROMPT},
            d,
        )
        db = await handle_db_migration(
            {"step_key": "database.migration"},
            {"id": "job-full-system", "goal": FULL_SYSTEM_PROMPT},
            d,
        )

        assert "backend/server.js" in backend["output_files"]
        assert "db/migrations/001_init.sql" in db["output_files"]
        assert any(route["path"] == "/health" for route in backend["routes_added"])


@pytest.mark.asyncio
async def test_full_system_builder_critical_block_does_not_fall_back(monkeypatch):
    import orchestration.plan_context as plan_context
    from agents.builder_agent import BuilderAgent

    async def fake_fetch_build_target(job_id):
        return "full_system_generator"

    async def critical_block(self, context):
        return {"status": "❌ CRITICAL BLOCK", "reason": "requested stack was not generated"}

    monkeypatch.setattr(plan_context, "fetch_build_target_for_job", fake_fetch_build_target)
    monkeypatch.setattr(BuilderAgent, "execute", critical_block)

    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(RuntimeError, match="full_system_generation_blocked"):
            await handle_frontend_generate(
                {"step_key": "frontend.scaffold"},
                {"id": "job-full-system-fail", "goal": FULL_SYSTEM_PROMPT},
                d,
            )
        assert not os.path.exists(os.path.join(d, "package.json"))
