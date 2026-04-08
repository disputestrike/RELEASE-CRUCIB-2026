# CrucibAI Status

Last updated: 2026-04-08

## Current Branch

`codex/postgres-foundation-and-execution-plan`

## Current Objective

Establish the Postgres-only foundation and execution tracking trail before changing runtime behavior.

## Confirmed Direction

- PostgreSQL is the only primary database.
- MongoDB references in primary docs and CI are treated as drift.
- The golden path is prompt/import to plan, build, proof, preview, iterate, export/deploy.
- Security hardening for terminal/git/workspace operations is required before public launch.
- Work should be committed in small slices on a `codex/*` branch.

## Known Risks

- `backend/server.py` is too large and mixes too many domains.
- Terminal and git endpoints currently expose powerful operations and need stricter authentication/path controls.
- CI still had MongoDB-era configuration before this branch.
- Fresh checkout setup requires dependency and environment bootstrapping.
- The full test suite was not run in this checkout before foundation fixes because frontend dependencies and local database setup were not ready.

## Active Milestone

Phase 1: Foundation and Safety

Tasks:

- [x] Create a dedicated working branch.
- [x] Add execution plan and status tracking docs.
- [x] Update docs to say Postgres-only in primary setup/deploy paths.
- [x] Update CI backend service from MongoDB to PostgreSQL/Redis.
- [x] Add or update local verification workflow.
- [x] Add ADR for workspace execution boundaries.
- [ ] Commit the first foundation slice.

## Next Milestone

Phase 2: Execution Surface Hardening

Planned tasks:

- Require authentication for terminal create/execute/close.
- Remove raw path trust from terminal and git APIs.
- Resolve workspaces server-side from authenticated `project_id` or `job_id`.
- Add tenant-isolation regression tests.
- Decide whether terminal execution is removed, sandboxed, or admin-only for launch.
