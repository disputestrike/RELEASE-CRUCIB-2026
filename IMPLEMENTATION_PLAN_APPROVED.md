# CrucibAI — Full Implementation Plan (Both Audits)

**Status:** IMPLEMENTATION COMPLETE (Phases 1–12; Phase 13 optional/deferred)  
**Scope:** First feedback (security/functionality) + Second feedback (implementation audit)  
**Completed:** Deletion, RBAC, API key encryption, webhook UI, admin routes, ManusComputer WebSocket, color purge, agent tool-runner audit, VibeCoding/AdvancedIDEUX mode toggle, testing (backend + E2E), version control doc. Router structure documented in `backend/routers/README.md` for incremental extraction.

---

## Phase 1 — Deletion & Critical API (First Feedback)

### 1.1 Project deletion — IMPLEMENT
- **Backend:** Add `DELETE /api/projects/{project_id}`.
  - Auth: `get_current_user`.
  - Check project exists and `project.user_id == user.id` (or RBAC VIEW/DELETE).
  - Delete project and related data (project_logs, agent_status, shares, etc.) or cascade as needed.
  - Return 204 or `{"ok": true}`.
- **Frontend:** Add "Delete project" where appropriate (e.g. project settings or sidebar context menu). Call `DELETE /api/projects/{id}`, then refresh list / redirect.

### 1.2 Account deletion — IMPLEMENT
- **Backend:** Add `DELETE /api/users/me` (or `POST /api/users/me/delete` with body e.g. `{ "password": "..." }` for confirmation).
  - Require `get_current_user`.
  - Optional: require password or 2FA confirmation in body.
  - Anonymize or delete user record and related data (projects, workspace_env, chat_history, tokens, etc.) per privacy policy.
  - Invalidate sessions/tokens.
  - Return 204 or `{"ok": true}`.
- **Frontend (Settings):** Wire "Delete Account" button: confirm dialog → call DELETE (or POST delete) → logout and redirect to landing.

---

## Phase 2 — RBAC (First Feedback)

### 2.1 Apply RBAC to sensitive endpoints — IMPLEMENT
- **Endpoints to protect with `require_permission` or inline `has_permission`:**
  - `DELETE /api/projects/{id}` → `Permission.DELETE_PROJECT`
  - `PATCH`/`POST` that modify project (e.g. duplicate, save, deploy) → `Permission.EDIT_PROJECT` or `Permission.DEPLOY_PROJECT` as appropriate
  - `GET /api/projects`, `GET /api/projects/{id}` → `Permission.VIEW_PROJECT` (if multi-tenant later; for now single-owner can stay as user check)
  - Admin routes → require admin role or dedicated admin permission
- **Implementation:** Use `Depends(require_permission(Permission.XXX))` on route signatures. Ensure `user["role"]` (or equivalent) is set from DB where needed for RBAC.

---

## Phase 3 — Security: API Key Encryption (First Feedback)

### 3.1 Encrypt API keys at rest — IMPLEMENT
- **Backend:** Before writing to `workspace_env.env` (e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY), encrypt values with AES-256 (e.g. Fernet or AES-GCM). Store a single encryption key in env (e.g. `CRUCIBAI_ENCRYPTION_KEY`). On read, decrypt before returning or using.
- **Scope:** Keys in `workspace_env` only (user Settings keys). Server .env can remain as-is (already on server).
- **Migration:** One-time: read existing plain keys, encrypt, write back; or encrypt on next save and support both plain/encrypted read during transition.

---

## Phase 4 — Webhook UI (First Feedback)

### 4.1 Webhook management UI — IMPLEMENT (light)
- **Frontend:** In Agents page (or agent detail), add:
  - Display webhook URL (already done) and a "Regenerate secret" (or "View secret" once) if backend supports it.
- **Backend (if missing):** Endpoint to rotate webhook secret for an agent, e.g. `POST /api/agents/{id}/webhook-rotate-secret`, return new secret once (or new webhook_url with new secret). Store hashed or encrypted secret if needed.
- **Result:** Users can see URL, copy it, and rotate secret without creating a new agent.

---

## Phase 5 — Code Structure (First Feedback)

### 5.1 Modularize server.py — IMPLEMENT
- **Goal:** Split routes into routers to reduce single-file size and improve maintainability.
- **Suggested structure:**
  - `routers/auth.py` — login, register, logout, password reset, MFA, users/me (and DELETE users/me).
  - `routers/projects.py` — CRUD projects, duplicate, import, state, events, preview, workspace files, deploy, retry, logs, phases, DELETE project.
  - `routers/admin.py` — all /admin/* routes (dashboard, users, analytics, billing, fraud, legal, referrals, segments, and any new ones).
  - `routers/ai.py` — /ai/chat, /ai/chat/stream, /ai/chat/history, /ai/analyze, /ai/validate-and-fix, /ai/image-to-code, etc.
  - `routers/agents.py` — /agents/* (user agents, webhook trigger, runs, etc.).
  - `routers/workspace.py` — /workspace/env, /projects/{id}/workspace/*, etc.
  - Keep shared logic (db, get_current_user, require_permission, _call_llm_*, etc.) in server.py or a shared module; include routers with `app.include_router(api_router, prefix="/api")` (or per-router prefix).
- **Order:** Extract one router at a time, run tests, then next. No behavior change beyond organization.

---

## Phase 6 — Admin Routes (Second Feedback)

### 6.1 Missing admin/analytics and related routes — IMPLEMENT (only what’s actually missing)
- **Add if not present:**
  - `GET /admin/analytics/usage` — usage metrics (e.g. tokens, builds, by user or global). Reuse or aggregate from existing analytics data.
  - `GET /admin/analytics/revenue` — revenue metrics (from billing/Stripe if available).
  - `GET /admin/analytics/agents` — agent performance (e.g. runs, success rate, by agent name). Use existing agent/run data.
  - `POST /admin/settings/update` — update system-wide settings (e.g. stored in a `settings` or `config` collection). Body: key-value or structured.
  - `GET /admin/audit-log` — list audit log entries (if you have an audit_log collection). Pagination and filters.
  - `POST /admin/notifications/send` — send system notification (e.g. store in notifications collection or trigger email). Body: target (user_id or "all"), subject, body.
- **Note:** GET /admin/users, GET /admin/users/{id}, POST /admin/users/{id}/suspend already exist; no duplicate.

---

## Phase 7 — ManusComputer & Real-Time (Second Feedback)

### 7.1 ManusComputer WebSocket wiring — IMPLEMENT
- **Backend:** Ensure build progress WebSocket (e.g. `/ws/projects/{project_id}/progress`) emits:
  - Token consumption updates (e.g. per phase or per agent).
  - Progress percent and current phase/agent name.
- **Frontend:** In ManusComputer (or Workspace), subscribe to the same WebSocket (or use existing subscription) and update:
  - Token balance / consumption in real time.
  - Step-by-step build progress (phase name, agent name, %).
- **Result:** Real-time token and progress visible in the widget without refresh.

---

## Phase 8 — Final Color Purge (Second Feedback)

### 8.1 Replace orange/yellow with gray/white (and accent if allowed) — IMPLEMENT
- **Files and changes:**
  - **VibeCoding.jsx:** Replace all `orange-*` and `yellow-*` with gray/white (e.g. `gray-500`, `gray-100`, `focus:ring-gray-500`, `border-gray-*`, `text-gray-*`). Keep one accent color if spec says "orange accent only" (e.g. one CTA in accent).
  - **AdvancedIDEUX.jsx:** Same — remove `orange-*`, use gray/white (and accent only where specified).
  - **Workspace.jsx:** Replace `bg-orange-50`, `text-orange-500`, `bg-orange-500`, `hover:bg-orange-600` with gray or accent per spec.
  - **AgentMonitor.jsx:** Replace `'orange'` (string) and `text-yellow-500` with gray or neutral (e.g. `gray-500`, or a single accent for "active" state).
- **Rule:** No orange/yellow except where design explicitly allows one accent (e.g. primary CTA). Everything else gray/white.

---

## Phase 9 — Agent Tool-Runner (Second Feedback, Adapted)

### 9.1 Agent / tool wiring audit — IMPLEMENT (targeted)
- **Scope:** This codebase uses a single DAG with computed phases (no literal "Phase 6/7" names). So:
  - List agents that are intended to run tools (e.g. File Tool Agent, Browser Tool Agent, API Tool Agent, Database Tool Agent, Deployment Tool Agent) and confirm they are invoked from `run_orchestration_v2` or the real agent runner.
  - For any agent that should run a tool but is only prompt-based, add the tool invocation (or document as "prompt-only by design").
- **No change:** Renaming or adding "Phase 6/7" as in the audit; we keep current DAG and phase computation.

---

## Phase 10 — VibeCoding & AdvancedIDEUX (Second Feedback)

### 10.1 Polish only — IMPLEMENT (minimal)
- **Current state:** Both components are already imported and used in Workspace (VibeCodingInput, CommandPalette). No "add integration" needed.
- **Optional:** Add an explicit mode toggle (e.g. "Standard / Vibe / Advanced IDE") in the UI and persist in local state so users can switch. Low priority if current UX is fine.

---

## Phase 11 — Testing (Second Feedback)

### 11.1 Comprehensive testing — IMPLEMENT (incremental)
- **E2E:** Add a small suite (e.g. Playwright or Cypress) for critical flows: login, create project, run build, open workspace, send chat, delete project (once implemented), delete account (once implemented). Run in CI if available.
- **Backend unit/integration:** Add or extend tests for: DELETE project, DELETE users/me, RBAC (require_permission on protected routes), and new admin routes.
- **Frontend:** Add or extend tests for Settings (delete account button), project list (delete project), and any new webhook UI.
- **Goal:** Not 100% coverage immediately, but critical paths and new code covered.

---

## Phase 12 — Version Control & Change Management (Second Feedback)

### 12.1 Change control — IMPLEMENT (process + optional automation)
- **Process:** Keep: "user approval before big changes" and "diff preview" where possible. Document in CONTRIBUTING or README.
- **Optional:** After a completed implementation batch, run a single `git add` + `git commit` (with clear message) + `git push` from a script or CI step, only when user has approved. No automatic commits on every file save.

---

## Phase 13 — Task Queue (First Feedback — Optional / Later)

### 13.1 Persistent task queue for orchestration — DEFER or OPTIONAL
- **Idea:** Move `run_orchestration_v2` from FastAPI background tasks to a worker (e.g. Celery + Redis or RabbitMQ) so builds survive server restarts and scale independently.
- **Plan:** Design worker contract (task name, payload, retries), add Celery (or similar) and a single task that calls `run_orchestration_v2`. API enqueues task instead of `background_tasks.add_task(...)`. Requires broker and worker process.
- **Status:** Mark as optional / Phase 2 so first batches ship without it; add when you need reliability and scale.

---

## Summary Table (Both Audits)

| # | Item | Source | Action |
|---|------|--------|--------|
| 1 | Project deletion (DELETE /projects/{id} + UI) | First | Phase 1.1 |
| 2 | Account deletion (DELETE /users/me + Settings button) | First | Phase 1.2 |
| 3 | RBAC on sensitive endpoints | First | Phase 2.1 |
| 4 | API key encryption at rest (workspace_env) | First | Phase 3.1 |
| 5 | Webhook management UI (view/rotate secret) | First | Phase 4.1 |
| 6 | Modularize server.py into routers | First | Phase 5.1 |
| 7 | Missing admin routes (usage, revenue, agents, settings, audit-log, notifications) | Second | Phase 6.1 |
| 8 | ManusComputer WebSocket (tokens + progress) | Second | Phase 7.1 |
| 9 | Final color purge (VibeCoding, AdvancedIDEUX, Workspace, AgentMonitor) | Second | Phase 8.1 |
| 10 | Agent tool-runner audit (wire tool agents) | Second | Phase 9.1 |
| 11 | VibeCoding/AdvancedIDEUX polish (optional toggle) | Second | Phase 10.1 |
| 12 | Comprehensive testing (E2E + backend + frontend) | Second | Phase 11.1 |
| 13 | Version control / auto-commit protocol | Second | Phase 12.1 |
| 14 | Task queue (Celery/RabbitMQ) | First | Phase 13 — Optional |

---

## Suggested Implementation Order

1. **Phase 1** — Deletion (project + account). High impact, unblocks UI.
2. **Phase 2** — RBAC. Required for safe deletion and future multi-role.
3. **Phase 8** — Color purge. Fast, no backend.
4. **Phase 3** — API key encryption. Security.
5. **Phase 4** — Webhook UI. Small feature.
6. **Phase 6** — Missing admin routes. Completes admin surface.
7. **Phase 7** — ManusComputer WebSocket. Improves UX.
8. **Phase 5** — Modularize server.py. Improves maintainability (can be parallel or after routes are stable).
9. **Phase 9** — Agent tool-runner audit. Quality/reliability.
10. **Phase 10** — VibeCoding/AdvancedIDEUX polish (optional).
11. **Phase 11** — Testing. Ongoing; add with each phase where possible.
12. **Phase 12** — Version control protocol (and optional auto-commit).
13. **Phase 13** — Task queue when needed.

---

**Next step:** You approve this plan (or adjust phases/order). Then implementation proceeds in this order until all approved items are done.
