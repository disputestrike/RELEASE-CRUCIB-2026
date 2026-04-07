# Operations runbook (CrucibAI)

Concise on-call reference. Fifty-point tracker: [`FIFTY_POINT_STATUS.md`](./FIFTY_POINT_STATUS.md).

## Severity triage

1. **API down or 5xx spike** — check load balancer / process health, then DB and Redis.
2. **Auth or data leak suspicion** — rotate `JWT_SECRET`, review recent deploys, enable `CRUCIBAI_REAL_AGENT_ONLY=1` on builder nodes if stubs are a concern.
3. **Build pipeline stuck** — inspect orchestration job row, `runtime_state`, cancel/resume endpoints; see `DATABASE.md` for job tables.

## Health checks

| Probe | Use |
|--------|-----|
| `GET /api/health` | Cheap liveness (no DB). |
| `GET /api/health/live` | Explicit liveness. |
| `GET /api/health/ready` | Readiness (503 if DB unreachable). |

Shell: `deploy/healthcheck.sh https://api.example.com` (optional second arg `live` or `ready`).

## Rollback

1. Re-deploy previous container image / Git revision (Railway, Docker, or your host).
2. Run DB migrations **down** only if a migration is confirmed broken; otherwise prefer forward-fix migrations.
3. Invalidate CDN if static assets changed.

## Logs and correlation

- Structured logging env: see `CRUCIBAI_STRUCTURED_LOGS` in `backend/.env.example`.
- OpenTelemetry: `CRUCIBAI_OTEL` and `orchestration/observability.py`.

## CI gate

Primary merge gate: GitHub Actions workflow **Verify full stack** — job **`verify-all-passed`**. Require it under branch protection for `main`. Automation and UI steps: [`BRANCH_PROTECTION.md`](./BRANCH_PROTECTION.md) (`scripts/enable_branch_protection.ps1`).

### Enable branch protection (GitHub UI)

1. Repo **Settings** → **Branches** → **Add branch protection rule** (or edit existing) for `main`.
2. Enable **Require status checks to pass before merging**.
3. Search for and require **`verify-all-passed`** (the job name from `.github/workflows/ci-verify-full.yml`).  
   If GitHub shows the workflow file name instead, pick the check that corresponds to that job.
4. Optionally require **up-to-date branches** before merge.

## API versioning

Public routes live under **`/api/...`** without a `/v1` prefix today. Breaking API changes should be announced in release notes; reserve **`/api/v1`** (or headers) for a future stable surface.

## Sessions and JWT

Access tokens are JWTs signed with **`JWT_SECRET`**. Rotating the secret logs everyone out. For stricter session hygiene, use short expiries and a separate refresh flow (product-specific).

## Static SPA + CSP

The API sets **`SecurityHeadersMiddleware`** (Sandpack-aware CSP). The React app’s **`public/index.html`** adds **Referrer-Policy** and **X-Content-Type-Options**. For production, your CDN or nginx can mirror or tighten **`Content-Security-Policy`** on static `index.html` responses.

## Environment matrix (short)

| Tier | `CRUCIBAI_DEV` | `DATABASE_URL` | Notes |
|------|----------------|----------------|-------|
| Local | `1` | Docker / local Postgres | `RUN.md`, `run-docker-deps.ps1` |
| CI | — | GitHub Actions service | `ci-verify-full.yml` |
| Production | `0` | managed Postgres | Set `JWT_SECRET`, LLM keys, optional `CRUCIBAI_CONTENT_POLICY_STRICT` |

## Incident contacts

Fill in your team PagerDuty / Slack channel here in your fork (not committed secrets).

## Post-incident

Capture a short root-cause summary (timeline, blast radius, fix PR links) in your issue tracker or internal wiki; link the deploy that contains the fix.
