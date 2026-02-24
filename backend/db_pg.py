"""
PostgreSQL connection layer for CrucibAI (optional).
When DATABASE_URL is set, provides asyncpg pool for monitoring and future tables.
MongoDB remains primary until full migration.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)
_pool = None


async def get_pg_pool():
    """Return asyncpg pool if DATABASE_URL is set, else None."""
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=5, command_timeout=60)
        logger.info("PostgreSQL pool created (DATABASE_URL set).")
        return _pool
    except Exception as e:
        logger.warning("PostgreSQL pool not created: %s", e)
        return None


async def close_pg_pool():
    """Close the global asyncpg pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed.")


def is_pg_available() -> bool:
    """Return True if DATABASE_URL is set (pool may still fail at runtime)."""
    return bool(os.environ.get("DATABASE_URL", "").strip())
