# Testing Guide

This repository uses layered validation to gate releases.

## Primary commands

- `node scripts/run-full-27-tests.js`
- `powershell -ExecutionPolicy Bypass -File scripts/full-systems-test.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/validate_unified_workspace_patch.ps1`

## Backend quick checks

- `python -m pytest backend/tests/test_api_contract.py -q`
- `python -m pytest backend/tests/test_smoke.py -q`

## Frontend quick checks

- `cd frontend && npm test -- --watch=false`
- `cd frontend && npm run build`

## Notes

- For local full-systems runs, ensure Docker and local infra are available when running Docker-backed gates.
- Live-production checks require a reachable deployed base URL.
