"""
Full PostgreSQL backend for CrucibAI (replaces MongoDB).
Motor-like API: db.users.find_one(), db.projects.insert_one(), etc.
Uses doc JSONB per table; DATABASE_URL required.
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
_pool = None

# Table config: (table_name, pk_columns for WHERE, optional serial_pk returned as _id)
TABLE_CONFIG = {
    "users": ("users", ["id"], None),
    "projects": ("projects", ["id"], None),
    "project_logs": ("project_logs", ["id"], None),
    "agent_status": ("agent_status", ["project_id", "agent_name"], None),
    "chat_history": ("chat_history", ["id"], None),
    "workspace_env": ("workspace_env", ["user_id"], None),
    "token_ledger": ("token_ledger", ["id"], None),
    "token_usage": ("token_usage", ["id"], None),
    "tasks": ("tasks", ["id"], None),
    "user_agents": ("user_agents", ["id"], None),
    "agent_runs": ("agent_runs", ["id"], None),
    "referral_codes": ("referral_codes", ["code"], None),
    "referrals": ("referrals", ["id"], None),
    "api_keys": ("api_keys", ["key"], None),
    "enterprise_inquiries": ("enterprise_inquiries", ["id"], None),
    "backup_codes": ("backup_codes", [], "_id"),  # serial _id
    "mfa_setup_temp": ("mfa_setup_temp", ["user_id"], None),
    "shares": ("shares", ["id"], None),
    "blocked_requests": ("blocked_requests", ["id"], None),
    "agent_memory": ("agent_memory", ["id"], None),
    "automation_tasks": ("automation_tasks", ["id"], None),
    "audit_log": ("audit_log", [], "_id"),  # serial _id, query by user_id + timestamp
    "examples": ("examples", ["id"], None),
}


def _doc_to_where(filter: Dict[str, Any], table: str) -> tuple:
    """Build WHERE clause and args from filter. Returns (where_sql, args_list)."""
    if not filter:
        return "TRUE", []
    parts = []
    args = []
    i = 0
    for k, v in filter.items():
        i += 1
        if table == "audit_log" and k == "user_id":
            parts.append(f"user_id = ${i}")
            args.append(str(v))
            continue
        if table == "audit_log" and k == "timestamp" and isinstance(v, dict):
            if "$gte" in v:
                parts.append(f"timestamp >= ${i}")
                args.append(v["$gte"])
            if "$lte" in v:
                i += 1
                parts.append(f"timestamp <= ${i}")
                args.append(v["$lte"])
            continue
        if table == "audit_log" and k == "action":
            parts.append(f"(doc->>'action') = ${i}")
            args.append(str(v))
            continue
        if table == "agent_status" and k in ("project_id", "agent_name"):
            parts.append(f"{k} = ${i}")
            args.append(str(v))
            continue
        if isinstance(v, dict):
            if "$gte" in v:
                parts.append(f"(doc->>'{k}') >= ${i}")
                args.append(v["$gte"])
            elif "$lte" in v:
                parts.append(f"(doc->>'{k}') <= ${i}")
                args.append(v["$lte"])
            elif "$in" in v:
                parts.append(f"(doc->>'{k}') = ANY(${i}::text[])")
                args.append([str(x) for x in v["$in"]])
            else:
                parts.append(f"(doc->>'{k}') = ${i}")
                args.append(str(v) if v is not None else None)
        else:
            if k == "_id" and table in ("backup_codes", "audit_log"):
                parts.append(f"_id = ${i}")
                args.append(v)
            else:
                parts.append(f"(doc->>'{k}') = ${i}")
                args.append(str(v) if v is not None else None)
    return " AND ".join(parts), args


def _projection_to_select(projection: Optional[Dict], doc_alias: "doc") -> str:
    """Return SELECT clause: either 'id, doc' or doc keys. We always need doc for the row."""
    if not projection:
        return "id, doc"
    if projection.get("_id") == 0 and len(projection) == 1:
        return "id, doc"
    # Include only projected keys from doc
    include = [k for k, v in projection.items() if v == 1 and k != "_id"]
    if not include:
        return "id, doc"
    # SELECT doc->>'k1' as k1, doc->>'k2' as k2, ...
    return "id, " + ", ".join(f"(doc->>'{k}') as \"{k}\"" for k in include)


class _Cursor:
    """Fake cursor for find().sort().skip().limit().to_list()."""

    def __init__(self, pool, table: str, filter: Dict, projection: Optional[Dict], conn_holder: list):
        self._pool = pool
        self._table = table
        self._filter = filter
        self._projection = projection
        self._conn_holder = conn_holder
        self._sort_field = None
        self._sort_dir = 1
        self._skip = 0
        self._limit = 100

    def sort(self, field: str, direction: int = 1):
        self._sort_field = field
        self._sort_dir = direction
        return self

    def skip(self, n: int):
        self._skip = n
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    async def to_list(self, length: int = 100):
        n = length if length is not None else self._limit
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name, pk_cols, serial_pk = config
        where_sql, args = _doc_to_where(self._filter, self._table)
        order = ""
        if self._sort_field:
            dir_sql = "DESC" if self._sort_dir == -1 else "ASC"
            order = f" ORDER BY (doc->>'{self._sort_field}') {dir_sql}"
        if serial_pk:
            # audit_log, backup_codes: order by _id or timestamp
            if table_name == "audit_log" and self._sort_field == "timestamp":
                order = f" ORDER BY timestamp {'DESC' if self._sort_dir == -1 else 'ASC'}"
            elif table_name == "audit_log":
                order = " ORDER BY timestamp DESC"
        q = f"SELECT id, doc FROM {table_name} WHERE {where_sql}{order} OFFSET {self._skip} LIMIT {n}"
        if table_name == "agent_status":
            q = f"SELECT project_id, agent_name, doc FROM {table_name} WHERE {where_sql}{order} OFFSET {self._skip} LIMIT {n}"
        if serial_pk:
            if table_name == "backup_codes":
                q = f"SELECT _id, doc FROM {table_name} WHERE {where_sql}{order} OFFSET {self._skip} LIMIT {n}"
            if table_name == "audit_log":
                q = f"SELECT _id, user_id, timestamp, doc FROM {table_name} WHERE {where_sql}{order} OFFSET {self._skip} LIMIT {n}"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(q, *args)
        out = []
        for r in rows:
            if table_name == "agent_status":
                doc = dict(r["doc"]) if r["doc"] else {}
                doc["project_id"] = r["project_id"]
                doc["agent_name"] = r["agent_name"]
                out.append(doc)
            elif serial_pk and table_name == "backup_codes":
                doc = dict(r["doc"]) if r["doc"] else {}
                doc["_id"] = r["_id"]
                out.append(doc)
            elif serial_pk and table_name == "audit_log":
                doc = dict(r["doc"]) if r["doc"] else {}
                doc["_id"] = r["_id"]
                doc["user_id"] = r["user_id"]
                doc["timestamp"] = r["timestamp"]
                out.append(doc)
            else:
                doc = dict(r["doc"]) if r["doc"] else {}
                doc["id"] = r["id"]
                out.append(doc)
        return out


class _PostgresCollection:
    def __init__(self, pool, table: str):
        self._pool = pool
        self._table = table

    async def find_one(self, filter: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name, pk_cols, serial_pk = config
        where_sql, args = _doc_to_where(filter, self._table)
        async with self._pool.acquire() as conn:
            if table_name == "agent_status":
                row = await conn.fetchrow(
                    f"SELECT project_id, agent_name, doc FROM {table_name} WHERE {where_sql} LIMIT 1",
                    *args
                )
            elif serial_pk and table_name == "backup_codes":
                row = await conn.fetchrow(
                    f"SELECT _id, doc FROM {table_name} WHERE {where_sql} LIMIT 1", *args
                )
            elif serial_pk and table_name == "audit_log":
                row = await conn.fetchrow(
                    f"SELECT _id, user_id, timestamp, doc FROM {table_name} WHERE {where_sql} LIMIT 1", *args
                )
            else:
                row = await conn.fetchrow(
                    f"SELECT id, doc FROM {table_name} WHERE {where_sql} LIMIT 1", *args
                )
            if not row:
                return None
            if table_name == "agent_status":
                doc = dict(row["doc"]) if row["doc"] else {}
                doc["project_id"] = row["project_id"]
                doc["agent_name"] = row["agent_name"]
                return doc
            if serial_pk and table_name == "backup_codes":
                doc = dict(row["doc"]) if row["doc"] else {}
                doc["_id"] = row["_id"]
                return doc
            if serial_pk and table_name == "audit_log":
                doc = dict(row["doc"]) if row["doc"] else {}
                doc["_id"] = row["_id"]
                doc["user_id"] = row["user_id"]
                doc["timestamp"] = row["timestamp"]
                return doc
            doc = dict(row["doc"]) if row["doc"] else {}
            doc["id"] = row["id"]
            if projection and projection.get("_id") == 0 and len(projection) == 1:
                doc.pop("_id", None)
            return doc

    def find(self, filter: Dict, projection: Optional[Dict] = None):
        return _Cursor(self._pool, self._table, filter, projection, [])

    async def insert_one(self, doc: Dict) -> Any:
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name, pk_cols, serial_pk = config
        doc = {k: v for k, v in doc.items() if v is not None}
        if table_name == "agent_status":
            project_id = doc.get("project_id")
            agent_name = doc.get("agent_name")
            await self._pool.execute(
                f"INSERT INTO {table_name} (project_id, agent_name, doc) VALUES ($1, $2, $3::jsonb)"
                " ON CONFLICT (project_id, agent_name) DO UPDATE SET doc = EXCLUDED.doc",
                project_id, agent_name, json.dumps(doc)
            )
            return None
        if serial_pk and table_name == "backup_codes":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"INSERT INTO {table_name} (doc) VALUES ($1::jsonb) RETURNING _id",
                    json.dumps(doc)
                )
            return type("Result", (), {"inserted_id": row["_id"]})()
        if serial_pk and table_name == "audit_log":
            user_id = doc.get("user_id", "")
            ts = doc.get("timestamp")
            if hasattr(ts, "isoformat"):
                ts = ts.isoformat()
            row = await self._pool.fetchrow(
                """INSERT INTO audit_log (user_id, timestamp, doc) VALUES ($1, $2::timestamptz, $3::jsonb) RETURNING _id""",
                user_id, ts or "now()", json.dumps(doc)
            )
            return type("Result", (), {"inserted_id": row["_id"]})()
        pk_col = "id"
        if table_name == "workspace_env":
            pk_col = "user_id"
        elif table_name == "referral_codes":
            pk_col = "code"
        pk = doc.get(pk_col) or doc.get("id")
        if not pk and table_name in ("examples",):
            import uuid
            pk = str(uuid.uuid4())
            doc["id"] = pk
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {table_name} ({pk_col}, doc) VALUES ($1, $2::jsonb)"
                f" ON CONFLICT ({pk_col}) DO UPDATE SET doc = EXCLUDED.doc",
                pk, json.dumps(doc)
            )
        return type("Result", (), {"inserted_id": pk})()

    async def update_one(self, filter: Dict, update: Dict, upsert: bool = False) -> None:
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name, pk_cols, serial_pk = config
        where_sql, where_args = _doc_to_where(filter, self._table)
        set_parts = []
        set_args = []
        i = 0
        if "$set" in update:
            for k, v in update["$set"].items():
                i += 1
                set_parts.append(f"doc = jsonb_set(doc, '{{{k}}}', ${i}::jsonb)")
                set_args.append(json.dumps(v, default=str) if v is not None else None)
        if "$inc" in update:
            for k, v in update["$inc"].items():
                i += 1
                set_parts.append(
                    f"doc = jsonb_set(doc, '{{{k}}}', to_jsonb((COALESCE((doc->>'{k}')::numeric, 0) + ${i})::text))"
                )
                set_args.append(v)
        if not set_parts:
            return
        args = set_args + where_args
        q = f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE {where_sql}"
        async with self._pool.acquire() as conn:
            await conn.execute(q, *args)

    async def delete_one(self, filter: Dict) -> None:
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name = config[0]
        where_sql, args = _doc_to_where(filter, self._table)
        async with self._pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {table_name} WHERE {where_sql}", *args)

    async def delete_many(self, filter: Dict) -> None:
        where_sql, args = _doc_to_where(filter, self._table)
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name = config[0]
        async with self._pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {table_name} WHERE {where_sql}", *args)

    async def count_documents(self, filter: Dict) -> int:
        where_sql, args = _doc_to_where(filter, self._table)
        config = TABLE_CONFIG.get(self._table, (self._table, ["id"], None))
        table_name = config[0]
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT COUNT(*) as c FROM {table_name} WHERE {where_sql}", *args
            )
        return row["c"] or 0


class _PostgresDB:
    """Motor-like db: db.users, db.projects, ..."""

    def __init__(self, pool):
        self._pool = pool

    def __getattr__(self, name: str) -> _PostgresCollection:
        if name in TABLE_CONFIG:
            return _PostgresCollection(self._pool, name)
        raise AttributeError(name)


async def get_pool():
    """Create or return asyncpg pool. Requires DATABASE_URL."""
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required. Set it in .env (PostgreSQL connection string).")
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(url, min_size=2, max_size=10, command_timeout=60)
        logger.info("PostgreSQL pool created (full migration mode).")
        return _pool
    except Exception as e:
        logger.exception("PostgreSQL pool creation failed: %s", e)
        raise


async def init_schema(pool) -> bool:
    """Run 001_full_schema.sql."""
    path = os.path.join(os.path.dirname(__file__), "migrations", "001_full_schema.sql")
    if not os.path.isfile(path):
        logger.warning("Schema file not found: %s", path)
        return False
    try:
        with open(path, "r") as f:
            sql = f.read()
        async with pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("PostgreSQL full schema initialized.")
        return True
    except Exception as e:
        logger.exception("Schema init failed: %s", e)
        return False


_db: Optional[_PostgresDB] = None


async def get_db() -> _PostgresDB:
    """Return Motor-like db (Postgres-backed). Call after get_pool() and init_schema()."""
    global _db
    if _db is not None:
        return _db
    pool = await get_pool()
    await init_schema(pool)
    _db = _PostgresDB(pool)
    return _db


async def close_pool():
    global _pool, _db
    _db = None
    if _pool:
        await _pool.close()
        _pool = None
    logger.info("PostgreSQL pool closed.")
