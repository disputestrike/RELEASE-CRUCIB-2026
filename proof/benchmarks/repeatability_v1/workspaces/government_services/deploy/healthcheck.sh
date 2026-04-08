#!/bin/sh
# CrucibAI — minimal HTTP health probe (run from repo / CI after API is up)
set -e
API_URL="${API_URL:-http://127.0.0.1:8000}"
curl -sf "${API_URL}/health" >/dev/null
echo "ok ${API_URL}/health"
