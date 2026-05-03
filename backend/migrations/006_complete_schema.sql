-- Migration 006: Complete schema - Create all missing tables and add missing columns
-- This migration is idempotent - safe to run multiple times

-- ============================================================================
-- SECTION 1: Core tables that already exist - add missing columns
-- ============================================================================

-- users: add any missing columns
ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS doc JSONB NOT NULL DEFAULT '{}';

-- projects: add any missing columns
ALTER TABLE IF EXISTS projects ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS projects ADD COLUMN IF NOT EXISTS doc JSONB NOT NULL DEFAULT '{}';

-- ============================================================================
-- SECTION 2: Jobs/Orchestration tables - ensure error_message and all columns
-- ============================================================================

-- jobs table - add missing error_message column
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS error_details TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS failure_details TEXT;

-- job_steps - ensure all columns exist
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS error_details TEXT;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS output_files TEXT;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0;

-- ============================================================================
-- SECTION 3: Missing document tables (JSONB-based)
-- ============================================================================

-- Create all JSONB document tables if they don't exist
CREATE TABLE IF NOT EXISTS project_logs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_project_logs_project_id ON project_logs ((doc->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_project_logs_created ON project_logs ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS agent_status (
    project_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    doc JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (project_id, agent_name)
);
CREATE INDEX IF NOT EXISTS idx_agent_status_project_id ON agent_status (project_id);

CREATE TABLE IF NOT EXISTS chat_history (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history ((doc->>'session_id'));
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_chat_history_created ON chat_history ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS saved_prompts (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS workspace_env (
    user_id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS token_ledger (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_token_ledger_user_id ON token_ledger ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_token_ledger_created ON token_ledger ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS token_usage (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_token_usage_project_id ON token_usage ((doc->>'project_id'));

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS user_agents (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_user_agents_user_id ON user_agents ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_user_agents_updated ON user_agents ((doc->>'updated_at'));

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs ((doc->>'agent_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_triggered ON agent_runs ((doc->>'triggered_at'));

CREATE TABLE IF NOT EXISTS referral_codes (
    code TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_referral_codes_user_id ON referral_codes ((doc->>'user_id'));

CREATE TABLE IF NOT EXISTS referrals (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals ((doc->>'referrer_id'));
CREATE INDEX IF NOT EXISTS idx_referrals_signup_at ON referrals ((doc->>'signup_completed_at'));

CREATE TABLE IF NOT EXISTS api_keys (
    key TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys ((doc->>'user_id'));

CREATE TABLE IF NOT EXISTS enterprise_inquiries (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS contact_submissions (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_contact_submissions_created ON contact_submissions ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS backup_codes (
    _id SERIAL PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_backup_codes_user_id ON backup_codes ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_backup_codes_used ON backup_codes ((doc->>'used'));

CREATE TABLE IF NOT EXISTS mfa_setup_temp (
    user_id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS shares (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_shares_project_id ON shares ((doc->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_shares_user_id ON shares ((doc->>'user_id'));

CREATE TABLE IF NOT EXISTS blocked_requests (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_blocked_requests_user_id ON blocked_requests ((doc->>'user_id'));

CREATE TABLE IF NOT EXISTS agent_memory (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_memory_user_id ON agent_memory ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_agent_memory_created ON agent_memory ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS automation_tasks (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_automation_tasks_user_id ON automation_tasks ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_automation_tasks_created ON automation_tasks ((doc->>'created_at'));

CREATE TABLE IF NOT EXISTS audit_log (
    _id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log ((doc->>'action'));

CREATE TABLE IF NOT EXISTS examples (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_examples_name ON examples ((doc->>'name'));

CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS app_sessions (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_messages (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claims_ledger (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS safety_policies (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS safety_audit_log (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE,
    name TEXT,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tenant_members (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS workspace_invitations (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_metrics (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS app_db_schemas (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS user_skills (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS app_items (
    id TEXT PRIMARY KEY,
    title TEXT,
    tenant_id TEXT,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_app_items_tenant_id ON app_items (tenant_id);

CREATE TABLE IF NOT EXISTS team_members (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS builds (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS vector_store (
    id TEXT PRIMARY KEY,
    embedding VECTOR(1536),
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS paypal_events_processed (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_paypal_events_received ON paypal_events_processed(received_at);

-- ============================================================================
-- SECTION 4: Verification and build tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS verification_runs (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id TEXT NOT NULL,
    step_id TEXT,
    verifier_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    score INTEGER DEFAULT 0,
    details_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verification_runs_job ON verification_runs(job_id);

CREATE TABLE IF NOT EXISTS step_retries (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    retry_number INTEGER DEFAULT 1,
    reason TEXT DEFAULT '',
    fix_applied TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_step_retries_job ON step_retries(job_id);
CREATE INDEX IF NOT EXISTS idx_step_retries_step ON step_retries(step_id);

CREATE TABLE IF NOT EXISTS cost_estimates (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id TEXT,
    goal_text TEXT DEFAULT '',
    estimated_tokens INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0,
    model TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage_log (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_log_user_id ON usage_log ((doc->>'user_id'));

-- ============================================================================
-- SECTION 5: Monitoring and logging
-- ============================================================================

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

-- ============================================================================
-- SECTION 6: Final validation - check critical tables have required columns
-- ============================================================================

-- Ensure proof_items has all required columns
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS job_id TEXT NOT NULL;
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS step_id TEXT;
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS proof_type TEXT NOT NULL DEFAULT 'generic';
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS payload_json TEXT DEFAULT '{}';
ALTER TABLE IF EXISTS proof_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_proof_items_job ON proof_items(job_id);
CREATE INDEX IF NOT EXISTS idx_proof_items_type ON proof_items(proof_type);

-- Ensure build_plans has all required columns
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS job_id TEXT NOT NULL;
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS project_id TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS plan_json TEXT DEFAULT '{}';
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft';
ALTER TABLE IF EXISTS build_plans ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_build_plans_job ON build_plans(job_id);

-- Ensure job_checkpoints has all required columns
ALTER TABLE IF EXISTS job_checkpoints ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS job_checkpoints ADD COLUMN IF NOT EXISTS job_id TEXT NOT NULL;
ALTER TABLE IF EXISTS job_checkpoints ADD COLUMN IF NOT EXISTS checkpoint_key TEXT NOT NULL DEFAULT 'latest';
ALTER TABLE IF EXISTS job_checkpoints ADD COLUMN IF NOT EXISTS snapshot_json TEXT DEFAULT '{}';
ALTER TABLE IF EXISTS job_checkpoints ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_job_checkpoints_job ON job_checkpoints(job_id);

-- Ensure job_events has all required columns
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS job_id TEXT NOT NULL;
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS step_id TEXT;
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS event_type TEXT NOT NULL;
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS payload_json TEXT DEFAULT '{}';
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS narrative TEXT DEFAULT '';
ALTER TABLE IF EXISTS job_events ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(event_type);

-- Ensure job_steps has all required columns
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS job_id TEXT NOT NULL;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS step_key TEXT NOT NULL;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS agent_name TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS phase TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS depends_on_json TEXT DEFAULT '[]';
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS output_ref TEXT;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS verifier_status TEXT;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS verifier_score INTEGER DEFAULT 0;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS job_steps ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_status ON job_steps(status);
CREATE INDEX IF NOT EXISTS idx_job_steps_key ON job_steps(job_id, step_key);

-- Ensure jobs has all required columns
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS id TEXT PRIMARY KEY;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS project_id TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'planned';
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'guided';
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS current_phase TEXT DEFAULT 'planning';
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS quality_score INTEGER DEFAULT 0;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS error_details TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS failure_details TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS blocked_steps TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS failed_step_keys TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS non_completed TEXT;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);

-- ============================================================================
-- SECTION 7: Cleanup - Ensure no duplicate indexes
-- ============================================================================

-- Drop any old duplicate indexes (PostgreSQL will ignore if they don't exist)
DROP INDEX IF EXISTS idx_job_steps_job_id;
DROP INDEX IF EXISTS idx_job_events_job_id;
DROP INDEX IF EXISTS idx_jobs_project_id;

-- Done!
