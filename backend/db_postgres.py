"""
Re-export from db_pg. The full Motor-like wrapper lives in db_pg.py.
"""
from db_pg import (
    get_db,
    get_pool,
    get_pg_pool,
    close_pool,
    close_pg_pool,
    is_pg_available,
    TABLE_CONFIG,
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
