"""
Agent cache for CrucibAI — caches agent outputs by (agent_name, input_hash) with TTL.
Uses PostgreSQL table agent_cache (via db_pg); optional in-memory cache for hot path.
Reduces duplicate agent runs, faster repeat requests, lower token/cost.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600  # 1 hour
COLLECTION_NAME = "agent_cache"

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
    # PostgreSQL
    try:
        doc = await db[COLLECTION_NAME].find_one(
            {"agent_name": agent_name, "input_hash": key}
        )
        if not doc:
            return None
        expires = doc.get("expires_at")
        if expires and datetime.now(timezone.utc) > expires:
            await db[COLLECTION_NAME].delete_one({"_id": doc["_id"]})
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
    # PostgreSQL
    try:
        await db[COLLECTION_NAME].update_one(
            {"agent_name": agent_name, "input_hash": key},
            {
                "$set": {
                    "output": output,
                    "expires_at": expires,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("agent_cache set %s: %s", agent_name, e)


async def invalidate(
    db, agent_name: Optional[str] = None, input_hash_key: Optional[str] = None
) -> int:
    """Remove cache entries. If agent_name only, remove all for that agent. Return count deleted."""
    try:
        q = {}
        if agent_name:
            q["agent_name"] = agent_name
        if input_hash_key:
            q["input_hash"] = input_hash_key
        if not q:
            return 0
        r = await db[COLLECTION_NAME].delete_many(q)
        if agent_name and not input_hash_key and agent_name in _memory_cache:
            _memory_cache[agent_name].clear()
        return r.deleted_count
    except Exception as e:
        logger.warning("agent_cache invalidate: %s", e)
        return 0
