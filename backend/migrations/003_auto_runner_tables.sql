-- Migration 003: Auto-Runner, DAG Orchestration, Proof System
-- CrucibAI Autonomous Platform Tables

-- ── Jobs ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         TEXT REFERENCES users(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'planned',  -- planned|approved|queued|running|blocked|failed|completed|cancelled
    mode            TEXT NOT NULL DEFAULT 'guided',   -- guided|auto|manual
    goal            TEXT NOT NULL DEFAULT '',
    current_phase   TEXT DEFAULT 'planning',
    retry_count     INTEGER DEFAULT 0,
    quality_score   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user    ON jobs(user_id);

-- ── Job Steps ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_steps (
    id              TEXT PRIMARY KEY,
    job_id          TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    step_key        TEXT NOT NULL,
    agent_name      TEXT NOT NULL DEFAULT '',
    phase           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|running|verifying|retrying|failed|completed|blocked|skipped
    depends_on_json TEXT DEFAULT '[]',
    order_index     INTEGER DEFAULT 0,
    retry_count     INTEGER DEFAULT 0,
    output_ref      TEXT,
    verifier_status TEXT,
    verifier_score  INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_job_steps_job    ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_status ON job_steps(status);
CREATE INDEX IF NOT EXISTS idx_job_steps_key    ON job_steps(job_id, step_key);

-- ── Job Events ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_events (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    step_id      TEXT REFERENCES job_steps(id) ON DELETE SET NULL,
    event_type   TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_events_job  ON job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(event_type);
CREATE INDEX IF NOT EXISTS idx_job_events_time ON job_events(created_at);

-- ── Job Checkpoints ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_checkpoints (
    id              TEXT PRIMARY KEY,
    job_id          TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    checkpoint_key  TEXT NOT NULL,
    snapshot_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (job_id, checkpoint_key)
);
CREATE INDEX IF NOT EXISTS idx_job_checkpoints_job ON job_checkpoints(job_id);

-- ── Proof Items ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proof_items (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    step_id      TEXT REFERENCES job_steps(id) ON DELETE SET NULL,
    proof_type   TEXT NOT NULL,   -- file|compile|db|route|deploy|api|test|generic
    title        TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_proof_items_job  ON proof_items(job_id);
CREATE INDEX IF NOT EXISTS idx_proof_items_type ON proof_items(proof_type);

-- ── Build Plans ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS build_plans (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    project_id   TEXT NOT NULL,
    goal         TEXT NOT NULL,
    plan_json    TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'draft',   -- draft|approved|running|completed
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_build_plans_job ON build_plans(job_id);

-- ── Verification Runs ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS verification_runs (
    id           TEXT PRIMARY KEY,
    step_id      TEXT NOT NULL REFERENCES job_steps(id) ON DELETE CASCADE,
    job_id       TEXT NOT NULL,
    passed       BOOLEAN NOT NULL DEFAULT FALSE,
    score        INTEGER DEFAULT 0,
    issues_json  TEXT DEFAULT '[]',
    proof_json   TEXT DEFAULT '[]',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verification_runs_step ON verification_runs(step_id);

-- ── Step Retries ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS step_retries (
    id              TEXT PRIMARY KEY,
    step_id         TEXT NOT NULL REFERENCES job_steps(id) ON DELETE CASCADE,
    job_id          TEXT NOT NULL,
    attempt_number  INTEGER NOT NULL DEFAULT 1,
    failure_type    TEXT,
    error_message   TEXT,
    fix_applied     TEXT,
    outcome         TEXT,   -- succeeded|failed|abandoned
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_step_retries_step ON step_retries(step_id);

-- ── Skills Marketplace ────────────────────────────────────────────────────────
-- Add missing columns to existing skills tables if needed
DO $$
BEGIN
    -- Check if skills table exists and add marketplace columns
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='skills') THEN
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS marketplace_listed BOOLEAN DEFAULT FALSE; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS install_count INTEGER DEFAULT 0; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS rating_avg NUMERIC(3,2) DEFAULT 0; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS tags TEXT DEFAULT '[]'; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS preview_url TEXT; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN ALTER TABLE skills ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE; EXCEPTION WHEN OTHERS THEN NULL; END;
    END IF;
END $$;

-- ── Cost Estimates ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_estimates (
    id              TEXT PRIMARY KEY,
    project_id      TEXT,
    goal            TEXT,
    build_kind      TEXT,
    estimated_tokens INTEGER DEFAULT 0,
    estimated_credits INTEGER DEFAULT 0,
    plan_json       TEXT DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
