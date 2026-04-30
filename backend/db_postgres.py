"""
Re-export from db_pg. Primary data store is PostgreSQL (JSONB documents).
"""

from .db_pg import (
    TABLE_CONFIG,
    close_pg_pool,
    close_pool,
    get_db,
    get_pg_pool,
    get_pool,
    is_pg_available,
)

__all__ = [
    "get_db",
    "get_pool",
    "get_pg_pool",
    "close_pool",
    "close_pg_pool",
    "is_pg_available",
    "TABLE_CONFIG",
]
