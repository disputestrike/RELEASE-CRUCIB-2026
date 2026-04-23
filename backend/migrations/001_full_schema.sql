-- CrucibAI full migration: MongoDB → PostgreSQL
-- All app data stored in doc JSONB; PKs for lookups and indexes.

-- Users (auth, credits, MFA, profile)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users ((doc->>'email'));

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects ((doc->>'status'));

-- Project logs (build logs)
CREATE TABLE IF NOT EXISTS project_logs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_project_logs_project_id ON project_logs ((doc->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_project_logs_created ON project_logs ((doc->>'created_at'));

-- Agent status (per project/agent)
CREATE TABLE IF NOT EXISTS agent_status (
    project_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    doc JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (project_id, agent_name)
);
CREATE INDEX IF NOT EXISTS idx_agent_status_project_id ON agent_status (project_id);

-- Chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history ((doc->>'session_id'));
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_chat_history_created ON chat_history ((doc->>'created_at'));

-- Workspace env (per user)
CREATE TABLE IF NOT EXISTS workspace_env (
    user_id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

-- Token ledger
CREATE TABLE IF NOT EXISTS token_ledger (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_token_ledger_user_id ON token_ledger ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_token_ledger_created ON token_ledger ((doc->>'created_at'));

-- Token usage
CREATE TABLE IF NOT EXISTS token_usage (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_token_usage_project_id ON token_usage ((doc->>'project_id'));

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks ((doc->>'created_at'));

-- User agents
CREATE TABLE IF NOT EXISTS user_agents (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_user_agents_user_id ON user_agents ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_user_agents_updated ON user_agents ((doc->>'updated_at'));

-- Agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs ((doc->>'agent_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_agent_runs_triggered ON agent_runs ((doc->>'triggered_at'));

-- Referral codes
CREATE TABLE IF NOT EXISTS referral_codes (
    code TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_referral_codes_user_id ON referral_codes ((doc->>'user_id'));

-- Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals ((doc->>'referrer_id'));
CREATE INDEX IF NOT EXISTS idx_referrals_signup_at ON referrals ((doc->>'signup_completed_at'));

-- API keys
CREATE TABLE IF NOT EXISTS api_keys (
    key TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys ((doc->>'user_id'));

-- Enterprise inquiries
CREATE TABLE IF NOT EXISTS enterprise_inquiries (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

-- Backup codes (MFA) – use serial _id for update_one({"_id": ...})
CREATE TABLE IF NOT EXISTS backup_codes (
    _id SERIAL PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_backup_codes_user_id ON backup_codes ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_backup_codes_used ON backup_codes ((doc->>'used'));

-- MFA setup temp
CREATE TABLE IF NOT EXISTS mfa_setup_temp (
    user_id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

-- Shares
CREATE TABLE IF NOT EXISTS shares (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_shares_project_id ON shares ((doc->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_shares_user_id ON shares ((doc->>'user_id'));

-- Blocked requests
CREATE TABLE IF NOT EXISTS blocked_requests (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_blocked_requests_user_id ON blocked_requests ((doc->>'user_id'));

-- Agent memory
CREATE TABLE IF NOT EXISTS agent_memory (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_agent_memory_user_id ON agent_memory ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_agent_memory_created ON agent_memory ((doc->>'created_at'));

-- Automation tasks
CREATE TABLE IF NOT EXISTS automation_tasks (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_automation_tasks_user_id ON automation_tasks ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_automation_tasks_created ON automation_tasks ((doc->>'created_at'));

-- Audit log (timestamp for range queries)
CREATE TABLE IF NOT EXISTS audit_log (
    _id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log ((doc->>'action'));

-- Examples (seed data for /api/examples)
CREATE TABLE IF NOT EXISTS examples (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_examples_name ON examples ((doc->>'name'));

-- Monitoring events (optional; same pool as main app)
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
