CREATE TABLE IF NOT EXISTS braintree_transactions (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS braintree_webhook_events (
    id TEXT PRIMARY KEY,
    doc JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_braintree_transactions_doc_gin
ON braintree_transactions USING gin (doc jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_braintree_webhook_events_doc_gin
ON braintree_webhook_events USING gin (doc jsonb_path_ops);
