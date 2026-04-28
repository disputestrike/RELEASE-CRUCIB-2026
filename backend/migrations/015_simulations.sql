-- Durable Simulation / Reality Engine tables.
-- Tables keep the repo's JSONB document-store pattern while adding queryable
-- indexes for simulation_id, run_id, user_id, org_id, created_at, and status.

CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_inputs (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_sources (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_evidence (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_agents (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_rounds (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_agent_messages (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_belief_updates (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_clusters (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_outcomes (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_trust_scores (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_assumptions (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_events (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_simulations_user_id ON simulations ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_simulations_org_id ON simulations ((doc->>'org_id'));
CREATE INDEX IF NOT EXISTS idx_simulations_status ON simulations ((doc->>'status'));
CREATE INDEX IF NOT EXISTS idx_simulations_created_at_doc ON simulations ((doc->>'created_at'));

CREATE INDEX IF NOT EXISTS idx_simulation_runs_simulation_id ON simulation_runs ((doc->>'simulation_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_runs_user_id ON simulation_runs ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_runs_status ON simulation_runs ((doc->>'status'));
CREATE INDEX IF NOT EXISTS idx_simulation_runs_created_at_doc ON simulation_runs ((doc->>'created_at'));

CREATE INDEX IF NOT EXISTS idx_simulation_inputs_simulation_id ON simulation_inputs ((doc->>'simulation_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_inputs_run_id ON simulation_inputs ((doc->>'run_id'));

CREATE INDEX IF NOT EXISTS idx_simulation_sources_run_id ON simulation_sources ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_sources_simulation_id ON simulation_sources ((doc->>'simulation_id'));

CREATE INDEX IF NOT EXISTS idx_simulation_evidence_run_id ON simulation_evidence ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_evidence_source_id ON simulation_evidence ((doc->>'source_id'));

CREATE INDEX IF NOT EXISTS idx_simulation_agents_run_id ON simulation_agents ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_rounds_run_id ON simulation_rounds ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_messages_run_id ON simulation_agent_messages ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_belief_updates_run_id ON simulation_belief_updates ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_clusters_run_id ON simulation_clusters ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_outcomes_run_id ON simulation_outcomes ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_trust_scores_run_id ON simulation_trust_scores ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_assumptions_run_id ON simulation_assumptions ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_events_run_id ON simulation_events ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_events_type ON simulation_events ((doc->>'event_type'));
CREATE INDEX IF NOT EXISTS idx_simulation_events_created_at_doc ON simulation_events ((doc->>'created_at'));
