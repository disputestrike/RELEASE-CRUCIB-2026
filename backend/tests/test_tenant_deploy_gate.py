"""Deploy gate: multitenant RLS migration requires backend to mention set_config + app.tenant_id."""

import os
import tempfile

from orchestration.multitenancy_rls_sql import migration_002_multitenancy_rls_sql
from orchestration.tenant_deploy_gate import (
    tenant_context_gate_enabled,
    verify_tenant_context_for_deploy,
    workspace_has_multitenancy_rls_migration,
)


def test_workspace_detects_multitenancy_migration_file():
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(
            os.path.join(mig, "002_multitenancy_rls.sql"), "w", encoding="utf-8"
        ) as f:
            f.write(migration_002_multitenancy_rls_sql())
        assert workspace_has_multitenancy_rls_migration(d) is True


def test_gate_fails_without_backend_tenant_guc_hints(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_TENANT_CONTEXT_DEPLOY_GATE", "1")
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(
            os.path.join(mig, "002_multitenancy_rls.sql"), "w", encoding="utf-8"
        ) as f:
            f.write(migration_002_multitenancy_rls_sql())
        os.makedirs(os.path.join(d, "backend"))
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write("print('no db')\n")
        issues, _ = verify_tenant_context_for_deploy(d)
        assert issues


def test_gate_passes_with_sketch_hints(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_TENANT_CONTEXT_DEPLOY_GATE", "1")
    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(
            os.path.join(mig, "002_multitenancy_rls.sql"), "w", encoding="utf-8"
        ) as f:
            f.write(migration_002_multitenancy_rls_sql())
        os.makedirs(os.path.join(d, "backend"))
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write(
                "# await conn.execute(\"SELECT set_config('app.tenant_id', $1, true)\", tid)\n"
                'X = "app.tenant_id"\n',
            )
        issues, proof = verify_tenant_context_for_deploy(d)
        assert not issues
        assert any(
            (p.get("payload") or {}).get("check")
            == "tenant_context_guc_wired_in_backend_sketch"
            for p in proof
        )


def test_gate_disabled(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_TENANT_CONTEXT_DEPLOY_GATE", "0")
    assert tenant_context_gate_enabled() is False
