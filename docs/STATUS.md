# CrucibAI Status

Last updated: 2026-04-08

## Current Branch

`main`

## Current Objective

Continue phase-locked hardening and proof from `main`, preserving the unified outcome platform wedge while moving through the remaining phases in order. Current execution focus: raise the core pipeline toward 10/10 by measuring repeatability across app categories instead of relying on a single happy-path proof.

## Confirmed Direction

- PostgreSQL is the only primary database.
- MongoDB references in primary docs and CI are treated as drift.
- The golden path is prompt/import to plan, build, proof, preview, iterate, export/deploy.
- CrucibAI's category wedge is the unified outcome platform: state the idea, build it, then automate it.
- The differentiator to preserve while hardening is the `run_agent` bridge: the same AI that builds the app runs inside user automations.
- Security hardening for terminal/git/workspace operations is required before public launch.
- Work should be committed in small slices and pushed directly to `main` unless the owner says otherwise.

## Resume Point

Exact external reference requested by the owner, `/home/claude/CRUCIBAI_WHAT_IT_IS_COMPLETE.md`, was not present in this Windows workspace or WSL. Nearest repo references read:

- `README.md`: "State the idea. We build it." and app-building AI inside automations.
- `docs/CRUCIBAI_SOURCE_BIBLE.md`: `run_agent` bridge and competitive-position sections.
- `docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md`: "The same AI that builds your app runs inside your automations."

Next implementation should continue from Phase 2/4 overlap, prioritizing runtime risk plus the golden path: tenant isolation, backend router extraction, proof/preview/deploy recovery, and product-surface beta gating.

Latest completed golden-path proof:

- Live Railway production replay completed `18/18` steps for job `8c3273ef-297e-4953-80b2-78356036a34b`.
- Live LLM invocation, preview boot, elite proof, deploy build, deploy publish readiness, and background runner stability passed.
- Evidence lives under `proof/live_production_golden_path/`.

Latest active 10/10 scoring work:

- `benchmarks/repeatability_prompts_v1.json` defines the first 50-prompt repeatability suite.
- `scripts/run-repeatability-benchmark.py` produces a deterministic scorecard under `proof/benchmarks/repeatability_v1/`.
- `scripts/release-gate.ps1` runs the repeatability tests and scorecard in backend-only mode.

## Known Risks

- `backend/server.py` is too large and mixes too many domains.
- Terminal execution is scoped and launch-gated, but still needs a real per-user sandbox/container boundary before broad public exposure.
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
- [x] Commit and push the release-gate slice (`825c3bd`).
- [x] Add a Cerebras context-window guard in the shared agent LLM path.
- [x] Add the LLM routing guard test to the release gate.
- [x] Add focused coverage so large build prompts require Anthropic instead of silently hitting Cerebras.
- [x] Commit and push the LLM context-window guard slice (`b120bbb`).
- [x] Reduce the FrontendAgent system prompt by replacing the giant example app with a compact JSON contract.
- [x] Verify FrontendAgent compiles and prompt size is materially lower.
- [x] Commit and push the FrontendAgent prompt compaction slice (`8f4d895`).
- [x] Add `backend\agents\frontend_agent.py` to the release-gate compile list.
- [x] Commit and push the release-gate compile coverage update (`1020791`).
- [x] Confirm the requested external `/home/claude/CRUCIBAI_WHAT_IT_IS_COMPLETE.md` was unavailable locally and record the nearest repo source-of-truth docs (`ec06ffa`).
- [x] Require authentication for the generic LLM-backed `/api/agents/run/generic` endpoint.
- [x] Add executor coverage proving a `run_agent` automation action calls the app-building agent callback with substituted prior-step output.
- [x] Add prompt-to-automation smoke coverage proving `/api/agents/from-description` can save a `run_agent` action from a natural-language description.
- [x] Add the prompt-to-automation and automation `run_agent` bridge checks to the backend release gate.
- [x] Add route-level smoke coverage proving a saved automation with a `run_agent` action can run and persist the agent output.
- [x] Add provider readiness module and `/api/health/llm` readiness endpoint without exposing secret values.
- [x] Add provider readiness tests and include them in the backend release gate.
- [x] Pin Node 22 for repo/frontend/Docker runtime paths while preserving `frontend/package.json` engines (`>=18 <=22`).
- [x] Add frontend runtime proof script and proof artifacts under `proof/frontend_runtime_gate/`.
- [x] Prove the frontend Docker build under Node 22 succeeds.
- [x] Convert `railway.json` to Dockerfile-based Railway deployment config with `/api/health` healthcheck.
- [x] Add Railway readiness verifier and proof artifacts under `proof/railway_verification/`.
- [x] Prove the full Railway-style Docker image builds and boots locally with `/api/health` 200.
- [x] Add deterministic golden-path wiring proof artifacts under `proof/e2e_golden_path/`.
- [x] Add `proof/END_TO_END_PROOF_REPORT.md` with the pass/fail matrix and remaining live-proof gaps.
- [x] Add `get_authenticated_or_api_user` and require it for LLM/action routes that previously accepted anonymous optional auth.
- [x] Preserve optional auth only for public/read-only catalog routes, anonymous-empty user panels, advisory estimate/history listings, marketplace, and conditional project-owner framework detection.
- [x] Require authenticated owner access for chat history instead of reading by `session_id` alone.
- [x] Require authenticated owner access before adding blueprint session messages; anonymous public-widget mutation is no longer accepted without owner auth.
- [x] Add terminal cross-user execution denial that returns `404` for another user's session.
- [x] Add Phase 2 runtime tests for anonymous LLM/action rejection, chat-history tenant scoping, blueprint persona isolation, blueprint session-message isolation, and terminal cross-user denial.
- [x] Add source-audit tests for remaining optional-auth routes, websocket project-progress auth, and blueprint optional-auth usage.
- [x] Add `scripts/phase2-security-audit.py` to generate reproducible route inventory and proof artifacts under `proof/phase2_security/`.
- [x] Add the Phase 2 route/websocket audit to `scripts/release-gate.ps1`.
- [x] Preserve preview and elite-builder verifier `failure_reason` / failed-check metadata through `verify_step`.
- [x] Add explicit deploy build/publish failure reasons, including readiness-only publish when no live deploy URL is configured.
- [x] Add `failure_reason` and `failure_details` to the Postgres jobs schema so failure persistence does not crash during late-stage pipeline errors.
- [x] Replace generic background wrapper `background_crash` persistence with explicit `background_runner_exception` metadata.
- [x] Add late-stage pipeline failure tests and include them in `scripts/release-gate.ps1`.
- [x] Add deterministic crash-fix proof artifacts under `proof/pipeline_crash_fix/`.

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
- `.\scripts\release-gate.ps1 -BackendOnly` passed after LLM guard update: smoke 28 passed, 24 deselected; tool agent guard 8 passed, 18 deselected.
- `python -m py_compile backend\agents\frontend_agent.py` passed after prompt compaction.
- `python -m pytest backend\tests\test_agents.py backend\tests\test_tool_agents.py -k "frontend_agent or base_agent or large_cerebras" -q` passed: 9 passed, 41 deselected.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after adding FrontendAgent to compile gate: smoke 28 passed, 24 deselected; tool agent guard 8 passed, 18 deselected.
- `.\scripts\verify-local.ps1` correctly failed on Node `v24.14.0`; the frontend declares Node `>=18 <=22`.
- `python -m py_compile backend\server.py backend\automation\executor.py` passed after generic agent auth hardening.
- Initial focused automation test attempt failed before exercising code because the shell had a stale `DATABASE_URL` for user `username`; rerun used `DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai` and `REDIS_URL=redis://127.0.0.1:6381/0`.
- `python -m pytest backend\tests\test_automation.py -k "run_agent" -q` passed with local Postgres/Redis env: 1 passed, 6 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "agent_run_generic or agents_from_description" -q` passed with local Postgres/Redis env: 3 passed, 52 deselected.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after adding automation bridge coverage: smoke 31 passed, 24 deselected; automation bridge 1 passed, 6 deselected; tool agent guard 8 passed, 18 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "agent_run_executes_run_agent_action" -q` passed with local Postgres/Redis env: 1 passed, 55 deselected.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after adding the route-level run-agent action smoke: smoke 32 passed, 24 deselected; automation bridge 1 passed, 6 deselected; tool agent guard 8 passed, 18 deselected.
- `python -m py_compile backend\provider_readiness.py backend\server.py scripts\generate-e2e-golden-path-proof.py` passed.
- PowerShell parser check passed for `scripts\frontend-runtime-gate.ps1`, `scripts\provider-preflight.ps1`, `scripts\verify-railway-readiness.ps1`, `scripts\verify-local.ps1`, `run-dev.ps1`, and `scripts\release-gate.ps1`.
- `python -m pytest backend\tests\test_provider_readiness.py backend\tests\test_smoke.py -k "provider_readiness or health_llm" -q` passed with local Postgres/Redis env: 6 passed, 56 deselected.
- `.\scripts\frontend-runtime-gate.ps1 -RunDockerBuild` generated `proof\frontend_runtime_gate\` and passed the Node 22 Docker frontend build.
- `.\scripts\provider-preflight.ps1` generated `proof\provider_readiness\`; local shell had no live LLM provider keys, so status was `not_configured` and live invocation was `not_run`.
- `.\scripts\verify-railway-readiness.ps1 -RunDockerBuild -RunContainerHealth` generated `proof\railway_verification\`; static config passed, full Docker image build passed, and local container health returned 200.
- `python scripts\generate-e2e-golden-path-proof.py` generated `proof\e2e_golden_path\` as production-faithful wiring proof with live LLM and browser screenshot explicitly marked `NOT_RUN`.
- `.\scripts\verify-local.ps1` completed despite active Node `v24.14.0` by generating frontend runtime proof and skipping host frontend dependency checks.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after provider readiness additions: smoke 33 passed, 24 deselected; provider readiness 5 passed; automation bridge 1 passed, 6 deselected; tool agent guard 8 passed, 18 deselected.
- `python -m py_compile backend\server.py backend\modules_blueprint.py scripts\phase2-security-audit.py` passed.
- First Phase 2 pytest attempt failed before tests because the shell had a placeholder `DATABASE_URL` for user `username`; rerun used local Postgres/Redis env.
- `python -m pytest backend\tests\test_smoke.py -k "phase2 or terminal" -q` passed with local Postgres/Redis env: 15 passed, 52 deselected.
- `python -m pytest backend\tests\test_phase2_security.py -q` passed with local Postgres/Redis env: 3 passed.
- `python scripts\phase2-security-audit.py --fail-on-unclassified` generated `proof\phase2_security\` and passed with 13 optional routes inventoried and 0 failures.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after Phase 2 audit additions: smoke 43 passed, 24 deselected; Phase 2 audit 3 passed; optional-auth audit 13 routes, 0 failures; provider readiness 5 passed; automation bridge 1 passed, 6 deselected; LLM routing guard 8 passed, 18 deselected.
- `python -m py_compile backend\db_pg.py backend\orchestration\verifier.py backend\orchestration\executor.py backend\orchestration\auto_runner.py backend\server.py scripts\generate-pipeline-crash-fix-proof.py` passed.
- Initial focused pipeline pytest attempt failed before exercising code because the shell had a placeholder `DATABASE_URL` for user `username`; rerun used local Postgres/Redis env.
- `python -m pytest backend\tests\test_pipeline_crash_fix.py -q` passed with local Postgres/Redis env: 7 passed.
- `python -m pytest backend\tests\test_smoke.py -k "background_runner" -q` passed with local Postgres/Redis env: 1 passed, 67 deselected.
- `python -m pytest backend\tests\test_verifier_deploy.py backend\tests\test_pipeline_crash_fix.py -q` passed with local Postgres/Redis env: 9 passed.
- `python scripts\generate-pipeline-crash-fix-proof.py` generated `proof\pipeline_crash_fix\` and passed all five PASS/FAIL checks: preview boot, elite/proof verification, deploy build, deploy publish, and background runner stability.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after late-stage pipeline crash fixes: smoke 44 passed, 24 deselected; pipeline crash fix 7 passed; Phase 2 audit 3 passed; optional-auth audit 13 routes, 0 failures; provider readiness 5 passed; automation bridge 1 passed, 6 deselected; LLM routing guard 8 passed, 18 deselected.
- `python -m pytest backend\tests\test_smoke.py -k "visual_edit or template_remix or terminal_execute_blocks_dangerous_commands or critical_endpoints" -q` passed with local Postgres/Redis env: 5 passed, 68 deselected.
- `.\scripts\release-gate.ps1 -BackendOnly` passed after Batch B UX/security work: smoke 48 passed, 25 deselected; pipeline crash fix 14 passed; repeatability benchmark 2 passed; Phase 2 audit 3 passed with 14 optional routes and 0 failures; provider readiness 5 passed; automation bridge 1 passed, 6 deselected; LLM routing guard 8 passed, 18 deselected.
- `.\scripts\frontend-runtime-gate.ps1 -RunDockerBuild` passed after completion-card and template-gallery changes; host Node remains v24.14.0, Docker Node 22 path remains green.

## Next Milestone

Phase 3: Backend Router Extraction

Planned tasks:

- Continue extracting coherent route modules from `backend/server.py` after trust routes moved into `backend/routes/trust.py`.
- Upgrade visual editing from deterministic text/style replacement to click-to-component selection and AI patch preview.
- Replace terminal host-shell execution with a per-project container sandbox before broad public exposure.
- Preserve the release-gate and proof artifacts as the regression bar while extracting routers.
