#!/usr/bin/env bash
# HTTP health probe for the CrucibAI API (use in Docker / CI / load balancers).
# Usage: ./deploy/healthcheck.sh [BASE_URL] [live|ready|""]
#   (default)  — GET /api/health (liveness-style, no DB)
#   live       — GET /api/health/live
#   ready      — GET /api/health/ready (503 if DB down)
set -euo pipefail
BASE="${1:-${API_BASE_URL:-http://127.0.0.1:8000}}"
BASE="${BASE%/}"
MODE="${2:-}"
if [[ "$MODE" == "ready" ]]; then
  PATH_SUFFIX="/api/health/ready"
elif [[ "$MODE" == "live" ]]; then
  PATH_SUFFIX="/api/health/live"
else
  PATH_SUFFIX="/api/health"
fi
curl -fsS "${BASE}${PATH_SUFFIX}" >/dev/null
echo "healthcheck OK: ${BASE}${PATH_SUFFIX}"
