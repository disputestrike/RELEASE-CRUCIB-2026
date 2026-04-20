-- Migration 012: Phase-1 capability build-out
-- Adds 11 new tables and 2 view aliases required by the A-Q spec.
-- All statements use IF NOT EXISTS so this migration is fully idempotent.
-- Branch: engineering/master-list-closeout  Date: 2026-04-20

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. thread_checkpoints  (A – Persistent agent workspace)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS thread_checkpoints (
    id              TEXT        PRIMARY KEY,
    thread_id       TEXT        NOT NULL,
    user_id         TEXT        NOT NULL,
    checkpoint_data JSONB       NOT NULL DEFAULT '{}',
    mode            TEXT,
    phase           TEXT,
    status          TEXT        NOT NULL DEFAULT 'saved',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tc_thread_id  ON thread_checkpoints (thread_id);
CREATE INDEX IF NOT EXISTS idx_tc_user_id    ON thread_checkpoints (user_id);
CREATE INDEX IF NOT EXISTS idx_tc_created_at ON thread_checkpoints (created_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. agent_runs  — already EXISTS as JSONB doc table; create normalised view alias
-- ─────────────────────────────────────────────────────────────────────────────
-- agent_runs may already exist from schema 001/006; safe to repeat.
CREATE TABLE IF NOT EXISTS agent_runs (
    id         TEXT PRIMARY KEY,
    doc        JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_thread   ON agent_runs ((doc->>'thread_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_user     ON agent_runs ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_mode     ON agent_runs ((doc->>'mode'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_created  ON agent_runs ((doc->>'created_at'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. run_steps  (E – agent loop step logging)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS run_steps (
    id          TEXT        PRIMARY KEY,
    run_id      TEXT        NOT NULL,
    thread_id   TEXT,
    phase       TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'pending',
    payload     JSONB       NOT NULL DEFAULT '{}',
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_run_steps_run_id    ON run_steps (run_id);
CREATE INDEX IF NOT EXISTS idx_run_steps_thread_id ON run_steps (thread_id);
CREATE INDEX IF NOT EXISTS idx_run_steps_phase     ON run_steps (phase);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. tool_calls  (F – tool registry observability)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tool_calls (
    id          TEXT        PRIMARY KEY,
    run_id      TEXT,
    step_id     TEXT,
    tool_name   TEXT        NOT NULL,
    input       JSONB       NOT NULL DEFAULT '{}',
    output      JSONB,
    status      TEXT        NOT NULL DEFAULT 'pending',
    duration_ms INTEGER,
    dry_run     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id    ON tool_calls (run_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls (tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_calls_created   ON tool_calls (created_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. screenshots  (H – preview / operator mode)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS screenshots (
    id           TEXT        PRIMARY KEY,
    thread_id    TEXT,
    run_id       TEXT,
    url          TEXT,
    storage_path TEXT,
    mime_type    TEXT        NOT NULL DEFAULT 'image/png',
    width        INTEGER,
    height       INTEGER,
    metadata     JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_screenshots_thread_id ON screenshots (thread_id);
CREATE INDEX IF NOT EXISTS idx_screenshots_run_id    ON screenshots (run_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. memories  — view alias over agent_memory with explicit scope column
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
    id         TEXT        PRIMARY KEY,
    user_id    TEXT        NOT NULL,
    project_id TEXT,
    scope      TEXT        NOT NULL DEFAULT 'user',   -- user|project|workflow|migration
    key        TEXT        NOT NULL,
    value      TEXT        NOT NULL,
    metadata   JSONB       NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_user_id    ON memories (user_id);
CREATE INDEX IF NOT EXISTS idx_memories_scope      ON memories (scope);
CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories (project_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_unique ON memories (user_id, scope, key);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. automations  — view alias / normalised layer over automation_tasks
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS automations (
    id          TEXT        PRIMARY KEY,
    user_id     TEXT        NOT NULL,
    thread_id   TEXT,
    name        TEXT        NOT NULL,
    description TEXT,
    schedule    TEXT,                    -- cron expression
    mode        TEXT        NOT NULL DEFAULT 'one_pass',
    config      JSONB       NOT NULL DEFAULT '{}',
    enabled     BOOLEAN     NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_automations_user_id   ON automations (user_id);
CREATE INDEX IF NOT EXISTS idx_automations_thread_id ON automations (thread_id);
CREATE INDEX IF NOT EXISTS idx_automations_enabled   ON automations (enabled);

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. automation_runs  (I – automations run history)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS automation_runs (
    id            TEXT        PRIMARY KEY,
    automation_id TEXT        NOT NULL,
    thread_id     TEXT,
    status        TEXT        NOT NULL DEFAULT 'pending',
    result        JSONB,
    error         TEXT,
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_auto_runs_automation_id ON automation_runs (automation_id);
CREATE INDEX IF NOT EXISTS idx_auto_runs_thread_id     ON automation_runs (thread_id);
CREATE INDEX IF NOT EXISTS idx_auto_runs_status        ON automation_runs (status);

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. artifacts  (L – artifact system)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    id           TEXT        PRIMARY KEY,
    thread_id    TEXT,
    run_id       TEXT,
    user_id      TEXT        NOT NULL,
    artifact_type TEXT       NOT NULL,   -- spec|plan|migration_report|audit|pdf|slides|screenshot_pack|handoff|proof
    title        TEXT        NOT NULL,
    storage_path TEXT,
    download_url TEXT,
    size_bytes   INTEGER,
    mime_type    TEXT,
    metadata     JSONB       NOT NULL DEFAULT '{}',
    version      INTEGER     NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_artifacts_thread_id     ON artifacts (thread_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_user_id       ON artifacts (user_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_type ON artifacts (artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_run_id        ON artifacts (run_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. artifact_versions  (L – versioned artifacts)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifact_versions (
    id           TEXT        PRIMARY KEY,
    artifact_id  TEXT        NOT NULL,
    version      INTEGER     NOT NULL,
    storage_path TEXT,
    download_url TEXT,
    size_bytes   INTEGER,
    diff_summary TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_av_artifact_id ON artifact_versions (artifact_id);
CREATE INDEX IF NOT EXISTS idx_av_version     ON artifact_versions (version);

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. preview_comments  (H – page-pinned comments)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS preview_comments (
    id              TEXT        PRIMARY KEY,
    thread_id       TEXT,
    screenshot_id   TEXT,
    user_id         TEXT        NOT NULL,
    comment         TEXT        NOT NULL,
    region          JSONB,                  -- {x, y, width, height}
    status          TEXT        NOT NULL DEFAULT 'open',   -- open|resolved|task_created
    fix_task_id     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pc_thread_id    ON preview_comments (thread_id);
CREATE INDEX IF NOT EXISTS idx_pc_screenshot_id ON preview_comments (screenshot_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 12. migration_runs  (C / G – migration engine)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS migration_runs (
    id              TEXT        PRIMARY KEY,
    thread_id       TEXT,
    user_id         TEXT        NOT NULL,
    source_path     TEXT,
    target_path     TEXT,
    strategy        TEXT        NOT NULL DEFAULT 'merge_many_to_fewer',
    status          TEXT        NOT NULL DEFAULT 'pending',
    plan            JSONB       NOT NULL DEFAULT '{}',
    summary         JSONB       NOT NULL DEFAULT '{}',
    artifact_id     TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mr_thread_id ON migration_runs (thread_id);
CREATE INDEX IF NOT EXISTS idx_mr_user_id   ON migration_runs (user_id);
CREATE INDEX IF NOT EXISTS idx_mr_status    ON migration_runs (status);

-- ─────────────────────────────────────────────────────────────────────────────
-- 13. migration_file_maps  (C / G – file-level mapping)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS migration_file_maps (
    id           TEXT        PRIMARY KEY,
    migration_id TEXT        NOT NULL,
    source_path  TEXT        NOT NULL,
    target_path  TEXT,
    action       TEXT        NOT NULL DEFAULT 'copy',   -- copy|merge|split|rename|delete|lift
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mfm_migration_id ON migration_file_maps (migration_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 14. source_to_target_mappings  (C – detailed symbol-level mapping)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_to_target_mappings (
    id              TEXT        PRIMARY KEY,
    file_map_id     TEXT        NOT NULL,
    source_symbol   TEXT,
    target_symbol   TEXT,
    symbol_type     TEXT,       -- function|class|variable|export
    transformation  TEXT,       -- rename|inline|lift|delete
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stm_file_map_id ON source_to_target_mappings (file_map_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 15. approvals  (O – safety / governance)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS approvals (
    id          TEXT        PRIMARY KEY,
    thread_id   TEXT,
    run_id      TEXT,
    user_id     TEXT        NOT NULL,
    action_type TEXT        NOT NULL,
    action_data JSONB       NOT NULL DEFAULT '{}',
    decision    TEXT,                   -- approved|denied|pending
    decided_at  TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approvals_thread_id ON approvals (thread_id);
CREATE INDEX IF NOT EXISTS idx_approvals_user_id   ON approvals (user_id);
CREATE INDEX IF NOT EXISTS idx_approvals_decision  ON approvals (decision);
