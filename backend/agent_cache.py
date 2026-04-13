"""
Agent cache for CrucibAI — caches agent outputs by (agent_name, input_hash) with TTL.
Uses PostgreSQL table agent_cache (via db_pg); optional in-memory cache for hot path.
Reduces duplicate agent runs, faster repeat requests, lower token/cost.

PGDatabase uses attribute access (db.agent_cache), not db["agent_cache"] — bracket
access caused 'PGDatabase' object is not subscriptable in production logs.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600  # 1 hour
COLLECTION_NAME = "agent_cache"


def _cache_collection(db: Any):
    """Resolve collection: PGDatabase.agent_cache or legacy db['agent_cache']."""
    col = getattr(db, COLLECTION_NAME, None)
    if col is not None:
        return col
    getitem = getattr(db, "__getitem__", None)
    if callable(getitem):
        try:
            return getitem(COLLECTION_NAME)
        except (KeyError, TypeError, AttributeError):
            pass
    raise AttributeError(
        f"Database has no '{COLLECTION_NAME}' collection (use PGDatabase.{COLLECTION_NAME})"
    )


def _cache_doc_id(agent_name: str, input_key: str) -> str:
    """Stable row id for JSONB agent_cache table."""
    h = hashlib.sha256(f"{agent_name}\0{input_key}".encode()).hexdigest()
    return f"ac_{h[:56]}"

# Optional in-memory cache (bounded, agent_name -> { input_hash -> { output, expires } })
_memory_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
_MEMORY_MAX_ENTRIES_PER_AGENT = 100


def _input_hash(input_data: str) -> str:
    return hashlib.sha256(input_data.encode()).hexdigest()[:32]


async def get(db, agent_name: str, input_data: str) -> Optional[Dict[str, Any]]:
    """Return cached output for (agent_name, input_data) if present and not expired."""
    key = _input_hash(input_data)
    # In-memory first
    if agent_name in _memory_cache and key in _memory_cache[agent_name]:
        entry = _memory_cache[agent_name][key]
        if entry.get("expires") and datetime.now(timezone.utc) < entry["expires"]:
            return entry.get("output")
        del _memory_cache[agent_name][key]
    # PostgreSQL / Mongo-style
    try:
        col = _cache_collection(db)
        doc = await col.find_one({"agent_name": agent_name, "input_hash": key})
        if not doc:
            return None
        expires = doc.get("expires_at")
        now = datetime.now(timezone.utc)
        if expires:
            exp_dt = expires
            if isinstance(expires, str):
                try:
                    exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                except ValueError:
                    exp_dt = None
            if exp_dt is not None and exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt is not None and now > exp_dt:
                qdel = (
                    {"id": doc.get("id")}
                    if doc.get("id") or doc.get("_id")
                    else {"agent_name": agent_name, "input_hash": key}
                )
                await col.delete_one(qdel)
                return None
        return doc.get("output")
    except Exception as e:
        logger.warning("agent_cache get %s: %s", agent_name, e)
        return None


async def set(
    db,
    agent_name: str,
    input_data: str,
    output: Dict[str, Any],
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    """Store output for (agent_name, input_data) with TTL."""
    key = _input_hash(input_data)
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    # In-memory
    if agent_name not in _memory_cache:
        _memory_cache[agent_name] = {}
    cache = _memory_cache[agent_name]
    if key in cache:
        cache[key] = {"output": output, "expires": expires}
    else:
        if len(cache) >= _MEMORY_MAX_ENTRIES_PER_AGENT:
            # Evict oldest (simple: drop one arbitrary)
            cache.pop(next(iter(cache)))
        cache[key] = {"output": output, "expires": expires}
    # PostgreSQL: PGCollection.update_one has no upsert — find or insert.
    try:
        col = _cache_collection(db)
        doc = await col.find_one({"agent_name": agent_name, "input_hash": key})
        now = datetime.now(timezone.utc)
        expires_val = expires
        if isinstance(expires_val, datetime):
            expires_val = expires_val.astimezone(timezone.utc).isoformat()
        payload = {
            "id": (doc or {}).get("id") or (doc or {}).get("_id") or _cache_doc_id(agent_name, key),
            "agent_name": agent_name,
            "input_hash": key,
            "output": output,
            "expires_at": expires_val,
            "updated_at": now.isoformat(),
        }
        if doc:
            await col.update_one(
                {"id": doc.get("id") or doc.get("_id")},
                {"$set": {k: v for k, v in payload.items() if k != "id"}},
            )
        else:
            await col.insert_one(payload)
    except Exception as e:
        logger.warning("agent_cache set %s: %s", agent_name, e)


async def invalidate(
    db, agent_name: Optional[str] = None, input_hash_key: Optional[str] = None
) -> int:
    """Remove cache entries. If agent_name only, remove all for that agent. Return count deleted."""
    try:
        col = _cache_collection(db)
        q = {}
        if agent_name:
            q["agent_name"] = agent_name
        if input_hash_key:
            q["input_hash"] = input_hash_key
        if not q:
            return 0
        r = await col.delete_many(q)
        if agent_name and not input_hash_key and agent_name in _memory_cache:
            _memory_cache[agent_name].clear()
        return r.deleted_count
    except Exception as e:
        logger.warning("agent_cache invalidate: %s", e)
        return 0
