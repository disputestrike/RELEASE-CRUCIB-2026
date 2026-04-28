-- WS-J: public share + remix for projects
CREATE TABLE IF NOT EXISTS project_shares (
    slug          TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL,
    owner_user_id TEXT,
    title         TEXT,
    snapshot      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    views         INTEGER NOT NULL DEFAULT 0,
    remixes       INTEGER NOT NULL DEFAULT 0,
    revoked       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_project_shares_project ON project_shares (project_id);
CREATE INDEX IF NOT EXISTS idx_project_shares_owner   ON project_shares (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_project_shares_created ON project_shares (created_at DESC);
