"""Behavioral verification: bundled into verification.security; planner deploy gate; helpers."""
import os
import tempfile

import pytest

from orchestration.planner import generate_plan
from orchestration.verification_stripe_replay import verify_stripe_replay_workspace


def test_stripe_replay_proves_idempotency():
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(os.path.join(mig, "003_stripe.sql"), "w", encoding="utf-8") as f:
            f.write("CREATE TABLE IF NOT EXISTS stripe_events_processed (id TEXT PRIMARY KEY);\n")
        r = verify_stripe_replay_workspace(d)
        assert r["passed"] is True
        assert any((p.get("payload") or {}).get("check") == "stripe_webhook_idempotency_proven" for p in r["proof"])


@pytest.mark.asyncio
async def test_rbac_verification_skips_without_url():
    from orchestration.verification_rbac import verify_rbac_enforcement_workspace

    r = await verify_rbac_enforcement_workspace("/tmp/nonexistent-workspace-xyz")
    assert r["passed"] is True
    assert any((p.get("payload") or {}).get("check") == "rbac_smoke_skipped" for p in r["proof"])


@pytest.mark.asyncio
async def test_planner_deploy_depends_only_on_security():
    plan = await generate_plan("Build a simple todo app with React")
    deploy = next(p for p in plan["phases"] if p["key"] == "deploy")
    db = next(s for s in deploy["steps"] if s["key"] == "deploy.build")
    assert db["depends_on"] == ["verification.security"]
    ver_phase = next(p for p in plan["phases"] if p["key"] == "verification")
    keys = [s["key"] for s in ver_phase["steps"]]
    assert "verification.rbac_enforcement" not in keys
    assert "verification.tenancy_smoke" not in keys


@pytest.mark.asyncio
async def test_planner_multitenant_stripe_same_security_gate():
    plan = await generate_plan(
        "Multi-tenant B2B SaaS with Postgres RLS and Stripe subscriptions",
        project_state={"env_vars": {"STRIPE_SECRET_KEY": "x"}},
    )
    deploy = next(s for s in next(p for p in plan["phases"] if p["key"] == "deploy")["steps"] if s["key"] == "deploy.build")
    assert deploy["depends_on"] == ["verification.security"]


@pytest.mark.asyncio
async def test_tenancy_smoke_runs_with_database_url():
    """Uses DATABASE_URL when PostgreSQL is available (conftest / CI)."""
    from orchestration.verification_tenancy_smoke import verify_tenancy_smoke_workspace

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn or "postgres" not in dsn.lower():
        pytest.skip("PostgreSQL DATABASE_URL required for live tenancy smoke")
    r = await verify_tenancy_smoke_workspace(".")
    assert r["passed"] is True
    assert any((p.get("payload") or {}).get("check") == "tenancy_isolation_proven" for p in r["proof"])


@pytest.mark.asyncio
async def test_verify_step_security_merges_behavior_bundle():
    """Main pipeline: verification.security runs security + RLS files + tenancy/stripe/rbac bundle."""
    from orchestration.verifier import verify_step

    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(os.path.join(mig, "001.sql"), "w", encoding="utf-8") as f:
            f.write("SELECT 1;\n")
        with open(os.path.join(mig, "stripe.sql"), "w", encoding="utf-8") as f:
            f.write("CREATE TABLE stripe_events_processed (id TEXT PRIMARY KEY);\n")
        os.makedirs(os.path.join(d, "backend"))
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")
        with open(os.path.join(d, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies":{"react":"18"},"engines":{"node":">=18"}}\n')
        out = await verify_step({"step_key": "verification.security"}, workspace_path=d)
        assert out["passed"] is True
        checks = {(p.get("payload") or {}).get("check") for p in out["proof"]}
        assert "stripe_webhook_idempotency_proven" in checks
        assert "migrations_read" in checks or "tenancy_sql_sketch" in checks


@pytest.mark.asyncio
async def test_tenancy_strict_fails_without_postgres_when_migration_present(monkeypatch):
    from orchestration.verification_tenancy_smoke import verify_tenancy_smoke_workspace

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CRUCIBAI_BEHAVIOR_TENANCY_STRICT", "1")
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(os.path.join(mig, "002_multitenancy_rls.sql"), "w", encoding="utf-8") as f:
            f.write("ALTER TABLE x ENABLE ROW LEVEL SECURITY;\n")
        r = await verify_tenancy_smoke_workspace(d)
        assert r["passed"] is False
        assert any("DATABASE_URL" in i for i in r["issues"])
