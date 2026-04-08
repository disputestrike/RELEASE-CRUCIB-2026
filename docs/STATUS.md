# CrucibAI Status

Last updated: 2026-04-08

## Current Branch

`main`

## Current Objective

Continue Phase 2 execution-surface hardening on `main`, with every approved slice committed and pushed directly to GitHub.

## Confirmed Direction

- PostgreSQL is the only primary database.
- MongoDB references in primary docs and CI are treated as drift.
- The golden path is prompt/import to plan, build, proof, preview, iterate, export/deploy.
- Security hardening for terminal/git/workspace operations is required before public launch.
- Work should be committed in small slices and pushed directly to `main` unless the owner says otherwise.

## Known Risks

- `backend/server.py` is too large and mixes too many domains.
- Remaining optional-auth routes must be reviewed before public launch.
- Fresh checkout setup requires dependency and environment bootstrapping.
- The full test suite was not run in this checkout before foundation fixes because frontend dependencies and local database setup were not ready.

## Active Milestone

Phase 2: Execution Surface Hardening

Tasks:

- [x] Create a dedicated working branch.
- [x] Add execution plan and status tracking docs.
- [x] Update docs to say Postgres-only in primary setup/deploy paths.
- [x] Update CI backend service from MongoDB to PostgreSQL/Redis.
- [x] Add or update local verification workflow.
- [x] Add ADR for workspace execution boundaries.
- [x] Commit the first foundation slice (`ac8d205`).
- [x] Require authentication for terminal create/execute/close.
- [x] Require authenticated project workspace resolution for git operations.
- [x] Update IDE Git/Terminal panels to use bearer auth and `project_id`.
- [x] Add focused smoke coverage for terminal/git auth and raw path rejection.
- [x] Commit the first execution-surface hardening slice (`02f2fff`).
- [x] Require authentication and project ownership checks for IDE debug/lint/profiler routes.
- [x] Bind debugger/profiler sessions to the authenticated user.
- [x] Update IDE Debug/Lint/Profiler panels to send bearer auth.
- [x] Add focused smoke coverage for IDE auth and ownership checks.
- [x] Commit and push the IDE execution-surface hardening slice (`0bb5886`).
- [x] Require authentication and task ownership for app database schema/provision routes.
- [x] Require authentication and task ownership for the legacy Vercel deploy helper.
- [x] Require admin access for agent cache invalidation.
- [x] Require authentication and project ownership when framework detection reads project metadata.
- [x] Add focused smoke coverage for app-db, cache invalidation, legacy deploy, and project-backed framework detection.
- [x] Commit and push the optional-auth state route hardening slice (`57b4011`).
- [x] Require authentication for agent memory store/list routes.
- [x] Require authentication for agent automation store/list routes.
- [x] Scope agent memory and automation list routes to the authenticated user.
- [x] Add focused smoke coverage for agent memory and automation auth/tenant isolation.
- [ ] Commit and push the agent memory/automation tenant isolation slice.

## Verification Log

- `python -m py_compile backend\server.py backend\terminal_integration.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "git_status or terminal" -q` passed with `DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai` and `REDIS_URL=redis://127.0.0.1:6381/0`: 5 passed, 17 deselected.
- `python -m py_compile backend\server.py backend\ide_features.py backend\terminal_integration.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "ide_ or git_status or terminal" -q` passed with `DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai` and `REDIS_URL=redis://127.0.0.1:6381/0`: 10 passed, 16 deselected.
- `python -m py_compile backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 9 passed, 23 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "ide_ or git_status or terminal or app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 19 passed, 13 deselected.
- `python -m py_compile backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "agent_memory or agent_automation or app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 13 passed, 23 deselected.
- `.\scripts\verify-local.ps1` correctly failed on Node `v24.14.0`; the frontend declares Node `>=18 <=22`.

## Next Milestone

Phase 2: Execution Surface Hardening

Planned tasks:

- Continue reviewing remaining optional-auth routes and classify them as public, authenticated, or admin-only.
- Add tenant-isolation regression tests beyond smoke coverage where high-risk endpoints remain.
- Decide whether terminal execution is removed, sandboxed, or admin-only for launch.
