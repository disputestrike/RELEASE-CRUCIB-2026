"""Wave 5 — API Keys route.

Allows users to create, list, and revoke API keys for third-party SDK access.

Endpoints
---------
POST   /api/keys         — create key; returns plaintext secret ONCE
GET    /api/keys         — list caller's keys (prefix only, no secrets)
DELETE /api/keys/{id}    — revoke key (sets revoked_at)
GET    /api/keys/{id}/usage — usage count or degraded
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keys", tags=["api-keys"])

_TABLE_CHECKED = False


def _get_auth():
    try:
        from ....server import get_current_user  # type: ignore        return get_current_user
    except Exception:
        async def _anon():
            return {"id": "anonymous"}
        return _anon


async def _get_pool():
    try:
        from ....db_pg import get_db  # type: ignore        return await get_db()
    except Exception:
        return None


async def _ensure_table(pool):
    global _TABLE_CHECKED
    if _TABLE_CHECKED:
        return
    if pool is None:
        return
    try:
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS crucib_api_keys (
                id text PRIMARY KEY,
                user_id text,
                name text,
                prefix text,
                hashed_secret text,
                scopes jsonb,
                created_at timestamptz DEFAULT now(),
                last_used_at timestamptz,
                revoked_at timestamptz
            )
            """
        )
        _TABLE_CHECKED = True
    except Exception as exc:
        logger.warning("crucib_api_keys ensure failed: %s", exc)


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    scopes: list = Field(default_factory=list)


@router.post("")
async def create_key(
    body: CreateKeyRequest,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Create a new API key; returns plaintext secret exactly once."""
    pool = await _get_pool()
    await _ensure_table(pool)

    key_id = uuid.uuid4().hex
    raw_secret = "crc_" + secrets.token_urlsafe(32)
    prefix = raw_secret[:12]
    hashed = hashlib.sha256(raw_secret.encode()).hexdigest()
    user_id = (user or {}).get("id") or "anonymous"
    now = datetime.now(timezone.utc)

    if pool is not None:
        try:
            import json
            await pool.execute(
                """
                INSERT INTO crucib_api_keys
                    (id, user_id, name, prefix, hashed_secret, scopes, created_at)
                VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7)
                """,
                key_id, user_id, body.name, prefix,
                hashed, json.dumps(body.scopes), now,
            )
        except Exception as exc:
            logger.warning("api_keys create persist failed: %s", exc)

    return {
        "id": key_id,
        "name": body.name,
        "prefix": prefix,
        "secret": raw_secret,
        "scopes": body.scopes,
        "created_at": now.isoformat(),
        "message": "Store this secret securely — it will not be shown again.",
    }


@router.get("")
async def list_keys(
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """List caller's API keys (prefix shown, secrets never returned)."""
    pool = await _get_pool()
    if pool is None:
        return {"keys": [], "degraded": True}

    await _ensure_table(pool)
    user_id = (user or {}).get("id") or "anonymous"

    try:
        rows = await pool.fetch(
            """
            SELECT id, name, prefix, scopes, created_at, last_used_at, revoked_at
            FROM crucib_api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
        import json
        keys = []
        for r in rows:
            scopes = r["scopes"]
            if isinstance(scopes, str):
                scopes = json.loads(scopes)
            keys.append({
                "id": r["id"],
                "name": r["name"],
                "prefix": r["prefix"],
                "scopes": scopes or [],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
                "revoked_at": r["revoked_at"].isoformat() if r["revoked_at"] else None,
            })
        return {"keys": keys}
    except Exception as exc:
        logger.warning("api_keys list failed: %s", exc)
        return {"keys": [], "degraded": True}


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Revoke an API key by setting revoked_at."""
    pool = await _get_pool()
    if pool is None:
        return {"revoked": False, "degraded": True}

    await _ensure_table(pool)
    user_id = (user or {}).get("id") or "anonymous"

    try:
        now = datetime.now(timezone.utc)
        result = await pool.execute(
            """
            UPDATE crucib_api_keys
            SET revoked_at = $1
            WHERE id = $2 AND user_id = $3 AND revoked_at IS NULL
            """,
            now, key_id, user_id,
        )
        updated = result.split(" ")[-1] if result else "0"
        return {"revoked": int(updated) > 0, "id": key_id}
    except Exception as exc:
        logger.warning("api_keys revoke failed: %s", exc)
        return {"revoked": False, "degraded": True}


@router.get("/{key_id}/usage")
async def key_usage(
    key_id: str,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Return usage count for a key; degrades gracefully if no audit table."""
    pool = await _get_pool()
    if pool is None:
        return {"calls": 0, "degraded": True}

    try:
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM crucib_api_key_audit WHERE key_id = $1",
            key_id,
        )
        return {"calls": int(count or 0), "key_id": key_id}
    except Exception:
        return {"calls": 0, "degraded": True}
