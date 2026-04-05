#!/usr/bin/env bash
# HTTP health probe for the CrucibAI API (use in Docker / CI / load balancers).
# Usage: ./deploy/healthcheck.sh [BASE_URL]
set -euo pipefail
BASE="${1:-${API_BASE_URL:-http://127.0.0.1:8000}}"
BASE="${BASE%/}"
curl -fsS "${BASE}/api/health" >/dev/null
echo "healthcheck OK: ${BASE}/api/health"
