# CrucibAI Backend Deployment Guide

The backend is FastAPI on PostgreSQL. MongoDB is not part of the current deployment path.

## Requirements

- Python 3.11+
- PostgreSQL with `DATABASE_URL`
- Redis with `REDIS_URL` recommended
- `JWT_SECRET`
- At least one AI provider key for real builds, preferably `ANTHROPIC_API_KEY`

## Local Backend

From the repo root:

```powershell
docker compose up -d postgres redis
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'
$env:REDIS_URL='redis://127.0.0.1:6381/0'
$env:JWT_SECRET='dev-secret-change-me-at-least-32-chars'
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

Or run the repo bootstrap:

```powershell
.\run-dev.ps1
```

## Railway

Use the root `Dockerfile`, attach Railway Postgres, and set:

```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=<strong-random-secret>
ANTHROPIC_API_KEY=<optional-real-builds>
CORS_ORIGINS=https://your-frontend.example
FRONTEND_URL=https://your-frontend.example
```

Keep `CRUCIBAI_TERMINAL_ENABLED` unset or `0` for public launch unless terminal execution is isolated in a trusted sandbox.

## Health Checks

```powershell
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/ready
```

`/api/health` is process liveness. `/api/health/ready` checks Postgres readiness.

## Verification

```powershell
python -m py_compile backend\server.py
$env:DATABASE_URL='postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'
$env:REDIS_URL='redis://127.0.0.1:6381/0'
python -m pytest backend\tests\test_smoke.py -q
```

## Backups

Use PostgreSQL backups, for example Railway Postgres backups or `pg_dump`:

```powershell
pg_dump $env:DATABASE_URL > crucibai-backup.sql
```
