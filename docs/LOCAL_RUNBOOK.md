# Local Runbook

Last updated: 2026-04-08

## Required Tools

- Python matching `.python-version`
- Node 20 or 22
- npm
- Docker Desktop for local Postgres and Redis
- Git

The frontend declares Node `>=18 <=22`. Node 24 is not supported by this repo right now.

## One-Command Start

From the repo root:

```powershell
.\run-dev.ps1
```

The script checks the toolchain, starts local Postgres and Redis through Docker Compose when ports `5434` and `6381` are not already reachable, installs frontend dependencies when `frontend/node_modules` is missing, starts the backend on `http://127.0.0.1:8000`, and starts the frontend on `http://localhost:3000`.

## Manual Start

Start dependencies:

```powershell
docker compose up -d postgres redis
```

Start backend:

```powershell
cd backend
$env:CRUCIBAI_DEV="1"
$env:CRUCIBAI_SKIP_NODE_VERIFY="1"
$env:DATABASE_URL="postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
$env:REDIS_URL="redis://127.0.0.1:6381/0"
$env:JWT_SECRET="dev-secret-do-not-use-in-production-123456"
$env:GOOGLE_CLIENT_ID="test.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET="test-google-client-secret"
$env:FRONTEND_URL="http://localhost:3000"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Start frontend in another terminal:

```powershell
cd frontend
npm install
$env:REACT_APP_BACKEND_URL="http://127.0.0.1:8000"
npm start
```

## Verification

Basic local verification:

```powershell
.\scripts\verify-local.ps1
```

Focused backend hardening smoke tests:

```powershell
$env:DATABASE_URL="postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
$env:REDIS_URL="redis://127.0.0.1:6381/0"
python -m pytest backend\tests\test_smoke.py -k "terminal or git_status or ide_ or app_db or run_auto or retry_step" -q
```

## Common Failures

- Node `v24.x`: install Node 20 or 22 and retry.
- `craco` missing: run `npm install` in `frontend`.
- Postgres connection refused: run `docker compose up -d postgres redis`.
- Backend import fails on env: use the manual backend env block above or `.\run-dev.ps1`.
