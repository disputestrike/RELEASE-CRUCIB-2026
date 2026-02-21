# CrucibAI Source Bible — What Was Missing & How to Fix / Get Everything

**Purpose:** If the Source of Truth / Engine Room doc (or an export like CRUCIBAI_SOURCE_BIBLE_V2.pdf) missed anything, this file lists **everything missing**, the **fix** for each, and **how to get the full picture**.

**Last updated:** February 2026

---

## Part A: Everything That Was Missing (Full List)

### 1. **Backend routes not documented in the main doc**

The Engine Room doc summarized routes but omitted many. Full list of **all** API routes with method and purpose:

| Method | Path | Purpose | Frontend caller (if any) |
|--------|------|--------|---------------------------|
| GET | /api/health | Health check | Layout.jsx |
| GET | /api/ | Root | — |
| POST | /api/errors/log | Client error logging | ErrorBoundary |
| GET | /api/dashboard/stats | Dashboard stats | Dashboard.jsx |
| GET | /api/projects/{id}/workspace/files | List workspace files | Workspace.jsx |
| GET | /api/projects/{id}/workspace/file | Get one file (query: path) | Workspace.jsx |
| GET | /api/projects/{id}/dependency-audit | Run dependency audit | — |
| GET | /api/projects/{id}/deploy/files | Files for deploy | Workspace.jsx |
| GET | /api/projects/{id}/export/deploy | Export for deploy | — |
| GET | /api/projects/{id}/preview-token | Preview token | — |
| GET | /api/projects/{id}/preview | Preview root | — |
| GET | /api/projects/{id}/preview/{path} | Preview path | — |
| POST | /api/projects/{id}/duplicate | Duplicate project | — |
| POST | /api/share/create | Create share link | — |
| GET | /api/share/{token} | Get shared project | ShareView.jsx |
| GET | /api/templates | List templates | TemplatesGallery, TemplatesPublic |
| POST | /api/projects/from-template | Create project from template | TemplatesGallery.jsx |
| POST | /api/projects/{id}/save-as-template | Save as template | — |
| GET | /api/settings/capabilities | User capabilities | Settings.jsx |
| GET | /api/users/me/deploy-tokens | Get deploy tokens | Settings.jsx |
| PATCH | /api/users/me/deploy-tokens | Update deploy tokens | Settings.jsx |
| GET | /api/agents/activity | Recent agent activity | Workspace.jsx |
| GET | /api/agents/{id} | Get agent | — |
| PATCH | /api/agents/{id} | Update agent | — |
| DELETE | /api/agents/{id} | Delete agent | — |
| GET | /api/agents/{id}/runs | List runs | — |
| GET | /api/agents/runs/{run_id} | Get run | — |
| GET | /api/agents/runs/{run_id}/logs | Run logs | — |
| POST | /api/agents/{id}/run | Trigger run | — |
| POST | /api/agents/from-template | Create from template | — |
| POST | /api/agents/runs/{run_id}/approve | Approve step | — |
| POST | /api/agents/runs/{run_id}/reject | Reject step | — |
| POST | /api/build/from-reference | Build from reference | — |
| POST | /api/ai/quality-gate | Quality gate check | Workspace.jsx |
| POST | /api/ai/explain-error | Explain error | Workspace.jsx |
| POST | /api/ai/suggest-next | Suggest next step | Workspace.jsx |
| POST | /api/ai/inject-stripe | Inject Stripe into project | PaymentsWizard.jsx |
| POST | /api/ai/generate-readme | Generate README | — |
| POST | /api/ai/generate-docs | Generate docs | — |
| POST | /api/ai/generate-faq-schema | FAQ schema | — |
| POST | /api/ai/design-from-url | Design from URL | Workspace.jsx |
| POST | /api/ai/optimize | Optimize code | Workspace.jsx |
| POST | /api/ai/accessibility-check | Accessibility check | Workspace.jsx |
| GET | /api/prompts/templates | Prompt templates | PromptLibrary, PromptsPublic |
| GET | /api/prompts/recent | Recent prompts | PromptLibrary.jsx |
| POST | /api/prompts/save | Save prompt | PromptLibrary.jsx |
| GET | /api/prompts/saved | Saved prompts | PromptLibrary.jsx |
| POST | /api/exports | Create export | ExportCenter.jsx |
| GET | /api/exports | List exports | ExportCenter.jsx |
| GET | /api/brand | Brand info | — |
| GET | /api/admin/analytics/overview | Analytics overview | — |
| GET | /api/admin/analytics/daily | Daily analytics | — |
| GET | /api/admin/analytics/weekly | Weekly analytics | — |
| GET | /api/admin/analytics/report | Analytics report | — |
| GET | /api/admin/users/{id}/export | Export user data | — |
| POST | /api/admin/users/{id}/grant-credits | Grant credits | — |
| POST | /api/admin/users/{id}/suspend | Suspend user | — |
| POST | /api/admin/users/{id}/downgrade | Downgrade user | — |
| GET | /api/admin/billing/transactions | Billing transactions | — |
| GET | /api/admin/fraud/flags | Fraud flags | — |
| GET | /api/admin/legal/blocked-requests | Blocked requests | — |
| POST | /api/admin/legal/review/{id} | Review request | — |
| GET | /api/admin/referrals/links | Referral links | — |
| GET | /api/admin/referrals/leaderboard | Leaderboard | — |
| GET | /api/admin/segments | Segments (×2) | — |
| POST | /api/tools/browser | Tool: browser | — |
| POST | /api/tools/file | Tool: file | — |
| POST | /api/tools/api | Tool: API | — |
| POST | /api/tools/database | Tool: database | — |
| POST | /api/tools/deploy | Tool: deploy | — |

(Plus all routes already listed in the Engine Room doc: auth, MFA, projects, build, agents/run/*, workspace/env, tokens, stripe, audit, enterprise, generate/doc|slides|sheets, rag/query, search, voice/transcribe, files/analyze, export/zip|github|deploy, etc.)

---

### 2. **Project state schema (state.json keys)**

Missing from the doc: the full list of keys in `workspace/<project_id>/state.json`. **Fix:** Add to Section 5 or 11 of the Source Bible.

**Full state keys** (from `backend/project_state.py`):

- `plan`, `requirements`, `stack`, `decisions`, `design_spec`, `brand_spec`, `memory_summary`, `artifacts`, `test_results`, `deploy_result`, `security_report`, `ux_report`, `performance_report`, `tool_log`, `images`, `videos`, `vibe_spec`, `voice_requirements`, `aesthetic_report`, `team_preferences`, `feedback_log`, `mood`, `accessibility_vibe`, `performance_vibe`, `creative_ideas`, `design_iterations`, `code_review_report`, `bundle_report`, `lighthouse_report`, `dependency_audit`, `scrape_urls`, `native_config`, `store_prep`

**How to get it:** Read `backend/project_state.py` → `DEFAULT_STATE`.

---

### 3. **120 agent names by phase**

The doc said "120 agents" but did not list each name. **Fix:** Add a subsection "120 agent names (from agent_dag.py)" with the full list.

**How to get it:** Run in repo: `python -c "from backend.agent_dag import AGENT_DAG; print('\n'.join(AGENT_DAG.keys()))"` or read `backend/agent_dag.py` and copy the keys of `AGENT_DAG`. Phases come from `get_execution_phases()` in the same file.

---

### 4. **Frontend–backend API call bugs (double /api)**

**Missing:** The doc did not note incorrect frontend API URLs.

**Bug:** In `frontend/src/components/Layout.jsx` and `frontend/src/pages/Workspace.jsx`, some calls use `${API}/api/projects` and `${API}/api/tasks`. Since `API` is already `${BACKEND_URL}/api`, this becomes `/api/api/projects` and `/api/api/tasks`, which are wrong.

**Fix:**

- In **Layout.jsx**: Change `axios.get(\`${API}/api/projects\", ...)` to `axios.get(\`${API}/projects\", ...)` and `axios.get(\`${API}/api/tasks\", ...)` to `axios.get(\`${API}/tasks\", ...)` (only if backend has GET `/api/tasks`; see below).
- In **Workspace.jsx**: Change `axios.post(\`${API}/api/tasks\", ...)` to `axios.post(\`${API}/tasks\", ...)` (only if backend has POST `/api/tasks`).

**Backend gap:** There is no GET `/api/projects` under a path that would be hit as `/api/api/projects` — the real route is GET `/api/projects`. So the bug is only the duplicate `api` in the URL. There is **no** GET `/api/tasks` or POST `/api/tasks` in `server.py`; if the UI expects them, either add those routes or remove/change the frontend calls so they don’t 404.

---

### 5. **Environment variables (required and optional)**

**Missing:** A single list of env vars for backend, frontend, and workers.

**Fix:** Add a "Required environment variables" section.

**Backend (server):** `MONGO_URL`, `DB_NAME`, `JWT_SECRET`; optional: `CORS_ORIGINS`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY` or `SENDGRID_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `USE_TOKEN_OPTIMIZED_PROMPTS`, etc.

**Frontend:** `REACT_APP_BACKEND_URL` (default `http://localhost:8000`).

**How to get it:** Grep `os.environ.get` / `os.environ[...]` in `backend/server.py`, `backend/automation/executor.py`, and `frontend` for any `REACT_APP_*`.

---

### 6. **MongoDB collections**

**Missing:** Explicit list of collections used.

**Fix:** Add a short "Data model" subsection: list collections (e.g. `projects`, `users`, `agents`, `project_logs`, `agent_status`, `shares`, `api_keys`, etc.). **How to get it:** Grep `db["..."]` or `db.<collection>` in `backend/server.py` and other backend files.

---

### 7. **Workspace file write flow**

**Missing:** Exact flow for writing files: which endpoints or internal APIs write to `workspace/<project_id>/`. **Fix:** State that writes go through `execute_tool(project_id, "file", { action: "write", path, content })` and/or project workspace routes (if any), and that there is no single "POST /api/projects/{id}/workspace/file" documented in the route list — clarify if file writes are only internal via tools.

---

### 8. **VibeCoding and AdvancedIDEUX**

**Missing:** No mention of `VibeCoding.jsx` (voice + `/api/ai/analyze`) and `AdvancedIDEUX.jsx`. **Fix:** In the "Full feature list" or "Where in the app", add: VibeCoding (voice transcribe, analyze) and AdvancedIDEUX (if it’s a distinct UX mode or component). **How to get it:** Grep for their imports and usage in `frontend/src`.

---

### 9. **Builder vs Workspace vs ProjectBuilder**

**Missing:** Clear distinction. **Fix:** One-line each: **Builder** = alternate build UI (uses `/api/ai/chat`); **Workspace** = main editor + build + tools (uses `/api/build/plan`, workspace files, AI, voice, etc.); **ProjectBuilder** = create new project (POST `/api/projects`). Add to "Where in the app".

---

### 10. **GenerateContent and generate endpoints**

**Missing:** GenerateContent page and `/api/generate/doc`, `/api/generate/slides`, `/api/generate/sheets`. **Fix:** In feature table and route list: GenerateContent.jsx calls `${API}/generate/${activeTab}` (doc, slides, sheets). Add to Section 2 and Section 4.

---

### 11. **Referrals**

**Missing:** Referrals are in the route list but not in the feature table. **Fix:** Add a row: Referrals (code, stats) — `/api/referrals/code`, `/api/referrals/stats` — TokenCenter (and any other UI that shows referral code/stats).

---

### 12. **IDE extensions**

**Missing:** No mention of `ide-extensions/` (vscode, jetbrains, sublime, vim). **Fix:** Add to directory structure and one line: "IDE extensions for CrucibAI (VSCode/Cursor, JetBrains, Sublime, Vim) — see ide-extensions/."

---

### 13. **Design system**

**Missing:** DESIGN_SYSTEM_MANUS_INSPIRED.md and how it affects UI. **Fix:** In "Incorporated documents" add DESIGN_SYSTEM_MANUS_INSPIRED.md; optionally one sentence on design system (Manus-inspired, components, tokens).

---

### 14. **Single source of truth test and frontend stores**

**Missing:** MASTER_SINGLE_SOURCE_OF_TRUTH_TEST.md, `frontend/src/stores/useLayoutStore.js`, `useTaskStore.js`, and E2E `single-source-of-truth.spec.js`. **Fix:** Add to "Tests & CI" and "Directory structure": single-source-of-truth test doc; frontend stores (Layout, Task); E2E spec. **How to get it:** List `frontend/src/stores/`, `frontend/e2e/*.spec.js`, and root `*SINGLE_SOURCE*`.

---

### 15. **Compliance matrix**

**Missing:** Doc references "compliance matrix green" but doesn’t link or summarize. **Fix:** Add file path or short summary (e.g. "Compliance matrix: all routes have frontend or proof; see RATE_RANK_COMPARE.md or compliance audit doc").

---

### 16. **Deploy flow (Vercel/Netlify) exact endpoints**

**Missing:** Exact paths. **Fix:** Already partially present; ensure doc has: POST `/api/projects/{project_id}/deploy/vercel`, POST `/api/projects/{project_id}/deploy/netlify`, GET `/api/projects/{project_id}/deploy/zip`, GET `/api/projects/{project_id}/export/deploy`.

---

### 17. **Error handling and ErrorBoundary**

**Missing:** Where client errors are sent (POST `/api/errors/log`). **Fix:** One line in Developer Notes or Data Flow: "ErrorBoundary logs errors to POST /api/errors/log."

---

### 18. **How to get “everything” into one doc (process)**

**Missing:** Step-by-step to produce a single, complete bible. **Fix:** See **Part B** below.

---

## Part B: How to Get Everything (Process)

1. **Regenerate from the Master Prompt**
   - Open **MASTER_SOURCE_OF_TRUTH_PROMPT.md**.
   - Copy the full prompt (the block under "The Prompt (copy below)").
   - Run it in an environment that has access to the full repo and all docs (e.g. Cursor with repo context, or a script that reads all .md and key .py/.jsx).
   - Save the output as **docs/CRUCIBAI_SOURCE_OF_TRUTH_ENGINE_ROOM.md** (or your main bible path).

2. **Merge in this file**
   - Open **docs/CRUCIBAI_SOURCE_BIBLE_WHAT_WAS_MISSING_AND_FIXES.md** (this file).
   - For each "Fix" above, either paste the missing content into the main doc (in the right section) or add a short "See WHAT_WAS_MISSING_AND_FIXES" note and keep the detail here.

3. **Apply code fixes**
   - Fix double `/api` in **Layout.jsx** and **Workspace.jsx** (Section A.4).
   - Add backend GET/POST `/api/tasks` if the product is supposed to have a tasks API; otherwise remove or replace the frontend calls.

4. **Append or expand in the main doc**
   - **State keys:** Add the list from Section A.2 to Section 5 or 11.
   - **120 agent names:** Add the list from `agent_dag.py` (Section A.3).
   - **Env vars:** Add Section A.5 as a new subsection under Developer Notes or Engine Room.
   - **Routes:** Use the full route table in Section A.1 to replace or expand the backend route summary in Section 4.
   - **Features:** Add rows for Referrals, GenerateContent, VibeCoding, Builder vs Workspace (Section A.8, A.9, A.10, A.11).
   - **IDE extensions, design system, single-source-of-truth test, compliance matrix:** Add the lines from A.12–A.15.

5. **Export to PDF**
   - From the updated **docs/CRUCIBAI_SOURCE_OF_TRUTH_ENGINE_ROOM.md**, export to PDF (e.g. Cursor/VS Code export, or Pandoc: `pandoc docs/CRUCIBAI_SOURCE_OF_TRUTH_ENGINE_ROOM.md -o CRUCIBAI_SOURCE_BIBLE_V2.pdf`). That way the PDF is generated from the single markdown source and won’t miss sections that were added to the .md.

6. **Verify**
   - Grep for key route paths in `frontend/src` and `backend/server.py` and confirm the doc matches.
   - Run backend and frontend tests; run security_audit; run CI. Note any failures in "Corrections & Gaps."

---

## Part C: One-Page Checklist (Did the doc miss…?)

- [ ] Every backend route (method + path + one-line purpose)?
- [ ] Every frontend route (path + component + protection)?
- [ ] Full project state schema (state.json keys)?
- [ ] 120 agent names (and optionally phase)?
- [ ] Frontend→backend API map (which page calls which endpoint)?
- [ ] Double-/api bug and /api/tasks existence?
- [ ] Env vars (backend + frontend)?
- [ ] MongoDB collections?
- [ ] VibeCoding, AdvancedIDEUX, Builder vs Workspace?
- [ ] GenerateContent, Referrals, Share create?
- [ ] Admin sub-routes (analytics, legal, referrals, segments)?
- [ ] AI sub-routes (quality-gate, explain-error, suggest-next, inject-stripe, optimize, accessibility-check, design-from-url)?
- [ ] Tools routes (/api/tools/*)?
- [ ] IDE extensions, design system, single-source-of-truth test?
- [ ] How to regenerate the bible and export to PDF?

If any box is unchecked, add the missing content using **Part A** and **Part B** above.

---

**End of What Was Missing & Fixes.**

Use this file together with **docs/CRUCIBAI_SOURCE_OF_TRUTH_ENGINE_ROOM.md** and **MASTER_SOURCE_OF_TRUTH_PROMPT.md** to get a complete, up-to-date source bible and PDF.
