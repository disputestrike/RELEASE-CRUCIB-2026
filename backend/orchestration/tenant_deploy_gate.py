"""
Deploy-time gate: multitenant RLS migrations require backend code to document / wire session GUC app.tenant_id.

Sketches must mention set_config (or asyncpg execute) with app.tenant_id so operators wire RLS before querying app_items.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from .multitenancy_rls_sql import MULTITENANCY_MIGRATION_FILENAME


def workspace_has_multitenancy_rls_migration(workspace_path: str) -> bool:
    if not workspace_path or not os.path.isdir(workspace_path):
        return False
    mig = os.path.join(workspace_path, "db", "migrations")
    if not os.path.isdir(mig):
        return False
    for name in os.listdir(mig):
        if name.lower() == MULTITENANCY_MIGRATION_FILENAME.lower():
            return True
        nl = name.lower()
        if nl.endswith(".sql") and ("multitenancy" in nl or "rls" in nl):
            try:
                with open(
                    os.path.join(mig, name), encoding="utf-8", errors="replace"
                ) as fh:
                    body = fh.read().lower()
            except OSError:
                continue
            if "row level security" in body and "app.tenant_id" in body:
                return True
    return False


def _collect_backend_py_text(workspace_path: str) -> str:
    root = os.path.join(workspace_path, "backend")
    if not os.path.isdir(root):
        return ""
    parts: List[str] = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if not n.endswith(".py"):
                continue
            p = os.path.join(dirpath, n)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    parts.append(fh.read())
            except OSError:
                continue
    return "\n".join(parts)


def tenant_context_gate_enabled() -> bool:
    raw = os.environ.get("CRUCIBAI_TENANT_CONTEXT_DEPLOY_GATE", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def verify_tenant_context_for_deploy(
    workspace_path: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Returns (issues, proof_rows) — issues non-empty should fail deploy.build verification.
    """
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not tenant_context_gate_enabled():
        proof.append(
            {
                "proof_type": "verification",
                "title": "Tenant GUC deploy gate disabled (CRUCIBAI_TENANT_CONTEXT_DEPLOY_GATE)",
                "payload": {"check": "tenant_context_gate_disabled"},
            },
        )
        return issues, proof

    if not workspace_has_multitenancy_rls_migration(workspace_path):
        proof.append(
            {
                "proof_type": "verification",
                "title": "No multitenant RLS migration — tenant session GUC gate skipped",
                "payload": {"check": "tenant_context_gate_skipped_no_rls_migration"},
            },
        )
        return issues, proof

    blob = _collect_backend_py_text(workspace_path)
    if not blob.strip():
        issues.append(
            "Multitenant RLS migration present but backend/*.py missing or empty — "
            "add FastAPI app with set_config('app.tenant_id', ...) before DB queries on app_items",
        )
        return issues, proof

    lo = blob.lower()
    if "set_config" not in lo:
        issues.append(
            "Multitenant workspace must reference PostgreSQL set_config (or equivalent) to set session GUC app.tenant_id",
        )
    if "app.tenant_id" not in blob:
        issues.append(
            "Multitenant workspace backend code must reference app.tenant_id (session GUC used by RLS policies)",
        )

    if not issues:
        proof.append(
            {
                "proof_type": "verification",
                "title": "Deploy gate: backend mentions tenant session GUC (set_config + app.tenant_id)",
                "payload": {"check": "tenant_context_guc_wired_in_backend_sketch"},
            },
        )
    return issues, proof
