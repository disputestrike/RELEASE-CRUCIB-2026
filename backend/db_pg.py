"""
PostgreSQL connection layer for CrucibAI.

Exposes a small document-style API on top of JSONB (e.g. db.users.find_one,
db.projects.insert_one) implemented with asyncpg. All application data lives
in PostgreSQL only — there is no MongoDB in this stack.

Schema: tables use (id TEXT PRIMARY KEY, doc JSONB NOT NULL) per 001_full_schema.sql.
"""

import os
import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)
_pool = None
_db = None

# Tables with composite primary keys (not just 'id')
COMPOSITE_PK_TABLES = {
    "agent_status": ["project_id", "agent_name"],
    "workspace_env": ["user_id"],
    "mfa_setup_temp": ["user_id"],
}

# Tables that use _id (legacy / JSONB-only)
LEGACY_ID_TABLES = {"backup_codes"}


async def get_pg_pool():
    """Return asyncpg pool, creating if needed."""
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    try:
        import asyncpg

        async def init_conn(conn):
            """Register JSONB codec so asyncpg returns dicts, not strings."""
            await conn.set_type_codec(
                "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
            )
            await conn.set_type_codec(
                "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
            )

        _pool = await asyncpg.create_pool(
            url, min_size=2, max_size=10, command_timeout=60, init=init_conn
        )
        logger.info("✅ PostgreSQL pool created with JSONB codec")
        return _pool
    except Exception as e:
        logger.error(f"❌ PostgreSQL pool failed: {e}")
        raise


async def close_pg_pool():
    """Close the global asyncpg pool."""
    global _pool, _db
    if _pool is not None:
        await _pool.close()
        _pool = None
        _db = None
        logger.info("✅ PostgreSQL pool closed")


def is_pg_available() -> bool:
    """Return True if DATABASE_URL is set."""
    return bool(os.environ.get("DATABASE_URL", "").strip())


# Aliases
get_pool = get_pg_pool


async def close_pool():
    await close_pg_pool()


class PGFindCursor:
    """Per-query find chain so concurrent handlers do not mutate shared PGCollection state."""

    __slots__ = (
        "_col",
        "_query",
        "_projection",
        "_sort_spec",
        "_skip_count",
        "_limit_count",
    )

    def __init__(
        self,
        col: "PGCollection",
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]],
    ):
        self._col = col
        self._query = dict(query or {})
        self._projection = projection
        self._sort_spec = None
        self._skip_count = 0
        self._limit_count = None

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            self._sort_spec = key_or_list
        else:
            self._sort_spec = [(key_or_list, direction)]
        return self

    def skip(self, count: int):
        self._skip_count = count
        return self

    def limit(self, count: int):
        self._limit_count = count
        return self

    async def to_list(self, length: int = None) -> List[Dict]:
        col = self._col
        async with col.pool.acquire() as conn:
            where_clause, params = col._build_where(self._query)
            select_cols = col._select_sql_columns()
            sql = f"SELECT {select_cols} FROM {col.table_name} WHERE {where_clause}"

            if self._sort_spec:
                order_parts = []
                for key, direction in self._sort_spec:
                    dir_str = "DESC" if direction == -1 else "ASC"
                    if key in ("created_at", "updated_at"):
                        order_parts.append(f"(doc->>'{key}') {dir_str}")
                    else:
                        order_parts.append(f"doc->'{key}' {dir_str}")
                sql += " ORDER BY " + ", ".join(order_parts)

            if self._skip_count:
                sql += f" OFFSET {self._skip_count}"
            if self._limit_count:
                sql += f" LIMIT {self._limit_count}"
            elif length:
                sql += f" LIMIT {length}"

            rows = await conn.fetch(sql, *params)
            docs = []
            for row in rows:
                doc = col._parse_doc(row["doc"])
                doc = col._attach_row_pk_to_doc(row, doc)
                docs.append(doc)

            if self._projection:
                docs = [col._apply_projection(doc, self._projection) for doc in docs]

            return docs


class PGCollection:
    """JSONB-backed collection for one PostgreSQL table (document-style access).

    All tables follow the schema:
        id TEXT PRIMARY KEY,
        doc JSONB NOT NULL DEFAULT '{}'

    Composite PK tables (agent_status, workspace_env) use their own PK columns.
    """

    def __init__(self, pool, table_name: str):
        self.pool = pool
        self.table_name = table_name

    def _select_sql_columns(self) -> str:
        if (
            self.table_name in COMPOSITE_PK_TABLES
            or self.table_name in LEGACY_ID_TABLES
        ):
            return "doc"
        if self.table_name == "referral_codes":
            return "code, doc"
        if self.table_name == "api_keys":
            return "key, doc"
        return "id, doc"

    def _attach_row_pk_to_doc(self, row, doc: Dict) -> Dict:
        if self.table_name == "referral_codes" and "code" in row:
            doc.setdefault("code", row["code"])
            doc.setdefault("id", row["code"])
        elif self.table_name == "api_keys" and "key" in row:
            doc.setdefault("key", row["key"])
            doc.setdefault("id", row["key"])
        elif "id" not in doc and "id" in row:
            doc["id"] = row["id"]
        return doc

    def _get_id_from_doc(self, doc: Dict) -> Optional[str]:
        """Extract the document ID - check 'id' first, then '_id'."""
        return doc.get("id") or doc.get("_id")

    def _parse_doc(self, raw) -> Dict:
        """Parse a JSONB value from asyncpg - may be str, dict, or None."""
        if raw is None:
            return {}
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {}
        if isinstance(raw, dict):
            return raw
        # asyncpg Record or other mapping
        try:
            return dict(raw)
        except Exception:
            return {}

    def _build_where(self, query: Dict[str, Any]) -> tuple:
        """Build WHERE clause from query dict. All fields are in doc JSONB."""
        if not query:
            return "TRUE", []

        def _is_numeric_scalar(v) -> bool:
            if isinstance(v, (int, float)):
                return True
            if isinstance(v, str):
                try:
                    float(v)
                    return True
                except ValueError:
                    return False
            return False

        conditions = []
        params = []
        param_idx = 1

        for key, value in query.items():
            # Special case: 'id' or '_id' maps to the actual PK column
            if key in ("id", "_id"):
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        if op == "$in":
                            placeholders = ", ".join(
                                [f"${param_idx + i}" for i in range(len(op_value))]
                            )
                            conditions.append(f"id IN ({placeholders})")
                            params.extend(op_value)
                            param_idx += len(op_value)
                        else:
                            conditions.append(f"id = ${param_idx}")
                            params.append(op_value)
                            param_idx += 1
                else:
                    conditions.append(f"id = ${param_idx}")
                    params.append(value)
                    param_idx += 1
            elif isinstance(value, dict):
                for op, op_value in value.items():
                    if op == "$eq":
                        if op_value is None:
                            conditions.append(f"(doc->'{key}') IS NULL")
                        elif isinstance(op_value, str):
                            conditions.append(f"(doc->>'{key}') = ${param_idx}")
                            params.append(op_value)
                            param_idx += 1
                        elif isinstance(op_value, (int, float)):
                            conditions.append(
                                f"(doc->>'{key}')::numeric = ${param_idx}::numeric"
                            )
                            params.append(op_value)
                            param_idx += 1
                        elif isinstance(op_value, bool):
                            conditions.append(
                                f"(doc->>'{key}')::boolean = ${param_idx}::boolean"
                            )
                            params.append(op_value)
                            param_idx += 1
                        else:
                            conditions.append(f"doc->'{key}' = ${param_idx}::jsonb")
                            params.append(json.dumps(op_value))
                            param_idx += 1
                    elif op == "$gte":
                        if _is_numeric_scalar(op_value):
                            conditions.append(
                                f"(doc->>'{key}')::numeric >= ${param_idx}::numeric"
                            )
                        else:
                            conditions.append(f"(doc->>'{key}') >= ${param_idx}")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$lte":
                        if _is_numeric_scalar(op_value):
                            conditions.append(
                                f"(doc->>'{key}')::numeric <= ${param_idx}::numeric"
                            )
                        else:
                            conditions.append(f"(doc->>'{key}') <= ${param_idx}")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$gt":
                        if _is_numeric_scalar(op_value):
                            conditions.append(
                                f"(doc->>'{key}')::numeric > ${param_idx}::numeric"
                            )
                        else:
                            conditions.append(f"(doc->>'{key}') > ${param_idx}")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$lt":
                        if _is_numeric_scalar(op_value):
                            conditions.append(
                                f"(doc->>'{key}')::numeric < ${param_idx}::numeric"
                            )
                        else:
                            conditions.append(f"(doc->>'{key}') < ${param_idx}")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$ne":
                        conditions.append(f"doc->'{key}' != ${param_idx}::jsonb")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$in":
                        placeholders = ", ".join(
                            [f"${param_idx + i}::jsonb" for i in range(len(op_value))]
                        )
                        conditions.append(f"doc->'{key}' IN ({placeholders})")
                        params.extend(op_value)
                        param_idx += len(op_value)
                    elif op == "$nin":
                        placeholders = ", ".join(
                            [f"${param_idx + i}::jsonb" for i in range(len(op_value))]
                        )
                        conditions.append(f"doc->'{key}' NOT IN ({placeholders})")
                        params.extend(op_value)
                        param_idx += len(op_value)
            else:
                if value is None:
                    conditions.append(f"(doc->'{key}') IS NULL")
                elif isinstance(value, str):
                    conditions.append(f"(doc->>'{key}') = ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif isinstance(value, (int, float)):
                    conditions.append(
                        f"(doc->>'{key}')::numeric = ${param_idx}::numeric"
                    )
                    params.append(value)
                    param_idx += 1
                elif isinstance(value, bool):
                    conditions.append(
                        f"(doc->>'{key}')::boolean = ${param_idx}::boolean"
                    )
                    params.append(value)
                    param_idx += 1
                else:
                    conditions.append(f"doc->'{key}' = ${param_idx}::jsonb")
                    params.append(value)
                    param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        return where_clause, params

    def _apply_update_operators(self, doc: Dict, update: Dict) -> Dict:
        """Apply document update operators ($set, $inc, etc.) on JSONB docs."""
        result = doc.copy()
        for op, changes in update.items():
            if op == "$set":
                result.update(changes)
            elif op == "$inc":
                for key, value in changes.items():
                    result[key] = result.get(key, 0) + value
            elif op == "$unset":
                for key in changes.keys():
                    result.pop(key, None)
            elif op == "$push":
                for key, value in changes.items():
                    if key not in result:
                        result[key] = []
                    if isinstance(result[key], list):
                        result[key].append(value)
            elif op == "$pull":
                for key, value in changes.items():
                    if key in result and isinstance(result[key], list):
                        result[key] = [v for v in result[key] if v != value]
        return result

    def _apply_projection(self, doc: Dict, projection: Dict) -> Dict:
        """Apply projection to document."""
        if not projection:
            return doc
        include_fields = [k for k, v in projection.items() if v == 1]
        if include_fields:
            return {k: doc.get(k) for k in include_fields if k in doc}
        exclude_fields = [k for k, v in projection.items() if v == 0]
        return {k: v for k, v in doc.items() if k not in exclude_fields}

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    async def find_one(
        self,
        query: Dict[str, Any] = None,
        projection: Dict = None,
        sort: Any = None,
    ) -> Optional[Dict]:
        """Find one document matching query. Optional sort: [(field, direction), ...] or (field, direction)."""
        query = query or {}
        async with self.pool.acquire() as conn:
            where_clause, params = self._build_where(query)
            select_cols = self._select_sql_columns()
            sql = f"SELECT {select_cols} FROM {self.table_name} WHERE {where_clause}"
            if sort:
                spec = sort if isinstance(sort, list) else [sort]
                order_parts = []
                for item in spec:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        key, direction = item[0], item[1]
                    else:
                        key, direction = item, -1
                    dir_str = "DESC" if direction == -1 else "ASC"
                    if key in ("created_at", "updated_at", "timestamp", "triggered_at"):
                        order_parts.append(f"(doc->>'{key}') {dir_str}")
                    else:
                        order_parts.append(f"doc->'{key}' {dir_str}")
                sql += " ORDER BY " + ", ".join(order_parts)
            sql += " LIMIT 1"
            row = await conn.fetchrow(sql, *params)
            if row:
                doc = self._parse_doc(row["doc"])
                doc = self._attach_row_pk_to_doc(row, doc)
                if projection:
                    doc = self._apply_projection(doc, projection)
                return doc
            return None

    def find(
        self, query: Dict[str, Any] = None, projection: Dict = None
    ) -> PGFindCursor:
        """Return an isolated cursor (safe under concurrent requests)."""
        return PGFindCursor(self, query or {}, projection)

    async def insert_one(self, document: Dict[str, Any]) -> Dict:
        """Insert a document into the table."""
        async with self.pool.acquire() as conn:
            if self.table_name == "referral_codes":
                pk = document.get("code") or self._generate_id()
                document["code"] = pk
                document.setdefault("id", pk)
                try:
                    await conn.execute(
                        "INSERT INTO referral_codes (code, doc) VALUES ($1, $2::jsonb)",
                        pk,
                        document,
                    )
                except Exception as e:
                    err = str(e).lower()
                    if "duplicate" in err or "unique" in err:
                        raise ValueError(f"Duplicate code: {pk}")
                    raise
                return {"_id": pk, "id": pk, "inserted_id": pk}
            if self.table_name == "api_keys":
                pk = document.get("key") or document.get("id") or self._generate_id()
                document["key"] = pk
                document.setdefault("id", pk)
                try:
                    await conn.execute(
                        "INSERT INTO api_keys (key, doc) VALUES ($1, $2::jsonb)",
                        pk,
                        document,
                    )
                except Exception as e:
                    err = str(e).lower()
                    if "duplicate" in err or "unique" in err:
                        raise ValueError(f"Duplicate key: {pk}")
                    raise
                return {"_id": pk, "id": pk, "inserted_id": pk}

        # Get or generate the id
        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            doc_id = self._generate_id()
            document["id"] = doc_id

        # Ensure doc has 'id' field
        document["id"] = doc_id

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    f"INSERT INTO {self.table_name} (id, doc) VALUES ($1, $2::jsonb)",
                    doc_id,
                    document,
                )
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "unique" in err:
                    raise ValueError(f"Duplicate id: {doc_id}")
                raise

        return {"_id": doc_id, "id": doc_id, "inserted_id": doc_id}

    async def insert_many(self, documents: List[Dict[str, Any]]) -> Dict:
        """Insert multiple documents."""
        ids = []
        async with self.pool.acquire() as conn:
            for doc in documents:
                doc_id = doc.get("id") or doc.get("_id") or self._generate_id()
                doc["id"] = doc_id
                try:
                    await conn.execute(
                        f"INSERT INTO {self.table_name} (id, doc) VALUES ($1, $2::jsonb)",
                        doc_id,
                        doc,
                    )
                    ids.append(doc_id)
                except Exception as e:
                    if (
                        "duplicate" not in str(e).lower()
                        and "unique" not in str(e).lower()
                    ):
                        raise
        return {"inserted_ids": ids}

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> Dict:
        """Update one document."""
        doc = await self.find_one(query)
        if not doc:
            return {"matched_count": 0, "modified_count": 0}

        updated_doc = self._apply_update_operators(doc, update)
        updated_doc["updated_at"] = datetime.utcnow().isoformat()

        doc_id = updated_doc.get("id") or updated_doc.get("_id")
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table_name} SET doc = $1::jsonb WHERE id = $2",
                updated_doc,
                doc_id,
            )

        return {"matched_count": 1, "modified_count": 1}

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> Dict:
        """Update multiple documents."""
        docs = await self.find(query).to_list()
        if not docs:
            return {"matched_count": 0, "modified_count": 0}

        modified = 0
        async with self.pool.acquire() as conn:
            for doc in docs:
                updated_doc = self._apply_update_operators(doc, update)
                updated_doc["updated_at"] = datetime.utcnow().isoformat()
                doc_id = updated_doc.get("id") or updated_doc.get("_id")
                await conn.execute(
                    f"UPDATE {self.table_name} SET doc = $1::jsonb WHERE id = $2",
                    updated_doc,
                    doc_id,
                )
                modified += 1

        return {"matched_count": len(docs), "modified_count": modified}

    async def delete_one(self, query: Dict[str, Any]) -> Dict:
        """Delete one document."""
        doc = await self.find_one(query)
        if not doc:
            return {"deleted_count": 0}

        doc_id = doc.get("id") or doc.get("_id")
        async with self.pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {self.table_name} WHERE id = $1", doc_id)

        return {"deleted_count": 1}

    async def delete_many(self, query: Dict[str, Any]) -> Dict:
        """Delete multiple documents."""
        docs = await self.find(query).to_list()
        if not docs:
            return {"deleted_count": 0}

        async with self.pool.acquire() as conn:
            for doc in docs:
                doc_id = doc.get("id") or doc.get("_id")
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE id = $1", doc_id
                )

        return {"deleted_count": len(docs)}

    async def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query."""
        query = query or {}
        async with self.pool.acquire() as conn:
            where_clause, params = self._build_where(query)
            sql = (
                f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_clause}"
            )
            row = await conn.fetchrow(sql, *params)
            return row["count"] if row else 0

    async def replace_one(
        self, query: Dict[str, Any], replacement: Dict[str, Any]
    ) -> Dict:
        """Replace one document."""
        doc = await self.find_one(query)
        if not doc:
            return {"matched_count": 0, "modified_count": 0}

        doc_id = doc.get("id") or doc.get("_id")
        replacement["id"] = doc_id
        replacement["updated_at"] = datetime.utcnow().isoformat()
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table_name} SET doc = $1::jsonb WHERE id = $2",
                replacement,
                doc_id,
            )

        return {"matched_count": 1, "modified_count": 1}


class PGDatabase:
    """Database facade over PostgreSQL JSONB tables."""

    def __init__(self, pool):
        self.pool = pool
        self._collections = {}

    def __getattr__(self, name: str) -> PGCollection:
        if name not in self._collections:
            self._collections[name] = PGCollection(self.pool, name)
        return self._collections[name]


def _strip_leading_sql_comments(fragment: str) -> str:
    """Remove blank lines and full-line -- comments so CREATE statements are not skipped."""
    if not fragment:
        return ""
    lines = fragment.splitlines()
    while lines:
        stripped = lines[0].strip()
        if not stripped or stripped.startswith("--"):
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


async def run_migrations():
    """Run all migration SQL files. Each statement runs independently — one failure won't block others."""
    pool = await get_pg_pool()
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    all_files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    for name in all_files:
        path = os.path.join(migrations_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            statements = [_strip_leading_sql_comments(s) for s in content.split(";")]
            ok = fail = 0
            for stmt in statements:
                if not stmt:
                    continue
                try:
                    async with pool.acquire() as conn:
                        await conn.execute(stmt)
                    ok += 1
                except Exception as e:
                    # Log but continue — don't let one table failure block the rest
                    logger.debug("Migration stmt skipped (%s): %s", name, str(e)[:120])
                    fail += 1
            logger.info("Migration %s: %d ok, %d skipped", name, ok, fail)
        except Exception as e:
            logger.warning("Migration %s failed to load: %s", name, e)


# All tables that must exist — used as safety net after migrations
REQUIRED_TABLES = [
    "users",
    "projects",
    "project_logs",
    "agent_status",
    "chat_history",
    "workspace_env",
    "token_ledger",
    "token_usage",
    "tasks",
    "saved_prompts",
    "user_agents",
    "agent_runs",
    "referral_codes",
    "referrals",
    "api_keys",
    "enterprise_inquiries",
    "contact_submissions",
    "backup_codes",
    "mfa_setup_temp",
    "shares",
    "blocked_requests",
    "agent_memory",
    "automation_tasks",
    "audit_log",
    "examples",
    "exports",
    "monitoring_events",
    # Blueprint modules
    "personas",
    "knowledge_sources",
    "knowledge_documents",
    "channels",
    "app_sessions",
    "session_messages",
    "claims_ledger",
    "safety_policies",
    "safety_audit_log",
    "tenants",
    "tenant_members",
    "workspace_invitations",
    "analytics_events",
    "session_metrics",
    "products",
    "orders",
    "app_db_schemas",
    # Auto-Runner / orchestration (relational, not JSONB doc store)
    "jobs",
    "job_steps",
    "job_events",
    "job_checkpoints",
    "proof_items",
    "build_plans",
]

ENSURE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS project_logs (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS agent_status (project_id TEXT NOT NULL, agent_name TEXT NOT NULL, doc JSONB NOT NULL DEFAULT '{}', PRIMARY KEY (project_id, agent_name));
CREATE TABLE IF NOT EXISTS chat_history (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS saved_prompts (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS workspace_env (user_id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS token_ledger (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS token_usage (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS user_agents (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS agent_runs (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS referral_codes (code TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS referrals (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS api_keys (key TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS enterprise_inquiries (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS contact_submissions (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS backup_codes (_id SERIAL PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS mfa_setup_temp (user_id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS shares (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS blocked_requests (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS agent_memory (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS automation_tasks (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS audit_log (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS examples (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS exports (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS monitoring_events (id SERIAL PRIMARY KEY, event_id TEXT NOT NULL, event_type TEXT NOT NULL, user_id TEXT NOT NULL, timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), duration FLOAT, metadata JSONB, success BOOLEAN DEFAULT TRUE, error_message TEXT);
CREATE TABLE IF NOT EXISTS personas (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS knowledge_sources (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS knowledge_documents (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS channels (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS app_sessions (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS session_messages (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS claims_ledger (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS safety_policies (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS safety_audit_log (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS tenant_members (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS workspace_invitations (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS analytics_events (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS session_metrics (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS app_db_schemas (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS user_skills (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
"""

# Relational orchestration tables (no FK to JSONB projects/users — avoids bootstrap ordering issues)
ORCHESTRATION_ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL DEFAULT '',
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    mode TEXT NOT NULL DEFAULT 'guided',
    goal TEXT NOT NULL DEFAULT '',
    current_phase TEXT DEFAULT 'planning',
    retry_count INTEGER DEFAULT 0,
    quality_score INTEGER DEFAULT 0,
    error_message TEXT,
    failure_reason TEXT,
    failure_details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
CREATE TABLE IF NOT EXISTS job_steps (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    step_key TEXT NOT NULL,
    agent_name TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    depends_on_json TEXT DEFAULT '[]',
    order_index INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    output_ref TEXT,
    verifier_status TEXT,
    verifier_score INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_status ON job_steps(status);
CREATE INDEX IF NOT EXISTS idx_job_steps_key ON job_steps(job_id, step_key);
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_strategy TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_explanation TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS workspace_fixed BOOLEAN DEFAULT FALSE;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS files_repaired TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_mutations_json TEXT DEFAULT '{}';
CREATE TABLE IF NOT EXISTS job_events (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    step_id TEXT,
    event_type TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(event_type);
CREATE TABLE IF NOT EXISTS job_checkpoints (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    checkpoint_key TEXT NOT NULL,
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (job_id, checkpoint_key)
);
CREATE INDEX IF NOT EXISTS idx_job_checkpoints_job ON job_checkpoints(job_id);
CREATE TABLE IF NOT EXISTS proof_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    step_id TEXT,
    proof_type TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_proof_items_job ON proof_items(job_id);
CREATE INDEX IF NOT EXISTS idx_proof_items_type ON proof_items(proof_type);
CREATE TABLE IF NOT EXISTS build_plans (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    project_id TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL DEFAULT '',
    plan_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_build_plans_job ON build_plans(job_id);
"""


async def ensure_all_tables():
    """Emergency safety net: create any missing tables. Runs after migrations."""
    pool = await get_pg_pool()
    combined = ENSURE_TABLES_SQL.strip() + "\n" + ORCHESTRATION_ENSURE_SQL.strip()
    statements = [s.strip() for s in combined.split(";") if s.strip()]
    ok = fail = 0
    for stmt in statements:
        try:
            async with pool.acquire() as conn:
                await conn.execute(stmt)
            ok += 1
        except Exception as e:
            logger.debug("ensure_tables stmt: %s", str(e)[:80])
            fail += 1
    logger.info("ensure_all_tables: %d created/verified, %d skipped", ok, fail)


async def get_db() -> PGDatabase:
    """Return the shared PostgreSQL-backed database instance."""
    global _db
    if _db is None:
        pool = await get_pg_pool()
        _db = PGDatabase(pool)
    return _db
