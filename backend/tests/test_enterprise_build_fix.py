import os
import tempfile

import pytest
from orchestration.executor import (
    handle_backend_route,
    handle_db_migration,
    handle_frontend_generate,
)
from orchestration.generated_app_template import build_frontend_file_set
from orchestration.preview_gate import verify_preview_workspace

HELIOS_PROMPT = """
AEGIS OMEGA BUILD — END-TO-END ELITE AUTONOMOUS SYSTEM TEST

Build a production-style multi-tenant enterprise platform named:
Helios Aegis Command

The system must support CRM, quoting, project workflow, AI recommendation,
rules and policy engine, immutable audit/compliance, analytics, background jobs,
integration adapters, deployment manifests, and proof-enforced validation.
Do not scaffold. Build the strongest honest version of the product.
""".strip()


def _workspace_files(base: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for root, _, filenames in os.walk(base):
        for filename in filenames:
            full = os.path.join(root, filename)
            rel = os.path.relpath(full, base).replace("\\", "/")
            with open(full, encoding="utf-8") as fh:
                files[rel] = fh.read()
    return files


def test_enterprise_frontend_template_builds_product_not_prompt_echo():
    files = dict(build_frontend_file_set({"goal": HELIOS_PROMPT}))

    assert "src/pages/PolicyPage.jsx" in files
    assert "src/pages/AnalyticsPage.jsx" in files
    assert "Helios Aegis Command" in files["src/pages/HomePage.jsx"]
    assert "Display name" in files["src/pages/LoginPage.jsx"]
    assert "Sign in (demo)" in files["src/pages/LoginPage.jsx"]
    assert "Dashboard" in files["src/pages/DashboardPage.jsx"]
    assert "MASTER EXECUTION DIRECTIVE" not in files["src/pages/HomePage.jsx"]
    assert (
        "You are an elite autonomous engineering" not in files["src/pages/HomePage.jsx"]
    )


@pytest.mark.asyncio
async def test_enterprise_frontend_handler_bypasses_generic_agent(monkeypatch):
    import orchestration.plan_context as plan_context
    from agents.frontend_agent import FrontendAgent

    async def should_not_run(self, context):  # pragma: no cover - failure guard
        raise AssertionError(
            "FrontendAgent should not run for enterprise command intent"
        )

    async def fake_fetch_build_target(job_id):
        return "fullstack"

    monkeypatch.setattr(FrontendAgent, "execute", should_not_run)
    monkeypatch.setattr(
        plan_context, "fetch_build_target_for_job", fake_fetch_build_target
    )
    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")

    with tempfile.TemporaryDirectory() as d:
        result = await handle_frontend_generate(
            {"step_key": "frontend.scaffold"},
            {"id": "job-helios-frontend", "goal": HELIOS_PROMPT},
            d,
        )

        files = _workspace_files(d)
        assert "src/pages/CRMPage.jsx" in result["output_files"]
        assert "src/pages/PolicyPage.jsx" in result["output_files"]
        assert "MASTER EXECUTION DIRECTIVE" not in files["src/pages/HomePage.jsx"]
        preview = await verify_preview_workspace(d)
        assert preview["passed"] is True, preview.get("issues")


@pytest.mark.asyncio
async def test_enterprise_backend_handler_writes_human_approval_api(monkeypatch):
    from agents.backend_agent import BackendAgent

    async def should_not_run(self, context):  # pragma: no cover - failure guard
        raise AssertionError(
            "BackendAgent should not run for enterprise command intent"
        )

    monkeypatch.setattr(BackendAgent, "execute", should_not_run)

    with tempfile.TemporaryDirectory() as d:
        result = await handle_backend_route(
            {"step_key": "backend.routes"},
            {"id": "job-helios-backend", "goal": HELIOS_PROMPT},
            d,
        )

        files = _workspace_files(d)
        main_py = files["backend/main.py"]
        assert "/api/quotes/{quote_id}/approve" in main_py
        assert "/api/policies/{policy_id}/enforce" in main_py
        assert "Explicit human approval role required" in main_py
        assert "CRUCIBAI_SECURITY_HEADERS" in main_py
        assert any(
            route["path"] == "/api/policies/{policy_id}/enforce"
            for route in result["routes_added"]
        )


@pytest.mark.asyncio
async def test_enterprise_database_handler_writes_enterprise_schema_and_seed():
    with tempfile.TemporaryDirectory() as d:
        migration = await handle_db_migration(
            {"step_key": "database.migration"},
            {"id": "job-helios-db", "goal": HELIOS_PROMPT},
            d,
        )
        seed = await handle_db_migration(
            {"step_key": "database.seed"},
            {"id": "job-helios-db", "goal": HELIOS_PROMPT},
            d,
        )

        files = _workspace_files(d)
        schema_sql = files["db/migrations/001_enterprise_command_schema.sql"]
        seed_sql = files["db/seeds/001_enterprise_seed.sql"]
        assert "CREATE TABLE IF NOT EXISTS organizations" in schema_sql
        assert "CREATE TABLE IF NOT EXISTS quotes" in schema_sql
        assert "pending_review" in schema_sql
        assert "Helios Aegis" in seed_sql
        assert (
            "db/migrations/001_enterprise_command_schema.sql"
            in migration["output_files"]
        )
        assert "db/seeds/001_enterprise_seed.sql" in seed["output_files"]
