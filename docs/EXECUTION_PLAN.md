# CrucibAI Execution Plan

This is the operating plan for turning CrucibAI into a reliable, market-leading AI app builder. It is intentionally blunt: the vision is strong, but the product wins only if the core build loop is safe, repeatable, measurable, and delightful.

## North Star

CrucibAI should make one promise and keep it:

> Describe the product. CrucibAI plans it, builds it, proves it, lets you edit it, and helps you deploy it.

The golden path is:

1. User enters a goal or imports an existing codebase.
2. CrucibAI creates a plan with scope, risk, time, and cost.
3. User approves the plan.
4. The orchestrator builds in an isolated workspace.
5. The UI streams each step and artifact.
6. The generated app previews successfully.
7. Verification produces a proof bundle.
8. The user can iterate, export, or deploy.

Anything outside this loop is secondary until the loop works end to end.

## Architecture Decisions

- PostgreSQL is the only system of record. Do not add MongoDB back.
- Use `pgvector` for memory and semantic retrieval when needed.
- Use Redis for queueing, rate limiting, and cache where it materially improves reliability.
- Store large generated artifacts in object storage when they outgrow database rows.
- Resolve workspace, git, and terminal operations from authenticated `project_id` or `job_id`; never trust raw server paths from clients.
- Use real verification as a product feature: compile, preview, test, scan, and record proof.

## Phase 1: Foundation and Safety

Goal: make the project run and test consistently.

- Remove MongoDB references from primary docs and CI.
- Make local startup Postgres-first and explicit.
- Make CI provision PostgreSQL and Redis, set `DATABASE_URL`, and run migrations/tests against the same database family used in production.
- Add a local verification script that checks Node, Python, env, backend import, frontend deps, and core tests.
- Lock supported Node guidance to the declared engine range, currently Node 18-22.
- Record every change in `docs/STATUS.md`.

Acceptance criteria:

- A fresh checkout can follow one documented path to start the app.
- CI no longer advertises or provisions MongoDB.
- Backend import and health checks are reproducible with documented env.

## Phase 2: Execution Surface Hardening

Goal: make powerful features safe enough to expose.

- Require authentication for terminal create, execute, and close.
- Remove client-supplied raw `project_path` and `repo_path` from public terminal/git APIs.
- Resolve all paths from server-owned workspace roots.
- Add authorization checks for IDE, git, terminal, workspace, and deploy operations.
- Replace `shell=True` terminal execution with a constrained command runner or move execution into a sandbox/container.
- Add tests proving tenant isolation across jobs and workspaces.

Acceptance criteria:

- User A cannot read, execute, mutate, or git-operate on User B's workspace.
- Terminal/git APIs reject unauthenticated calls and raw paths.
- Security tests cover these boundaries.

## Phase 3: Golden Build Loop

Goal: make one build journey excellent before expanding feature surface.

- Confirm a fresh job can run from prompt to preview to deploy/export.
- Make plan approval, job stream, proof panel, file explorer, preview, and failure retry use the same job model.
- Reduce prompt size for small-context models and route large generation tasks to long-context models.
- Add a model-routing policy: reasoning/planning to stronger long-context models, cheap/fast code subtasks to smaller models when safe, verification to the most reliable reviewer.
- Make stale/foreign test jobs easy to reset in dev without weakening production access control.

Acceptance criteria:

- One smoke test creates a fresh job, waits for completion, fetches files, and validates preview/deploy artifacts.
- Failed verification creates actionable repair input rather than noisy logs.

## Phase 4: Bring Your Code and Iteration

Goal: make CrucibAI differentiated.

- Make import from paste, ZIP, and Git a first-class path.
- Analyze imported code and produce a change plan rather than replacing everything.
- Let users say "fix this" or "continue" and rerun only the necessary agents.
- Store iteration history, generated diffs, and proof after each iteration.
- Make export/deploy preserve user ownership and portability.

Acceptance criteria:

- A user can import a repo, ask for a feature, preview the result, and inspect the diff.
- Iteration can repair a failed build without starting from scratch.

## Phase 5: Product Focus and Launch Readiness

Goal: ship a product users trust.

- Keep visible navigation focused on Dashboard, Workspace, Projects, Deploy, Settings, and Agents.
- Mark unfinished modules as beta or hide them until real data and flows are wired.
- Add production monitoring, alerting, deploy status, and rollback instructions.
- Make security audit failures block launch builds once the transition period is over.
- Recruit beta users and measure successful build-to-preview and build-to-deploy rates.

Acceptance criteria:

- Beta users can complete the golden path without internal help.
- The team has dashboards for API health, job failures, LLM failures, deploy failures, and cost.

## Tracking Rules

- `docs/STATUS.md` records the current state, active branch, completed work, blockers, and next actions.
- `docs/DECISIONS/` stores architecture decision records.
- `test_reports/` stores generated proof and verification outputs.
- Commits should be small and reviewable.
- Work lands on `codex/*` branches before merge to `main`.
