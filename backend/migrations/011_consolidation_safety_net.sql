-- Migration 011: consolidation safety net
-- Ensures tables introduced after 010 that are referenced in application code exist.
-- All statements use IF NOT EXISTS so this is fully idempotent.

-- sandbox_runs: records code execution results from the E2B / in-process sandbox
CREATE TABLE IF NOT EXISTS sandbox_runs (
    id         TEXT        PRIMARY KEY,
    doc        JSONB       NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_sandbox_runs_project_id ON sandbox_runs ((doc->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_sandbox_runs_agent     ON sandbox_runs ((doc->>'agent_name'));
CREATE INDEX IF NOT EXISTS idx_sandbox_runs_created   ON sandbox_runs ((doc->>'created_at'));

-- provider_readiness_log: optional audit of provider readiness checks
CREATE TABLE IF NOT EXISTS provider_readiness_log (
    id         TEXT        PRIMARY KEY,
    doc        JSONB       NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_provider_readiness_created ON provider_readiness_log ((doc->>'created_at'));

-- user_skills (may already exist from 006; safe to repeat with IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS user_skills (
    id      TEXT PRIMARY KEY,
    doc     JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_user_skills_user_id ON user_skills ((doc->>'user_id'));

-- team_members (may already exist)
CREATE TABLE IF NOT EXISTS team_members (
    id      TEXT PRIMARY KEY,
    doc     JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members ((doc->>'team_id'));

-- workspace_invitations (may already exist)
CREATE TABLE IF NOT EXISTS workspace_invitations (
    id      TEXT PRIMARY KEY,
    doc     JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_invitee ON workspace_invitations ((doc->>'invitee_email'));
