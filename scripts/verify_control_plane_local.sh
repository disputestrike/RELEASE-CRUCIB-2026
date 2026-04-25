#!/usr/bin/env bash
# Local automated checks for the control-plane program (no Railway).
# Run from repo root: RELEASE-CRUCIB-2026/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
echo "== control plane: pytest (transcript + capabilities) =="
python -m pytest \
  backend/tests/test_control_plane_transcript.py \
  backend/tests/test_projects_capabilities_endpoint.py \
  -q
echo "== done =="
