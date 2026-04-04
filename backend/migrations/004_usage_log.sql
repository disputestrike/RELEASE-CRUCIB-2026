-- Migration 004: usage_log table for credit tracking
-- Fixes: credit_tracker ERROR - Failed to record usage: relation "usage_log" does not exist
-- Uses id+doc JSONB pattern to match PGCollection wrapper in db_pg.py

CREATE TABLE IF NOT EXISTS usage_log (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_log_user_id  ON usage_log ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_usage_log_model    ON usage_log ((doc->>'model'));
CREATE INDEX IF NOT EXISTS idx_usage_log_created  ON usage_log (created_at DESC);
