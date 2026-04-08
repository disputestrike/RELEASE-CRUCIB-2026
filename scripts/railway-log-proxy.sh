#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CRUCIBAI_BASE_URL:-https://crucibai-production.up.railway.app}"

if [[ "${1:-}" != "logs" ]]; then
  echo "railway-log-proxy only supports: railway logs -e production" >&2
  exit 1
fi

python - "$BASE_URL" <<'PY'
import json
import sys
from urllib import request

base = sys.argv[1].rstrip("/")
with request.urlopen(f"{base}/api/debug/agent-selection-logs", timeout=60) as resp:
    payload = json.loads(resp.read().decode("utf-8"))
for line in payload.get("logs", []):
    print(line)
PY
