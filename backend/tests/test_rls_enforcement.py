"""
Structural RLS checks (validate_rls_syntax, verification.rls) — complements test_multitenancy_rls_live.py.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from orchestration.multitenancy_rls_sql import (
    migration_002_multitenancy_rls_sql,
    validate_rls_syntax,
)
from orchestration.verification_rls import verify_rls_workspace


def test_validate_rls_syntax_passes_on_generated_migration():
    sql = migration_002_multitenancy_rls_sql()
    res = validate_rls_syntax(sql)
    assert res["passed"] is True
    assert res["issues"] == []
    assert any((p.get("check") == "rls_syntax_valid") for p in res["proof"])


def test_validate_rls_syntax_fails_on_empty_sql():
    res = validate_rls_syntax("")
    assert res["passed"] is False
    assert res["issues"]


def test_validate_rls_syntax_fails_without_force_rls():
    bad = "ALTER TABLE app_items ENABLE ROW LEVEL SECURITY;\nCREATE POLICY p ON app_items FOR SELECT USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);\n"
    res = validate_rls_syntax(bad)
    assert res["passed"] is False
    assert any("FORCE" in i for i in res["issues"])


def test_verify_rls_workspace_finds_and_validates_migration_file():
    sql = migration_002_multitenancy_rls_sql()
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        path = os.path.join(mig, "002_multitenancy_rls.sql")
        with open(path, "w", encoding="utf-8") as f:
            f.write(sql)
        res = verify_rls_workspace(d)
        assert res["passed"] is True
        assert res["score"] == 100
        assert any(
            (p.get("payload") or {}).get("check") == "rls_syntax_valid"
            for p in res["proof"]
        )


def test_verify_rls_workspace_fails_without_migrations_dir():
    with tempfile.TemporaryDirectory() as d:
        res = verify_rls_workspace(d)
        assert res["passed"] is False
        assert res["score"] == 0
        assert any("db/migrations" in i for i in res["issues"])


def test_verify_rls_workspace_fails_when_no_rls_named_file():
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(os.path.join(mig, "001_only.sql"), "w", encoding="utf-8") as f:
            f.write("-- no rls\n")
        res = verify_rls_workspace(d)
        assert res["passed"] is False
        assert any("No RLS migration" in i for i in res["issues"])


@pytest.mark.asyncio
async def test_verifier_rls_step():
    from orchestration.verifier import verify_step

    sql = migration_002_multitenancy_rls_sql()
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(
            os.path.join(mig, "002_multitenancy_rls.sql"), "w", encoding="utf-8"
        ) as f:
            f.write(sql)
        out = await verify_step({"step_key": "verification.rls"}, workspace_path=d)
        assert out["passed"] is True
