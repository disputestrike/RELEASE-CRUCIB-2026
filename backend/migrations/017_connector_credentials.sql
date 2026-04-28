CREATE TABLE IF NOT EXISTS connector_credentials (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS connector_oauth_states (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_connector_credentials_doc_gin
ON connector_credentials USING gin (doc jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_connector_oauth_states_doc_gin
ON connector_oauth_states USING gin (doc jsonb_path_ops);
