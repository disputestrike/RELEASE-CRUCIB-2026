#!/usr/bin/env bash
# Full backend verification for CI or local parity with GitHub Actions.
# Requires: Postgres + Redis reachable via DATABASE_URL / REDIS_URL; Python deps from backend/requirements.txt
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
export GITHUB_ACTIONS="${GITHUB_ACTIONS:-true}"
export DISABLE_CSRF_FOR_TEST="${DISABLE_CSRF_FOR_TEST:-1}"
export CRUCIBAI_TEST="${CRUCIBAI_TEST:-1}"
export CRUCIBAI_DEV="${CRUCIBAI_DEV:-1}"

echo "== pytest (full backend suite) =="
python -m pytest tests/ -q --tb=short --ignore=tests/run_production_validation.py

echo "== API health (uvicorn smoke) =="
PORT="${CI_HEALTH_PORT:-18999}"
BASE="http://127.0.0.1:${PORT}"
python -m uvicorn server:app --host 127.0.0.1 --port "$PORT" &
UV_PID=$!
sleep "${CI_HEALTH_SLEEP:-10}"
curl -fsS "${BASE}/api/health" | head -c 400
echo
echo "== deploy healthcheck script (repo) =="
bash "$ROOT/deploy/healthcheck.sh" "${CI_API_BASE_URL:-$BASE}"
kill "$UV_PID" || true
wait "$UV_PID" 2>/dev/null || true

echo "ci_verify_backend.sh: OK"
