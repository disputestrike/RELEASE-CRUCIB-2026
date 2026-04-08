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
- [x] Commit and push the agent memory/automation tenant isolation slice (`37d90ca`).
- [x] Require job ownership before retrying a failed/blocked job step.
- [x] Add focused smoke coverage for owned and unowned retry-step attempts.
- [x] Commit and push the retry-step ownership slice (`6c09d38`).
- [x] Ignore client-supplied `workspace_path` in Auto-Runner start and derive workspace from the job project.
- [x] Add focused smoke coverage proving Auto-Runner ignores malicious request workspace paths.
- [x] Commit and push the Auto-Runner workspace boundary slice (`e6399cd`).
- [x] Require project ownership before creating plans/jobs with a supplied `project_id`.
- [x] Preserve 404/403 errors from plan/job creation instead of converting them to 500s.
- [x] Add focused smoke coverage for owned and unowned plan/job creation.
- [x] Commit and push the plan/job project ownership slice (`9d0b580`).
- [x] Move router inclusion after all API route declarations and mount frontend static last.
- [x] Add task-specific app-db route to avoid project/task dynamic route collisions.
- [x] Add task ownership checks for GitHub sync and Railway deploy helpers.
- [x] Add focused smoke coverage for Git sync/Railway deploy unowned task/project rejection.
- [x] Commit and push the late-route registration and deploy ownership slice (`412141d`).
- [x] Replace terminal command execution `shell=True` with explicit shell invocation using `shell=False`.
- [x] Add focused smoke verification that scoped terminal execution still works on Windows.
- [x] Commit and push the terminal shell hardening slice (`6cf1e13`).
- [x] Upgrade `run-dev.ps1` to check Node, start Postgres/Redis, install frontend deps when missing, and use Postgres-only dev env.
- [x] Add `docs/POSTGRES_ONLY_MIGRATION.md`.
- [x] Add `docs/LOCAL_RUNBOOK.md`.
- [x] Validate PowerShell syntax for `run-dev.ps1` and `scripts/verify-local.ps1`.
- [x] Commit and push the local bootstrap/runbook slice (`f90cf30`).
- [x] Require a valid JWT and project ownership before accepting project progress websocket connections.
- [x] Update frontend project progress websocket callers to pass encoded auth tokens.
- [x] Commit and push the websocket project progress auth slice (`8e0ac58`).
- [x] Require project ownership for blueprint app-db schema provisioning when a `project_id` is supplied.
- [x] Add focused smoke coverage for unowned blueprint app-db project rejection.
- [x] Commit and push the blueprint app-db ownership slice (`ccb2e5a`).
- [x] Require authenticated owner access for stateful job/proof/stream endpoints.
- [x] Reject legacy unowned job records from stateful job/proof execution surfaces.
- [x] Add focused smoke coverage for unauthenticated and cross-user job state access.
- [x] Commit and push the job state ownership slice (`a6fbe8d`).
- [x] Add a stable build contract envelope to proof bundles.
- [x] Add focused smoke coverage proving job proof returns the build contract.
- [x] Commit and push the proof build-contract slice (`60cbe7e`).
- [x] Add an explicit `CRUCIBAI_TERMINAL_ENABLED` launch gate for terminal sessions and command execution.
- [x] Keep terminal enabled for test/dev by default while disabled by default in production.
- [x] Add focused smoke coverage for disabled terminal create/execute behavior.
- [x] Commit and push the terminal launch-gate slice (`da1225b`).
- [x] Replace stale Railway deployment guide with Postgres-only instructions.
- [x] Replace stale backend deployment guide with Postgres-only instructions.
- [x] Commit and push the deployment docs cleanup slice (`fa064b5`).
- [x] Add `scripts/release-gate.ps1` for backend security/proof smoke and optional frontend gate.
- [x] Validate the release-gate script parser and backend-only path.
- [ ] Commit and push the release-gate slice.

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
- `python -m py_compile backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "retry_step or agent_memory or agent_automation or app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 15 passed, 23 deselected.
- `python -m py_compile backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "run_auto or retry_step or agent_memory or agent_automation or app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 16 passed, 23 deselected.
- `python -m py_compile backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "orchestrator_plan or create_job or run_auto or retry_step" -q` passed with local Postgres/Redis env: 6 passed, 36 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "orchestrator_plan or create_job or run_auto or retry_step or agent_memory or agent_automation or app_db or cache_invalidate or detect_frameworks or deploy" -q` passed with local Postgres/Redis env: 19 passed, 23 deselected.
- `python -m py_compile backend\server.py backend\modules_blueprint.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "git_sync or railway_deploy or deploy or app_db" -q` passed with local Postgres/Redis env: 10 passed, 36 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "orchestrator_plan or create_job or run_auto or retry_step or agent_memory or agent_automation or app_db or cache_invalidate or detect_frameworks or deploy or git_sync or railway_deploy" -q` passed with local Postgres/Redis env: 23 passed, 23 deselected.
- `python -m py_compile backend\terminal_integration.py backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "terminal" -q` passed with local Postgres/Redis env: 3 passed, 43 deselected.
- PowerShell parser check passed for `run-dev.ps1`.
- PowerShell parser check passed for `scripts\verify-local.ps1`.
- `python -m py_compile backend\server.py` passed after project progress websocket auth changes.
- `python -m py_compile backend\modules_blueprint.py backend\server.py` passed.
- `python -m pytest backend\tests\test_smoke.py -k "app_db or git_sync or railway_deploy" -q` passed with local Postgres/Redis env: 9 passed, 38 deselected.
- `.\scripts\release-gate.ps1 -BackendOnly` passed: 28 passed, 24 deselected.
- `.\scripts\verify-local.ps1` correctly failed on Node `v24.14.0`; the frontend declares Node `>=18 <=22`.

## Next Milestone

Phase 2: Execution Surface Hardening

Planned tasks:

- Continue reviewing remaining optional-auth routes and classify them as public, authenticated, or admin-only.
- Add tenant-isolation regression tests beyond smoke coverage where high-risk endpoints remain.
- Decide whether terminal execution is removed, sandboxed, or admin-only for launch.
