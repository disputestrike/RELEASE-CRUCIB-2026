-- Migration 005: Fix orchestration tables
-- Recreates jobs, job_steps, job_events, job_checkpoints, proof_items, build_plans,
-- verification_runs, step_retries WITHOUT foreign key constraints so they work
-- even when project_id/user_id are not actual rows in referenced tables.
-- Uses IF NOT EXISTS so this is safe to run multiple times.

-- Drop and recreate jobs without FK constraints
DO $$
BEGIN
  -- If the old jobs table had FK constraints that caused creation to fail, drop and recreate
  -- First check if jobs table exists
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'jobs') THEN
    CREATE TABLE jobs (
      id            TEXT PRIMARY KEY,
      project_id    TEXT NOT NULL DEFAULT '',
      user_id       TEXT,
      status        TEXT NOT NULL DEFAULT 'planned',
      mode          TEXT NOT NULL DEFAULT 'guided',
      goal          TEXT NOT NULL DEFAULT '',
      current_phase TEXT DEFAULT 'planning',
      retry_count   INTEGER DEFAULT 0,
      quality_score INTEGER DEFAULT 0,
      error_message TEXT,
      created_at    TIMESTAMPTZ DEFAULT NOW(),
      updated_at    TIMESTAMPTZ DEFAULT NOW(),
      started_at    TIMESTAMPTZ,
      completed_at  TIMESTAMPTZ
    );
  ELSE
    -- Add error_message column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'error_message') THEN
      ALTER TABLE jobs ADD COLUMN error_message TEXT;
    END IF;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user    ON jobs(user_id);

-- job_steps
CREATE TABLE IF NOT EXISTS job_steps (
    id              TEXT PRIMARY KEY,
    job_id          TEXT NOT NULL,
    step_key        TEXT NOT NULL,
    agent_name      TEXT NOT NULL DEFAULT '',
    phase           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
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

-- job_events
CREATE TABLE IF NOT EXISTS job_events (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL,
    step_id      TEXT,
    event_type   TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    narrative    TEXT DEFAULT '',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_events_job  ON job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(event_type);

-- job_checkpoints
CREATE TABLE IF NOT EXISTS job_checkpoints (
    id               TEXT PRIMARY KEY,
    job_id           TEXT NOT NULL,
    checkpoint_key   TEXT NOT NULL DEFAULT 'latest',
    snapshot_json    TEXT DEFAULT '{}',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_checkpoints_job ON job_checkpoints(job_id);

-- proof_items
CREATE TABLE IF NOT EXISTS proof_items (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL,
    step_id      TEXT,
    proof_type   TEXT NOT NULL DEFAULT 'generic',
    title        TEXT NOT NULL DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_proof_items_job  ON proof_items(job_id);
CREATE INDEX IF NOT EXISTS idx_proof_items_type ON proof_items(proof_type);

-- build_plans
CREATE TABLE IF NOT EXISTS build_plans (
    id           TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL,
    project_id   TEXT NOT NULL DEFAULT '',
    goal         TEXT NOT NULL DEFAULT '',
    plan_json    TEXT DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'draft',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_build_plans_job ON build_plans(job_id);

-- verification_runs
CREATE TABLE IF NOT EXISTS verification_runs (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id       TEXT NOT NULL,
    step_id      TEXT,
    verifier_id  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    score        INTEGER DEFAULT 0,
    details_json TEXT DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verification_runs_job ON verification_runs(job_id);

-- step_retries
CREATE TABLE IF NOT EXISTS step_retries (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id       TEXT NOT NULL,
    step_id      TEXT NOT NULL,
    retry_number INTEGER DEFAULT 1,
    reason       TEXT DEFAULT '',
    fix_applied  TEXT DEFAULT '',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_step_retries_job  ON step_retries(job_id);
CREATE INDEX IF NOT EXISTS idx_step_retries_step ON step_retries(step_id);

-- cost_estimates
CREATE TABLE IF NOT EXISTS cost_estimates (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id          TEXT,
    goal_text       TEXT DEFAULT '',
    estimated_tokens INTEGER DEFAULT 0,
    estimated_cost  REAL DEFAULT 0,
    model           TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- usage_log (also from 004 — ensure it exists with correct schema)
CREATE TABLE IF NOT EXISTS usage_log (
    id         TEXT PRIMARY KEY,
    doc        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_log_user_id ON usage_log ((doc->>'user_id'));
