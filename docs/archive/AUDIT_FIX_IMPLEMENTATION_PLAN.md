# Audit Fix — Implementation Plan (100% Green)

**Status:** IMPLEMENTED — All phases A–H complete.  
**Source:** `APP_AUDIT_GAPS_AND_PERFORMANCE.md`

---

## Phase A — MongoDB Indexes

**Goal:** Ensure collections used in hot paths have indexes so queries stay fast at scale.

| Step | Action |
|------|--------|
| A.1 | Add a startup routine (or dedicated module `backend/db_indexes.py`) that creates indexes on: `users` (id unique, email unique, created_at), `projects` (user_id, id unique, created_at, status), `token_ledger` (user_id, created_at, type), `agent_runs` (agent_id, triggered_at), `agent_status` (project_id), `workspace_env` (user_id unique), `project_logs` (project_id, created_at). |
| A.2 | Call index creation from `server.py` on app startup (e.g. in `@app.on_event("startup")` or a lifespan handler), catching and logging errors so missing perms don’t crash the app. |

**Done when:** Server starts and indexes exist (or are created); no behavior change beyond performance.

---

## Phase B — Cap Large / Unbounded List Fetches

**Goal:** No unbounded `to_list(None)`; all list queries use explicit caps; revenue/aggregations stay bounded.

| Step | Action |
|------|--------|
| B.1 | In `server.py`: Define constants for max list sizes (e.g. `MAX_PROJECTS_LIST = 500`, `MAX_TOKEN_LEDGER_REVENUE = 5000`, `MAX_EXPORTS_LIST = 200`). Replace hardcoded `to_list(1000)` / `to_list(5000)` with these constants. |
| B.2 | In `query_optimizer.py`: If the example/demo uses `to_list(None)`, change to `to_list(1000)` or remove/comment that example so production code never uses unbounded fetch. |
| B.3 | Ensure dashboard/stats and admin revenue paths use the same caps (no new unbounded queries). |

**Done when:** All `to_list` calls use a bounded limit; no `to_list(None)` in active code paths.

---

## Phase C — Non-Blocking Subprocess in Server

**Goal:** Subprocess calls in async routes do not block the event loop.

| Step | Action |
|------|--------|
| C.1 | In `server.py`: Wrap `subprocess.run` in settings/capabilities (Docker check), dependency-audit (`npm audit`, `pip_audit`) in `asyncio.to_thread(...)` or `loop.run_in_executor(ThreadPoolExecutor(), ...)` so they run off the main loop. |
| C.2 | Keep timeouts and error handling as-is; only change execution to thread pool. |

**Done when:** Docker check and npm/pip audit run in a thread; server stays responsive during those requests.

---

## Phase D — Frontend Error Feedback (No Silent Catch)

**Goal:** Every critical `axios` call that currently uses `.catch(() => {})` logs the error and, where appropriate, shows user feedback.

| Step | Action |
|------|--------|
| D.1 | Add a small shared helper, e.g. `frontend/src/utils/apiError.js`: `logApiError(context, err)` that does `console.error(context, err?.response?.data || err)` and optionally sets a global “last error” for UI (or use existing toast/notification if present). |
| D.2 | Replace empty `.catch(() => {})` in Workspace.jsx, Settings.jsx, AgentsPage.jsx, PromptsPublic.jsx, PromptLibrary.jsx, Pricing.jsx, PatternsPublic.jsx, TemplatesPublic.jsx with `.catch((e) => logApiError('...', e))`. For key user actions (save, delete, build), optionally show a short message (e.g. “Request failed. Try again.”) via state or toast. |

**Done when:** No silent catch on API calls; console has context for failures; critical flows show user-visible error where appropriate.

---

## Phase E — Documentation (SOURCE_BIBLE)

**Goal:** OPEN table reflects current state; no false “missing” or “not integrated” items.

| Step | Action |
|------|--------|
| E.1 | In `docs/CRUCIBAI_SOURCE_BIBLE.md`: Mark “`/api/tasks` route missing” as **FIXED** (routes exist). Mark “VibeCoding not integrated”, “AdvancedIDEUX not integrated”, “ManusComputer partially wired” as **FIXED** (integrated/wired). Mark “WebSocket reconnection” as **FIXED** (Workspace has backoff). Optionally add a short note that “Multi-file parsing” and “Quality gate sometimes returns 0” remain to be verified in usage. |

**Done when:** OPEN table and related text are accurate and up to date.

---

## Phase F — Free-Tier Landing Enforcement on Project Create

**Goal:** Free users without a paid purchase can only create landing-type projects (align with `/build/plan`).

| Step | Action |
|------|--------|
| F.1 | In `server.py` in `POST /projects`: After credit check, if `plan == "free"` and no paid purchase in `token_ledger`, require project_type or requirements to indicate “landing” (e.g. `project_type == "landing"` or a flag in requirements). If not, return 402 with message: “Free tier is for landing pages only. Upgrade or buy credits to create full apps.” |
| F.2 | Ensure frontend can send `project_type: "landing"` when user selects landing; no change required if it already does. |

**Done when:** Free users without paid purchase cannot create non-landing projects via API.

---

## Phase G — Input Length Limits

**Goal:** Prevent abuse and token blow-up via oversized prompt/requirements.

| Step | Action |
|------|--------|
| G.1 | In `server.py`: For `BuildPlanRequest.prompt`, add Pydantic `Field(..., max_length=50000)` or validator. For project create, cap `data.requirements` / `data.description` total size (e.g. max 50k chars) and reject with 400 if exceeded. |
| G.2 | Document limits in API docs or CONTRIBUTING if needed. |

**Done when:** Prompt and project requirements have enforced max length; 400 returned when exceeded.

---

## Phase H — Health Endpoint Optional Dependency Check

**Goal:** `/api/health` can optionally report MongoDB (and optionally other deps) status for ops.

| Step | Action |
|------|--------|
| H.1 | In `server.py`: Add optional query param or env, e.g. `?deps=1` or `HEALTH_CHECK_DEPS=1`. When set, run a quick `db.command("ping")` (or list_collections limit 1). If ping fails, return 503 with `{"status": "degraded", "mongodb": "unavailable"}`; else keep current 200 and add `"mongodb": "ok"` to body. |
| H.2 | Default remains current behavior (no DB ping) so existing health checks don’t change. |

**Done when:** Health can optionally check MongoDB and return 503 when DB is down.

---

## Implementation Order

1. **A** — MongoDB indexes (foundation for performance).  
2. **B** — Cap list fetches (quick, low risk).  
3. **C** — Subprocess in executor (server only, contained).  
4. **G** — Input length limits (security/abuse).  
5. **F** — Landing enforcement on POST /projects (product rule).  
6. **H** — Health deps (ops).  
7. **D** — Frontend error feedback (UX).  
8. **E** — Documentation (no runtime impact).  

---

## Definition of “100% Green”

- All phases A–H implemented as above.  
- No new linter errors; existing tests still pass.  
- Audit doc `APP_AUDIT_GAPS_AND_PERFORMANCE.md` updated so the summary table shows “Done” or “Fixed” for each addressed item.  

---

**Approved to proceed.** Implementing in the order above until 100% green.
