# Production sketch checklist (CrucibAI)

- [ ] Secrets only in env — run production gate scan (deploy.build verification)
- [ ] Stripe: webhook signature + `stripe_events_processed` idempotency table
- [ ] Multi-tenant: apply `db/migrations/002_multitenancy_rls.sql` (RLS on `app_items`); extend policies to other tables
- [ ] Auth: replace client-demo tokens with server session or JWT validation
- [ ] Observability: JSON logs + trace context; optional `deploy/observability/*.stub.*` for local OTel/Prometheus/Grafana
- [ ] Multi-region: if `terraform/multiregion_sketch` exists, add remote state, networking, replication, DNS before apply
- [ ] CI: run `deploy/healthcheck.sh` with `API_URL` after deploy; optional `CRUCIBAI_API_SMOKE_URL` for in-runner live GET
