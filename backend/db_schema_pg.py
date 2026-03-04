"""
Legacy: monitoring_events-only schema. For full app (all tables), db_pg.init_schema()
runs backend/migrations/001_full_schema.sql. The app uses db_pg.get_db() which calls that.
"""
import logging

logger = logging.getLogger(__name__)

MONITORING_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS monitoring_events (
    id SERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration FLOAT,
    metadata JSONB,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_user_id ON monitoring_events(user_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_timestamp ON monitoring_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_type ON monitoring_events(event_type);
"""


async def init_pg_schema(pool) -> bool:
    """Create tables (e.g. monitoring_events). Returns True on success."""
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(MONITORING_EVENTS_SQL)
        logger.info("PostgreSQL schema initialized (monitoring_events).")
        return True
    except Exception as e:
        logger.warning("PostgreSQL schema init failed: %s", e)
        return False
