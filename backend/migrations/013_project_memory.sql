-- WS-G: Per-project persistent memory (K/V with JSONB values)
-- Used for long-lived project defaults ("default_currency": "EUR") and learned
-- preferences that must survive across sessions.

CREATE TABLE IF NOT EXISTS project_memory (
    project_id TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, key)
);

CREATE INDEX IF NOT EXISTS idx_project_memory_updated
    ON project_memory (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_memory_project
    ON project_memory (project_id);
