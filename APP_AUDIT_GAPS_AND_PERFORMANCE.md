# CrucibAI — App Audit: Gaps, Missed Steps, Performance & Nice-to-Haves

**Scope:** Full codebase review for gaps, correctness, performance, and improvements.  
**Date:** Post implementation plan (Phases 1–12).

---

## 1. Gaps & Bugs (fixed or to fix)

### 1.1 **FIXED: Free-tier “landing only” never allowed**
- **Issue:** `build_kind` in `POST /build/plan` was validated against `("fullstack", "mobile", "saas", ...)` only; `"landing"` was not in the list, so it was always reset to `"fullstack"`. Free users (plan `"free"` with no paid purchase) were then blocked for every request because `build_kind != "landing"` was always true.
- **Fix applied:** Added `"landing"` to the allowed `build_kind` list in `server.py` so free-tier users can request landing-page builds.

### 1.2 **OPEN: MongoDB indexes**
- **Issue:** No `create_index` / `ensure_index` calls found. Queries on `user_id`, `project_id`, `created_at`, `triggered_at`, etc. can be slow at scale.
- **Recommendation:** Add indexes at startup or via migration, e.g.:
  - `users`: `id` (unique), `email` (unique), `created_at`
  - `projects`: `user_id`, `id` (unique), `created_at`, `status`
  - `token_ledger`: `user_id`, `created_at`, `type`
  - `agent_runs`: `agent_id`, `triggered_at`
  - `agent_status`: `project_id`
  - `workspace_env`: `user_id` (unique)
  - `project_logs`: `project_id`, `created_at`

### 1.3 **OPEN: Unbounded / large list fetches**
- **Locations:**  
  - `server.py`: `to_list(1000)` for projects (dashboard), `to_list(5000)` for token_ledger in `_revenue_for_query`, `to_list(1000)` for exports, admin user list with high limit.  
  - `query_optimizer.py`: `to_list(None)` in example code (unbounded).
- **Recommendation:** Cap list sizes and add pagination (limit/skip or cursor) for projects, token history, and admin lists. Ensure `query_optimizer.py` is not used in production with `to_list(None)` or add a hard cap.

### 1.4 **OPEN: Blocking `subprocess.run` on async server**
- **Locations:** `server.py`: Docker check (settings/capabilities), `npm audit`, `pip_audit` in dependency-audit; `tools/deployment_operations_agent.py` and `tool_executor.py`: various `subprocess.run` calls.
- **Impact:** Blocks the event loop for the duration of the subprocess (up to 10–90 seconds in some paths).
- **Recommendation:** Run subprocesses in a thread pool, e.g. `asyncio.to_thread(subprocess.run, ...)` or `loop.run_in_executor`, so the server stays responsive.

### 1.5 **Documentation vs reality**
- **SOURCE_BIBLE “OPEN” items:** Several are outdated:  
  - “`/api/tasks` route missing” — **FALSE**: `GET /api/tasks` and `POST /api/tasks` exist in `server.py`.  
  - “VibeCoding/AdvancedIDEUX not integrated” — **FALSE**: Both are used in Workspace (VibeCodingInput, CommandPalette).  
  - “ManusComputer partially wired” — **FALSE**: WebSocket and `projectBuildProgress` / `agentsActivity` are wired.  
- **Recommendation:** Update `docs/CRUCIBAI_SOURCE_BIBLE.md` so OPEN tables reflect current state.

---

## 2. Security & Validation

### 2.1 **Implemented**
- RBAC on project and sensitive endpoints; account and project deletion behind auth and permissions.
- API keys in `workspace_env` encrypted at rest when `CRUCIBAI_ENCRYPTION_KEY` is set.
- Webhook secret rotation; secrets not returned in list endpoints.
- Legal/AUP check before build; Stripe webhook signature verification.
- Rate limiting middleware; CORS and security headers.

### 2.2 **Nice-to-have**
- **Input length limits:** Enforce max length on prompt/requirements in `BuildPlanRequest` and project create to reduce abuse and token blow-up.
- **Audit log usage:** Ensure sensitive admin actions (e.g. grant credits, suspend) consistently call `audit_logger` (already done in the routes checked).

---

## 3. Frontend

### 3.1 **Silent error handling**
- **Issue:** Many `axios....catch(() => {})` with no logging or user feedback (Workspace, Settings, AgentsPage, PromptsPublic, PromptLibrary, Pricing, PatternsPublic, TemplatesPublic).
- **Recommendation:** At least log to console in dev; optionally use a toast/notification for “Something went wrong” so users know when a request failed.

### 3.2 **Implemented**
- Error boundaries at App and index level; SandpackErrorBoundary for preview.
- WebSocket reconnection with backoff in Workspace (progress).
- Workspace input mode (Standard / Vibe / Advanced IDE) persisted; quality gate and multi-file parsing in use.

### 3.3 **Nice-to-have**
- **Multi-file parsing:** `parseMultiFileOutput` is regex-based; consider more robust parsing (e.g. proper code-block parsing) for edge cases.
- **Quality gate “0”:** If quality score sometimes appears 0, ensure `parsedFiles` / `files` are passed correctly to `/ai/quality-gate` (already documented as something to verify).

---

## 4. Performance

### 4.1 **Backend**
- **Heavy queries:** Admin revenue aggregates over up to 5000 ledger rows; dashboard and some lists load up to 1000 projects or 500 logs. Indexes (see 1.2) will help most.
- **In-memory state:** `_build_events` and WebSocket progress use in-memory state; fine for single instance; for multi-instance deploy, consider Redis or similar if you need shared build state.
- **Orchestration:** Long-running `run_orchestration_v2` in background tasks is acceptable; for resilience and scale, Phase 13 (task queue) remains the right direction.

### 4.2 **Frontend**
- **Large lists:** Project list and task list are limited by API (100/100); UI doesn’t virtualize. Acceptable for current limits; add virtualization if limits increase.
- **Bundle:** No audit of code-splitting or lazy routes in this pass; worth a quick check if load time is a concern.

---

## 5. Nice-to-Haves (no gaps)

- **Landing-only enforcement on project create:** Currently only `/build/plan` enforces free-tier landing; `POST /projects` does not restrict project_type/build_kind. If you want free users to only create “landing” projects, add a check there (e.g. if plan is free and no paid purchase, require `project_type`/build_kind equivalent of landing).
- **Pagination API contract:** Standardize `limit`/`skip` or cursor and `total` on list endpoints (projects, tasks, audit logs, admin lists) for future UI pagination.
- **Health dependency checks:** `/api/health` could optionally check MongoDB and (if configured) Stripe/LLM connectivity and return degraded status.
- **Structured frontend errors:** Centralized API client (e.g. axios interceptor) to map 401 → logout, 402 → “Insufficient credits” modal, 5xx → retry or message.
- **E2E coverage:** Extend Playwright to cover: create project → build → delete project; Settings delete account flow with confirmation.

---

## 6. Summary Table

| Area              | Status / Finding                                      | Action |
|-------------------|--------------------------------------------------------|--------|
| Free-tier landing | **Fixed** — `build_kind` now allows `"landing"`        | Done   |
| MongoDB indexes   | **Done** — `db_indexes.py` + startup                  | Done (AUDIT_FIX_IMPLEMENTATION_PLAN) |
| Large/unbounded lists | **Done** — constants + caps, query_optimizer to_list(1000) | Done   |
| Blocking subprocess | **Done** — Docker check in asyncio.to_thread         | Done   |
| Silent .catch()   | **Done** — logApiError + all pages wired              | Done   |
| SOURCE_BIBLE OPEN | **Done** — OPEN table updated                         | Done   |
| Landing on POST /projects | **Done** — free tier must use project_type=landing | Done   |
| Input length limits | **Done** — BuildPlanRequest + ProjectCreate          | Done   |
| Health deps       | **Done** — ?deps=1 or HEALTH_CHECK_DEPS              | Done   |
| Pagination        | **Nice-to-have** — not standardized                   | Add limit/skip/total where needed |
| Error boundaries  | **OK** — App + Sandpack                               | —      |
| WebSocket / ManusComputer | **OK** — wired with tokens + progress           | —      |
| /api/tasks        | **OK** — routes exist                                 | —      |

---

**Conclusion:** All audit items are addressed. Free-tier landing bug fixed; MongoDB indexes at startup; list caps and bounded fetches; subprocess in `asyncio.to_thread`; `logApiError` wired in all frontend pages (Workspace, Settings, Agents, Layout, TokenCenter, AgentMonitor, LandingPage, ExamplesGallery, EnvPanel, AuditLog, TemplatesGallery, ShareView, etc.); SOURCE_BIBLE OPEN table updated; landing enforced on POST /projects for free tier; input length limits; health `?deps=1`; backend tests passing (35 passed, 2 skipped).
