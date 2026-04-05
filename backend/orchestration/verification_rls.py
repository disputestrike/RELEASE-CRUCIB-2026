"""
verification.rls — structural validation of multitenant RLS migration files on disk.

Live isolation is proven in tests/test_multitenancy_rls_live.py (asyncpg + real Postgres).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .multitenancy_rls_sql import MULTITENANCY_MIGRATION_FILENAME, validate_rls_syntax
from .verification_security import _pi


def _rls_candidate_files(migration_dir: str) -> List[str]:
    out: List[str] = []
    try:
        names = sorted(os.listdir(migration_dir))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".sql"):
            continue
        nl = name.lower()
        if MULTITENANCY_MIGRATION_FILENAME.lower() in nl or "rls" in nl or "multitenancy" in nl:
            out.append(name)
    return out


def verify_rls_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        return {"passed": False, "score": 0, "issues": ["No workspace for RLS verification"], "proof": proof}

    migration_dir = os.path.join(workspace_path, "db", "migrations")
    if not os.path.isdir(migration_dir):
        return {
            "passed": False,
            "score": 0,
            "issues": ["No db/migrations directory (expected generated multitenant RLS migration)"],
            "proof": proof,
        }

    candidates = _rls_candidate_files(migration_dir)
    if not candidates:
        return {
            "passed": False,
            "score": 0,
            "issues": [
                "No RLS migration file found (expect filename containing rls or multitenancy, "
                f"e.g. {MULTITENANCY_MIGRATION_FILENAME})",
            ],
            "proof": proof,
        }

    for rf in candidates:
        full = os.path.join(migration_dir, rf)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                sql = fh.read()
        except OSError as e:
            issues.append(f"Cannot read {rf}: {e}")
            continue
        res = validate_rls_syntax(sql)
        if not res["passed"]:
            for it in res["issues"]:
                issues.append(f"{rf}: {it}")
        else:
            proof.append(
                _pi(
                    "verification",
                    f"RLS migration structurally valid: {rf}",
                    {"check": "rls_syntax_valid", "file": rf, "status": "pass"},
                    verification_class="runtime",
                ),
            )

    score = 100 if not issues else max(40, 100 - len(issues) * 25)
    return {"passed": len(issues) == 0, "score": score, "issues": issues, "proof": proof}
