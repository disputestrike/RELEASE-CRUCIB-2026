#!/usr/bin/env bash
# Local automated checks for the control-plane program (no Railway).
# Run from repo root: RELEASE-CRUCIB-2026/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export CRUCIB_TEST_SQLITE=1
export CRUCIBAI_TEST_DB_UNAVAILABLE=1
echo "== pre_release_sanity: app + route smoke =="
python scripts/pre_release_sanity.py
echo "== control plane: pytest (transcript + capabilities + import hygiene) =="
cd "$ROOT/backend"
python -m pytest \
  tests/test_control_plane_transcript.py \
  tests/test_projects_capabilities_endpoint.py \
  tests/test_cors_policy.py \
  tests/test_route_loading.py \
  tests/test_repair_loop.py \
  tests/test_idempotency_header_golden.py \
  -q
cd "$ROOT"
echo "== done =="
