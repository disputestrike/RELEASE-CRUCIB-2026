"""
Live PostgreSQL RLS tests for Auto-Runner multitenant migration DDL.

Uses DATABASE_URL (same DB as backend tests). Creates an isolated schema and role, then drops them.
Runs on asyncpg (no psycopg2 required for Python 3.13+).
"""
from __future__ import annotations

import os
import uuid
from urllib.parse import unquote, urlparse

import asyncpg
import pytest

from orchestration.multitenancy_rls_sql import (
    APP_ITEMS_DDL,
    migration_002_multitenancy_rls_sql,
    multitenancy_rls_ddl_statements,
)


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


def test_generated_migration_includes_live_rls_policies():
    body = migration_002_multitenancy_rls_sql()
    assert "FORCE ROW LEVEL SECURITY" in body
    assert "CREATE POLICY app_items_select" in body
    assert "CREATE POLICY app_items_insert" in body
    assert "current_setting('app.tenant_id', true)" in body


@pytest.mark.asyncio
async def test_rls_isolates_rows_and_blocks_cross_tenant_writes():
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        pytest.skip("DATABASE_URL not set")

    kw = _dsn_parts(dsn)
    schema = "rls_t_" + uuid.uuid4().hex[:12]
    role = "rls_r_" + uuid.uuid4().hex[:10]
    role_pw = "RlsTestPw09" + uuid.uuid4().hex[:12]

    admin = await asyncpg.connect(**kw)
    try:
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

            await user_conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)",
                str(id_a),
            )
            n = await user_conn.fetchval("SELECT count(*) FROM app_items")
            assert n == 1
            title = await user_conn.fetchval("SELECT title FROM app_items")
            assert title == "row-a"

            await user_conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)",
                str(id_b),
            )
            assert await user_conn.fetchval("SELECT count(*) FROM app_items") == 1

            await user_conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)",
                str(id_a),
            )
            with pytest.raises(asyncpg.PostgresError) as ei:
                await user_conn.execute(
                    "INSERT INTO app_items (title, tenant_id) VALUES ($1, $2)",
                    "evil",
                    id_b,
                )
            assert "row-level security" in str(ei.value).lower()
        finally:
            await user_conn.close()

    finally:
        await admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        try:
            await admin.execute(f'DROP OWNED BY "{role}"')
        except asyncpg.PostgresError:
            pass
        await admin.execute(f'DROP ROLE IF EXISTS "{role}"')
        await admin.close()
