-- Reality Engine contract tables for evidence-first Simulation.
-- Existing simulation tables remain untouched; these add durable claim graph,
-- population-model, trust-snapshot, and replay stores using the repo JSONB
-- document pattern.

CREATE TABLE IF NOT EXISTS simulation_claims (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_population_models (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_trust_snapshots (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_replay_events (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_simulation_claims_run_id ON simulation_claims ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_claims_simulation_id ON simulation_claims ((doc->>'simulation_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_claims_supports ON simulation_claims ((doc->>'supports_or_refutes'));
CREATE INDEX IF NOT EXISTS idx_simulation_claims_doc_gin ON simulation_claims USING gin (doc jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_simulation_population_models_run_id ON simulation_population_models ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_population_models_simulation_id ON simulation_population_models ((doc->>'simulation_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_population_models_doc_gin ON simulation_population_models USING gin (doc jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_simulation_trust_snapshots_run_id ON simulation_trust_snapshots ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_trust_snapshots_phase ON simulation_trust_snapshots ((doc->>'phase'));
CREATE INDEX IF NOT EXISTS idx_simulation_trust_snapshots_doc_gin ON simulation_trust_snapshots USING gin (doc jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_simulation_replay_events_run_id ON simulation_replay_events ((doc->>'run_id'));
CREATE INDEX IF NOT EXISTS idx_simulation_replay_events_type ON simulation_replay_events ((doc->>'event_type'));
CREATE INDEX IF NOT EXISTS idx_simulation_replay_events_created_at_doc ON simulation_replay_events ((doc->>'created_at'));
CREATE INDEX IF NOT EXISTS idx_simulation_replay_events_doc_gin ON simulation_replay_events USING gin (doc jsonb_path_ops);
