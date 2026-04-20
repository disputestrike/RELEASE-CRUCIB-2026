"""
backend/services/memory_store.py
─────────────────────────────────
Canonical memory façade with explicit scope enum.

Spec: J – Memory Store
Branch: engineering/master-list-closeout

Design:
  • MemoryScope enum: user | project | workflow | migration
  • Delegates to MemoryService (vector store) + direct `memories` table
  • Stores coding conventions, architecture preferences, naming, etc.
  • Retrieve before planning; write back after confirmed runs
  • Show what memory was used; allow delete / edit
"""

from __future__ import annotations

import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# J. Memory Scopes
# ─────────────────────────────────────────────────────────────────────────────

class MemoryScope(str, Enum):
    USER      = "user"       # cross-project user preferences
    PROJECT   = "project"    # per-project conventions
    WORKFLOW  = "workflow"   # per-thread / per-run ephemeral context
    MIGRATION = "migration"  # migration run preferences and preferences


# Well-known keys the agent loop reads before planning
CONVENTION_KEYS = [
    "coding_conventions",
    "architecture_preferences",
    "naming_conventions",
    "folder_conventions",
    "ui_preferences",
    "preferred_stacks",
    "deployment_defaults",
    "review_preferences",
    "migration_preferences",
]


# ─────────────────────────────────────────────────────────────────────────────
# MemoryStore
# ─────────────────────────────────────────────────────────────────────────────

class MemoryStore:
    """Unified memory store façade.

    Uses the `memories` table (migration 012) for structured key/value memory
    and falls back to MemoryService (vector store) for semantic retrieval.
    """

    def __init__(self) -> None:
        self._svc: Any = None

    def _get_svc(self):
        if self._svc is None:
            try:
                from memory.service import MemoryService
                self._svc = MemoryService()
            except Exception:
                self._svc = None
        return self._svc

    # ── Write ─────────────────────────────────────────────────────────────────

    async def set(
        self,
        *,
        user_id: str,
        scope: MemoryScope | str,
        key: str,
        value: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Any,
    ) -> str:
        """Upsert a memory entry."""
        if isinstance(scope, str):
            scope = MemoryScope(scope)
        memory_id = str(uuid.uuid4())
        now = __import__("datetime").datetime.utcnow().isoformat()
        await db.execute(
            """INSERT INTO memories (id, user_id, project_id, scope, key, value, metadata, created_at, updated_at)
               VALUES (:id, :user_id, :project_id, :scope, :key, :value, :metadata::jsonb, :now, :now)
               ON CONFLICT (user_id, scope, key) DO UPDATE
               SET value = EXCLUDED.value,
                   metadata = EXCLUDED.metadata,
                   updated_at = EXCLUDED.updated_at""",
            {
                "id": memory_id,
                "user_id": user_id,
                "project_id": project_id,
                "scope": scope.value,
                "key": key,
                "value": value,
                "metadata": __import__("json").dumps(metadata or {}),
                "now": now,
            },
        )
        return memory_id

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get(
        self,
        *,
        user_id: str,
        scope: MemoryScope | str,
        key: str,
        project_id: Optional[str] = None,
        db: Any,
    ) -> Optional[str]:
        """Retrieve a single memory value."""
        if isinstance(scope, str):
            scope = MemoryScope(scope)
        row = await db.fetch_one(
            """SELECT value FROM memories
               WHERE user_id = :user_id AND scope = :scope AND key = :key
               LIMIT 1""",
            {"user_id": user_id, "scope": scope.value, "key": key},
        )
        return row["value"] if row else None

    async def get_all(
        self,
        *,
        user_id: str,
        scope: Optional[MemoryScope | str] = None,
        project_id: Optional[str] = None,
        db: Any,
    ) -> List[Dict[str, Any]]:
        """List all memory entries for a user, optionally filtered by scope."""
        params: Dict[str, Any] = {"user_id": user_id}
        where = "user_id = :user_id"
        if scope:
            if isinstance(scope, str):
                scope = MemoryScope(scope)
            where += " AND scope = :scope"
            params["scope"] = scope.value
        if project_id:
            where += " AND project_id = :project_id"
            params["project_id"] = project_id
        rows = await db.fetch_all(
            f"SELECT * FROM memories WHERE {where} ORDER BY scope, key",
            params,
        )
        return [dict(r) for r in rows]

    async def get_conventions(
        self,
        *,
        user_id: str,
        project_id: Optional[str] = None,
        db: Any,
    ) -> Dict[str, str]:
        """Retrieve all convention keys across user + project scopes.
        Used by AgentLoop before planning.
        """
        result: Dict[str, str] = {}
        for scope in [MemoryScope.USER, MemoryScope.PROJECT]:
            entries = await self.get_all(user_id=user_id, scope=scope, project_id=project_id, db=db)
            for e in entries:
                if e["key"] in CONVENTION_KEYS:
                    result[e["key"]] = e["value"]
        return result

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(
        self,
        *,
        user_id: str,
        scope: MemoryScope | str,
        key: str,
        db: Any,
    ) -> bool:
        if isinstance(scope, str):
            scope = MemoryScope(scope)
        result = await db.execute(
            "DELETE FROM memories WHERE user_id = :user_id AND scope = :scope AND key = :key",
            {"user_id": user_id, "scope": scope.value, "key": key},
        )
        return True

    # ── Semantic retrieval (vector store fallback) ────────────────────────────

    async def semantic_search(
        self,
        *,
        user_id: str,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic recall using the MemoryService vector store."""
        svc = self._get_svc()
        if svc is None:
            return []
        try:
            return await svc.retrieve_project_context(
                project_id=project_id or user_id,
                query=query,
                top_k=top_k,
            )
        except Exception as exc:
            logger.warning("[MemoryStore] semantic_search failed: %s", exc)
            return []

    # ── Write-back helper ─────────────────────────────────────────────────────

    async def write_back_conventions(
        self,
        *,
        user_id: str,
        project_id: Optional[str],
        conventions: Dict[str, str],
        db: Any,
    ) -> None:
        """Persist confirmed conventions (called after agent run completes)."""
        for key, value in conventions.items():
            scope = MemoryScope.PROJECT if project_id else MemoryScope.USER
            await self.set(
                user_id=user_id,
                scope=scope,
                key=key,
                value=value,
                project_id=project_id,
                db=db,
            )


# Module-level singleton
memory_store = MemoryStore()
