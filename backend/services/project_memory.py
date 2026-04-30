"""Per-project persistent memory (JSONB K/V over asyncpg).

Used anywhere long-lived project state must survive across sessions:
- Project-level defaults ("default_currency": "EUR")
- Learned user preferences per project
- Pinned project context the agents should always reload

Values are stored as JSONB so callers can stash any JSON-serializable Python
object (dict, list, number, bool, str, None).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProjectMemory:
    """Async K/V memory scoped to a project_id."""

    def __init__(self, pool):
        if pool is None:
            raise ValueError("ProjectMemory requires an asyncpg pool, got None")
        self._pool = pool

    async def set(self, project_id: str, key: str, value: Any) -> None:
        """Upsert a key/value pair. Overwrites on conflict."""
        payload = json.dumps(value)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO project_memory (project_id, key, value, updated_at)
                VALUES ($1, $2, $3::jsonb, NOW())
                ON CONFLICT (project_id, key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                project_id,
                key,
                payload,
            )

    async def get(self, project_id: str, key: str) -> Optional[Any]:
        """Return the value, or None if absent."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM project_memory WHERE project_id = $1 AND key = $2",
                project_id,
                key,
            )
        if row is None:
            return None
        v = row["value"]
        return v if not isinstance(v, str) else json.loads(v)

    async def list(self, project_id: str) -> dict[str, Any]:
        """Return all key/value pairs for a project."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value, updated_at FROM project_memory WHERE project_id = $1 ORDER BY key",
                project_id,
            )
        out: dict[str, Any] = {}
        for r in rows:
            v = r["value"]
            out[r["key"]] = v if not isinstance(v, str) else json.loads(v)
        return out

    async def delete(self, project_id: str, key: str) -> bool:
        """Delete a key. Returns True if a row was removed."""
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM project_memory WHERE project_id = $1 AND key = $2",
                project_id,
                key,
            )
        # asyncpg returns "DELETE <n>"
        try:
            n = int(str(res).rsplit(" ", 1)[-1])
        except Exception:
            n = 0
        return n > 0

    async def keys(self, project_id: str) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key FROM project_memory WHERE project_id = $1 ORDER BY key",
                project_id,
            )
        return [r["key"] for r in rows]


# Process-wide instance wired on first call
_mem: Optional[ProjectMemory] = None


async def get_project_memory() -> ProjectMemory:
    global _mem
    if _mem is not None:
        return _mem
    from ....db_pg import get_pg_pool
    pool = await get_pg_pool()
    _mem = ProjectMemory(pool)
    return _mem
