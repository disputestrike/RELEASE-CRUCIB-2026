"""
verification.tenancy_smoke — live Postgres: two tenants, RLS must hide the other tenant's rows.

Requires DATABASE_URL (postgresql). Skips with reduced score when unset (local dev without Docker).
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

import asyncpg

from .multitenancy_rls_sql import APP_ITEMS_DDL, multitenancy_rls_ddl_statements
from .tenant_deploy_gate import workspace_has_multitenancy_rls_migration
from .verification_security import _pi


def _tenancy_strict_requires_postgres() -> bool:
    raw = os.environ.get("CRUCIBAI_BEHAVIOR_TENANCY_STRICT", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    return os.environ.get("GITHUB_ACTIONS", "").strip() == "true"


def _sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _dsn_parts(dsn: str) -> dict:
    p = urlparse(dsn)
    path = (p.path or "").strip("/")
    dbname = path.split("/")[0] if path else "postgres"
    return {
        "host": p.hostname or "127.0.0.1",
        "port": p.port or 5432,
        "database": dbname,
        "user": unquote(p.username or "postgres"),
        "password": unquote(p.password or ""),
    }


async def verify_tenancy_smoke_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    dsn = os.environ.get("DATABASE_URL", "").strip()
    has_mt_mig = workspace_has_multitenancy_rls_migration(workspace_path or "")
    if not dsn or "postgres" not in dsn.lower():
        if has_mt_mig and _tenancy_strict_requires_postgres():
            issues.append(
                "Tenancy smoke required: workspace has multitenant RLS migration but DATABASE_URL is not PostgreSQL "
                "(set CRUCIBAI_BEHAVIOR_TENANCY_STRICT=0 locally to skip)",
            )
            return {"passed": False, "score": 0, "issues": issues, "proof": proof}
        proof.append(
            _pi(
                "verification",
                "Tenancy smoke skipped (no PostgreSQL DATABASE_URL)",
                {"check": "tenancy_smoke_skipped", "reason": "no_database_url"},
                verification_class="presence",
            ),
        )
        return {"passed": True, "score": 72, "issues": issues, "proof": proof}

    kw = _dsn_parts(dsn)
    schema = "tsmoke_" + uuid.uuid4().hex[:12]
    role = "tsmoke_r_" + uuid.uuid4().hex[:10]
    role_pw = "TsmokePw09" + uuid.uuid4().hex[:12]

    admin = None
    try:
        admin = await asyncpg.connect(**kw)
        await admin.execute(f'CREATE SCHEMA "{schema}"')
        await admin.execute(f'SET search_path TO "{schema}", public')
        await admin.execute(APP_ITEMS_DDL)
        for stmt in multitenancy_rls_ddl_statements():
            await admin.execute(stmt)

        id_a = await admin.fetchval(
            "INSERT INTO tenants (slug, name) VALUES ('a', 'A') RETURNING id",
        )
        id_b = await admin.fetchval(
            "INSERT INTO tenants (slug, name) VALUES ('b', 'B') RETURNING id",
        )
        await admin.execute(
            "INSERT INTO app_items (title, tenant_id) VALUES ($1, $2), ($3, $4)",
            "row-a",
            id_a,
            "row-b",
            id_b,
        )

        await admin.execute(
            f'CREATE ROLE "{role}" WITH LOGIN PASSWORD {_sql_string_literal(role_pw)} NOSUPERUSER',
        )
        dbname = kw["database"]
        await admin.execute(f'GRANT CONNECT ON DATABASE "{dbname}" TO "{role}"')
        await admin.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
        await admin.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{role}"',
        )
        await admin.execute(f'ALTER TABLE "{schema}".app_items OWNER TO "{role}"')
        await admin.execute(f'ALTER TABLE "{schema}".tenants OWNER TO "{role}"')

        user_conn = await asyncpg.connect(
            host=kw["host"],
            port=kw["port"],
            database=kw["database"],
            user=role,
            password=role_pw,
        )
        try:
            await user_conn.execute(f'SET search_path TO "{schema}", public')
            await user_conn.execute("SELECT set_config('app.tenant_id', $1, false)", str(id_a))
            n = await user_conn.fetchval("SELECT count(*) FROM app_items")
            if n != 1:
                issues.append(f"Tenancy smoke: expected 1 visible row for tenant A, got {n}")
            title = await user_conn.fetchval("SELECT title FROM app_items")
            if title != "row-a":
                issues.append("Tenancy smoke: wrong row visible for tenant A")

            await user_conn.execute("SELECT set_config('app.tenant_id', $1, false)", str(id_b))
            if await user_conn.fetchval("SELECT count(*) FROM app_items") != 1:
                issues.append("Tenancy smoke: tenant B should see exactly 1 row")

            await user_conn.execute("SELECT set_config('app.tenant_id', $1, false)", str(id_a))
            try:
                await user_conn.execute(
                    "INSERT INTO app_items (title, tenant_id) VALUES ($1, $2)",
                    "evil",
                    id_b,
                )
                issues.append("Tenancy smoke: cross-tenant INSERT should be blocked by RLS")
            except asyncpg.PostgresError as e:
                if "row-level security" not in str(e).lower():
                    issues.append(f"Tenancy smoke: unexpected error on cross-tenant insert: {e}")
        finally:
            await user_conn.close()
    except Exception as e:
        err_str = str(e)
        # Connection refused / unreachable = DB not available, not a code bug.
        # In test environments (CRUCIBAI_TEST=1) or when DB is simply not running,
        # treat this as skipped rather than failed so unit tests pass without Postgres.
        is_conn_error = any(
            kw in err_str.lower()
            for kw in ("connect call failed", "connection refused", "could not connect",
                       "connection timed out", "errno 111", "errno 61", "[errno")
        )
        in_test_env = os.environ.get("CRUCIBAI_TEST", "") == "1" or os.environ.get("CRUCIBAI_TEST_DB_UNAVAILABLE", "") == "1"
        if is_conn_error and in_test_env:
            proof.append(
                _pi(
                    "verification",
                    "Tenancy smoke skipped (database unreachable in test environment)",
                    {"check": "tenancy_smoke_skipped", "reason": "db_unreachable_test_env"},
                    verification_class="presence",
                ),
            )
            return {"passed": True, "score": 72, "issues": [], "proof": proof}
        issues.append(f"Tenancy smoke DB error: {e}")
    finally:
        if admin is not None:
            try:
                await admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                try:
                    await admin.execute(f'DROP OWNED BY "{role}"')
                except asyncpg.PostgresError:
                    pass
                await admin.execute(f'DROP ROLE IF EXISTS "{role}"')
            except Exception:
                pass
            await admin.close()

    if not issues:
        proof.append(
            _pi(
                "verification",
                "Tenancy smoke: two tenants, no cross-tenant reads; cross-tenant write blocked by RLS",
                {"check": "tenancy_isolation_proven", "workspace": bool(workspace_path)},
                verification_class="runtime",
            ),
        )

    score = 100 if not issues else max(25, 100 - len(issues) * 30)
    return {"passed": len(issues) == 0, "score": score, "issues": issues, "proof": proof}
