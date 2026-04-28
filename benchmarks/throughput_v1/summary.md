# Throughput v1 — Build-pipeline benchmark

- Prompts attempted: **3** (limit=10)
- API base: `http://localhost:8000`
- Per-prompt timeout: 600s, poll every 2.0s
- Success rate: **0.0%** (0/3)
- t_total p50: **n/a**, p95: **n/a** (successes only)

## Per-prompt results

| Prompt | t_plan (s) | t_total (s) | files | success |
|---|---:|---:|---:|:---:|
| todo_app | n/a | 0.01 | 0 | no |
| landing_page | n/a | 0.00 | 0 | no |
| rest_api_blog | n/a | 0.00 | 0 | no |

## Failure taxonomy

| Error prefix | Count |
|---|---:|
| `create_failed` | 3 |

## How to run locally

```bash
# 1. Install backend deps
pip install -r backend/requirements.txt

# 2. Start the API (requires Postgres configured via env)
PYTHONPATH=backend python3 -m uvicorn server:app \
    --host 127.0.0.1 --port 8000 --app-dir backend

# 3. Smoke run (3 prompts)
CRUCIBAI_API=http://127.0.0.1:8000 CRUCIBAI_PROMPT_LIMIT=3 \
    python3 benchmarks/throughput_v1/run.py

# 4. Full run (all 10)
CRUCIBAI_API=http://127.0.0.1:8000 \
    python3 benchmarks/throughput_v1/run.py
```

If you already have a JWT, set `CRUCIBAI_TOKEN=<jwt>` to skip the
`POST /api/auth/guest` fallback.

## How to run against prod

```bash
CRUCIBAI_API=https://crucibai-production.up.railway.app \
    CRUCIBAI_TOKEN=<jwt> \
    python3 benchmarks/throughput_v1/run.py
```

Obtain a JWT by signing in via the web app and copying the token
from localStorage / the `/auth?token=` redirect, or by calling
`POST /api/auth/login` with credentials.

## Next steps

- **v2**: add Lovable / Bolt / v0 comparison columns (same 10 prompts,
  same t_plan / t_total / files metrics, side-by-side in summary.md).
- Add a `--runs=N` flag to measure variance, not just point estimates.
- Capture per-step timings from `/api/jobs/{id}/steps` so we can
  break down plan vs. codegen vs. verify latency.

## Run notes

- Local smoke run (2026-04-22): backend started in **liveness-only mode** because
- `DATABASE_URL` was not set (Postgres is mandatory — `backend/db_pg.py`).
- As a result, `POST /api/auth/guest` returns 503 `Database not ready` and
- `POST /api/jobs/` returns 401 `Not authenticated`. All 3 smoke prompts recorded
- `create_failed` and `t_total ≈ 3 ms` (the request-error latency, not a build time).
- 
- To produce real local numbers: export `DATABASE_URL=postgres://...` (or run a
- local Postgres via docker) and set `FRONTEND_URL=http://localhost:8000` before
- launching uvicorn. Against the Railway prod deploy the DB is already wired and
- only a valid `CRUCIBAI_TOKEN` is needed — see “How to run against prod”.
- 
- Known failure taxonomy prefixes the script currently emits: `create_failed`,
- `poll_failed`, `create_no_job_id`, `timeout after Xs`, `exception`, plus any
- `error_message` / `failure_reason` the orchestrator stores on terminal jobs.
