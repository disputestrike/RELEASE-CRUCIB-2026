-- Migration 010: schema_migrations tracking table
-- Tracks which migrations have been applied so they are not re-run on every
-- startup.  Each row records the migration filename and when it was applied.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   TEXT        PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
