# Stress-test build brief (“if this ships, the pipeline is real”)

Paste the **Goal text** below as a single user/build goal. It is tuned so `uses_agent_swarm()` sees enough markers (`multi-tenant`, `tenant isolation`, `compliance`, `immutable audit`, `background jobs`, `worker/job system`, `integration adapters`, `analytics/reporting`, `crm`, `quote workflow`, `project workflow`, `policy engine`) without sounding random.

Use **after** deploy smoke passes (`scripts/railway_release_smoke.py`). Expect long runtime, many swarm steps, heavy LLM/tool use.

---

## Goal text (copy everything between the lines)

```
Build Helios Operations Cloud — an elite autonomous multi-tenant B2B SaaS for regulated teams.

MULTI-TENANT & ISOLATION (mandatory): Strict tenant isolation per organization (Org → Workspace → Project). Row-level security semantics in the app layer; no cross-tenant reads. Per-tenant feature flags and usage metering.

CRM & PIPELINES: Full CRM module (accounts, contacts, deals, activities, tasks). Quote workflow with configurable approval stages, PDF export, e-sign handoff placeholder. Project workflow linking deals to delivery milestones and time tracking.

COMPLIANCE & AUDIT: Compliance mode (GDPR-oriented): export/delete requests, consent logs, data retention windows. Immutable audit trail for security-relevant actions (who/when/what/before-after hash). Policy engine for role-based rules (e.g. “finance can approve quotes over $50k”) with evaluation logs.

BACKGROUND JOBS & WORKERS: Worker/job system for long tasks — email digests, report generation, bulk imports, webhook retries, scheduled CRM sync jobs. Idempotent handlers, dead-letter queue concept, job status UI for admins.

INTEGRATION ADAPTERS: Pluggable integration adapters — REST connector framework, OAuth2 client flow skeleton, webhook ingress with signature verification, mapping UI for field sync (CRM ↔ external system). At least one “mock ERP” adapter for demos.

ANALYTICS & REPORTING: Analytics/reporting dashboards — funnel metrics, sales velocity, SLA breaches, audit stats. Export CSV; scheduled weekly summary emails via background jobs.

PRODUCT SURFACES: React + TypeScript SPA (role-based navigation), FastAPI backend, PostgreSQL, Redis for queues/cache. Real-time updates for task/quote status (WebSockets or SSE). Auth: email/password + session/JWT; org invites.

DEPLOYMENT & OPS: Dockerized services, env-based config, health checks, structured logging. Payment placeholder (Stripe-style) for subscription tiers (no live charges in dev).

Deliver production-grade code: schemas, migrations, API contracts, tests for critical paths, README with local run instructions. Name the product “Helios Operations Cloud” in UI copy.

This build should exercise the full system: planning, architecture, schema, backend APIs, frontend, integrations, security posture, jobs, and deployment story — multiple phases, not a toy demo.
```

---

## What you are validating

| Area | Signal |
|------|--------|
| Swarm / multi-step | Long DAG, many agents, workspace tool loop |
| Writes & gates | Real files, language/pollution gates, repair paths |
| Memory / staged workflow | Build memory, convergence across steps |
| Integrations narrative | Adapters + webhooks (even if sandboxed) |
| Ops story | Jobs, audit, reporting — stresses reasoning + structure |

---

## How to interpret results

- **Success:** App serves; core flows sketched or implemented; job/audit/integration pieces exist as coherent modules; build completes or fails with actionable errors.
- **Partial:** Some modules stubs — still useful: note which agents failed verification.
- **Failure:** Use logs, `tool_loop` / `anthropic_usage`, and verifier output — that is the backlog, not “the model failed.”

---

## Optional constraints (add to the goal if your product supports hints)

- “Target stack: React + Vite + TypeScript, FastAPI, PostgreSQL, Redis, Docker.”
- “Prioritize backend contracts and DB schema before UI polish.”

Do **not** run this alongside unrelated destructive tests on production credentials.
