# API Routers (Phase 5)

Per `IMPLEMENTATION_PLAN_APPROVED.md`, `server.py` should be split into routers:

- **routers/auth.py** — login, register, logout, MFA, users/me, DELETE users/me
- **routers/projects.py** — CRUD projects, duplicate, import, state, events, deploy, retry, logs, DELETE project
- **routers/admin.py** — all /admin/* routes (dashboard, users, analytics, billing, fraud, legal, referrals, segments, settings, audit-log, notifications)
- **routers/ai.py** — /ai/chat, /ai/analyze, /ai/image-to-code, /ai/validate-and-fix, etc.
- **routers/agents.py** — /agents/* (user agents, webhook, runs, templates)
- **routers/workspace.py** — /workspace/env, /projects/{id}/workspace/*

**Current state:** All routes remain in `server.py`. To extract a router:

1. Create a shared `deps` module (e.g. `backend/deps.py`) with `db`, `get_current_user`, `get_current_admin`, `require_permission`, and any helpers used by the routes. Set these from `server.py` after defining them.
2. Create `routers/<name>.py` with an `APIRouter()` and move the corresponding route handlers, importing shared deps from `deps`.
3. In `server.py`: `from routers.<name> import router; api_router.include_router(router)` (with no extra prefix so routes stay under `/api`).
4. Remove the moved handlers from `server.py` and run tests.

No behavior change beyond organization.
