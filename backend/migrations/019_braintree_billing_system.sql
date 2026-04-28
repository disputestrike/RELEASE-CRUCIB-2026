-- Braintree billing management system.
-- The application uses the existing JSONB document-store convention:
--   id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}'
-- Historical Stripe identifiers remain inside doc as nullable/deprecated fields
-- for audit/migration instead of being deleted.

CREATE TABLE IF NOT EXISTS businesses (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS prices (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS payment_methods (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS billing_events (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS entitlements (id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}');

CREATE INDEX IF NOT EXISTS idx_businesses_doc_gin ON businesses USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_products_doc_gin ON products USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_prices_doc_gin ON prices USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_customers_doc_gin ON customers USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_payment_methods_doc_gin ON payment_methods USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_subscriptions_doc_gin ON subscriptions USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_orders_doc_gin ON orders USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_billing_events_doc_gin ON billing_events USING GIN (doc);
CREATE INDEX IF NOT EXISTS idx_entitlements_doc_gin ON entitlements USING GIN (doc);

CREATE INDEX IF NOT EXISTS idx_prices_product_active
    ON prices ((doc->>'product_id'), (doc->>'billing_type'), (doc->>'active'));
CREATE INDEX IF NOT EXISTS idx_customers_user
    ON customers ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_payment_methods_user
    ON payment_methods ((doc->>'user_id'));
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_product
    ON subscriptions ((doc->>'user_id'), (doc->>'product_id'), (doc->>'status'));
CREATE INDEX IF NOT EXISTS idx_orders_user_product
    ON orders ((doc->>'user_id'), (doc->>'product_id'), (doc->>'status'));
CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_events_idempotent
    ON billing_events ((doc->>'event_provider'), (doc->>'event_type'), (doc->>'braintree_webhook_id'));
