# Comprehensive Pre–Soft Launch Audit

**Purpose:** Hidden blockers, endpoint/router/function coverage, line counts, flooders, connectivity, and Facebook-style checklist.  
**Status:** 64 backend tests passing (in-process, no mocks).  
**Generated:** February 2026 (post–test fix).

---

## 1. Code size (today)

| Area | Lines | Notes |
|------|-------|--------|
| **Backend (Python)** | **~4,352** | server.py, agent_dag, agent_resilience, code_quality, orchestration, tests |
| **Frontend (src)** | **~10,108** | App.js, pages, components, ui (JS/JSX only) |
| **Total app code** | **~14,460** | Excludes node_modules, __pycache__, build |

---

## 2. Backend: 88 routes – tested vs untested

### 2.1 Tested by pytest (64 tests, in-process)

| Route | Method | Test file | What’s asserted |
|-------|--------|-----------|-----------------|
| `/` | GET | contract, crucibai, smoke | 200, body.message |
| `/health` | GET | contract, crucibai, smoke | 200, status healthy, timestamp |
| `/auth/register` | POST | crucibai | 200 + token/user, 400 duplicate |
| `/auth/login` | POST | contract (422 invalid body), crucibai | 200 / 401 |
| `/auth/me` | GET | contract (401 no token), crucibai | 200 with token, 401 without |
| `/tokens/bundles` | GET | crucibai, smoke | 200, bundles.starter/pro |
| `/tokens/purchase` | POST | crucibai | 200, new_balance |
| `/tokens/history` | GET | crucibai | 200, history, current_balance |
| `/agents` | GET | crucibai, smoke | 200, agents list, Planner/Frontend/Backend |
| `/patterns` | GET | crucibai, smoke | 200, patterns array |
| `/templates` | GET | smoke | not 500 |
| `/build/phases` | GET | contract, crucibai, smoke | 200, phases array |
| `/dashboard/stats` | GET | crucibai | 200 (auth), total_projects, token_balance, weekly_data |
| `/projects` | GET | crucibai | 200 (auth), projects |
| `/projects` | POST | crucibai | 200 or 402 (auth) |
| `/ai/chat` | POST | crucibai | 200 or 503/500, response/model_used/session_id when 200 |
| `/ai/analyze` | POST | crucibai | 200 or 503/500, result/task when 200 |
| `/ai/validate-and-fix` | POST | crucibai | 200 or 503/500, fixed_code/valid when 200 |
| `/search` | POST | crucibai | 200 or 503/500, query/results when 200 |
| `/voice/transcribe` | POST | contract | 422 no file, 400/503 empty file |
| `/stripe/create-checkout-session` | POST | crucibai | 401/503 no auth, 400/401/403/503 invalid bundle |

**Also:** agent_dag, agent_resilience, code_quality, orchestration_e2e (quality score, failure recovery, DAG, context) – no HTTP.

### 2.2 Not covered by pytest (high‑impact for frontend)

| Route | Method | Used by frontend | Risk if broken |
|-------|--------|-------------------|----------------|
| `/build/plan` | POST | Workspace (plan step) | **High** – core flow |
| `/projects/{project_id}` | GET | AgentMonitor, BuildProgress | **High** |
| `/projects/{project_id}/retry-phase` | POST | AgentMonitor | Medium |
| `/projects/{project_id}/logs` | GET | AgentMonitor | Medium |
| `/projects/{project_id}/phases` | GET | AgentMonitor | Medium |
| `/projects/{project_id}/duplicate` | POST | Dashboard | Low |
| `/projects/{project_id}/save-as-template` | POST | Dashboard | Low |
| `/projects/from-template` | POST | TemplatesGallery | Medium |
| `/examples` | GET | LandingPage, ExamplesGallery | **High** (landing) |
| `/examples/{name}` | GET | ExamplesGallery (detail) | Medium |
| `/examples/{name}/fork` | POST | ExamplesGallery | Medium |
| `/agents/status/{project_id}` | GET | AgentMonitor | **High** |
| `/agents/activity` | GET | Workspace | Low |
| `/ai/chat/history/{session_id}` | GET | Workspace | Medium |
| `/ai/chat/stream` | POST | Workspace (streaming) | Medium |
| `/ai/image-to-code` | POST | Workspace (image upload) | Medium |
| `/voice/transcribe` | POST | Workspace, Landing (real file) | **High** – only 422/400 tested |
| `/export/zip`, `/export/github`, `/export/deploy` | POST | Workspace, ExportCenter | Medium |
| `/exports` | GET/POST | ExportCenter | Low |
| `/workspace/env` | GET/POST | Settings, EnvPanel | Medium |
| `/share/create` | POST | Dashboard | Low |
| `/share/{token}` | GET | ShareView | Medium |
| `/prompts/templates`, `/prompts/recent`, `/prompts/save`, `/prompts/saved` | GET/POST | PromptsPublic, PromptLibrary | Low |
| `/ai/explain-error`, `/ai/suggest-next`, `/ai/optimize`, `/ai/security-scan`, `/ai/accessibility-check`, `/ai/design-from-url`, `/ai/generate-readme`, `/ai/generate-docs`, `/ai/generate-faq-schema`, `/ai/inject-stripe` | POST | Workspace / various | Low–medium |
| `/files/analyze` | POST | Workspace | Low |
| `/rag/query` | POST | (backend only?) | Low |
| `/auth/google`, `/auth/google/callback` | GET | AuthPage (OAuth) | Medium if using Google |
| `/stripe/webhook` | POST | Stripe (server‑to‑server) | High for payments |
| `/agents/run/*` (17 routes) | GET/POST | Orchestration / internal | High for build flow |
| `/build/from-reference` | POST | (reference builds) | Low |
| **WebSocket** `/ws/projects/{project_id}/progress` | WS | BuildProgress, AgentMonitor | **High** – live progress |

---

## 3. Hidden blockers and “flooders”

### 3.1 Blockers (can break critical path)

| Item | Why it’s a blocker | Mitigation |
|------|--------------------|------------|
| **No rate limiting** | Auth and AI endpoints can be hammered; token exhaustion, cost, or DoS. | Add rate limit (e.g. slowapi or nginx) on `/auth/login`, `/auth/register`, `/ai/chat`, `/build/plan` before/at launch. |
| **MongoDB required at startup** | `MONGO_URL` / `DB_NAME` must be set; `seed_examples_if_empty()` runs on startup. | Already in conftest for tests; production must have DB up and env set. |
| **LLM / API keys** | Missing keys → 500/503 on AI routes; tests accept 503/500. | Document required env (OPENAI, ANTHROPIC, etc.); frontend should show “Add API key” or similar. |
| **Stripe webhook** | If Stripe is used, webhook must be reachable and signature verified. | Test with Stripe CLI or manual; no pytest for webhook. |
| **WebSocket** | Progress and AgentMonitor depend on WS; not tested automatically. | Manual click-through: start build, confirm WS updates. |
| **GET /examples** | Landing and ExamplesGallery call it; not in pytest. | Smoke already hits `/api/templates`; add GET `/api/examples` to smoke or a single integration test. |

### 3.2 “Flooders” (abuse / overload risk)

| Risk | Endpoint(s) | Today | Recommendation |
|------|-------------|--------|-----------------|
| Auth brute force | `/auth/login`, `/auth/register` | No rate limit | Rate limit by IP (e.g. 10/min per IP). |
| Token burn / cost | `/ai/chat`, `/build/plan`, `/ai/analyze`, etc. | No global throttle | Per-user token balance already; optional per-IP or per-endpoint cap. |
| File upload abuse | `/voice/transcribe`, `/files/analyze`, `/ai/image-to-code` | Size limits possible but not clearly enforced in one place | Enforce max body size (e.g. 10–50 MB) and timeouts. |
| Webhook spam | `/stripe/webhook` | Signature validation present | Keep; ensure only Stripe IPs or secret check. |

---

## 4. Connectivity and frontend → backend

| Check | Status |
|-------|--------|
| **Base URL** | Frontend uses `REACT_APP_BACKEND_URL` (default `http://localhost:8000`); API prefix `/api`. |
| **CORS** | Backend: `CORSMiddleware`, `allow_origins=CORS_ORIGINS` (default `*`). For production set to frontend origin. |
| **Health in UI** | Layout: `GET /api/health`; shows “Backend connected” or “Backend unavailable”. |
| **WebSocket URL** | BuildProgress / progress: `http` → `ws`, path `/ws/projects/{id}/progress`. |
| **Auth header** | Token in `Authorization: Bearer <token>`; stored in localStorage; sent by axios where needed. |

**Frontend API usage (summary):** App.js (auth/me, login, register); Layout (health); Workspace (build/plan, voice, ai/chat, stream, image-to-code, validate-and-fix, security-scan, accessibility-check, suggest-next, export/*, optimize, explain-error, analyze, files/analyze, design-from-url); ProjectBuilder (POST projects); AgentMonitor (projects/:id, agents/status, logs, phases, retry-phase); BuildProgress (fetch projects/:id); Dashboard (share/create, duplicate, save-as-template, dashboard/stats, projects); TokenCenter (bundles, history, usage, purchase); Settings, EnvPanel (workspace/env); ExamplesGallery (examples, examples/:name/fork); ShareView (share/:token); Templates (templates, projects/from-template); Prompts (prompts/*); Pricing (tokens/bundles); PaymentsWizard (Stripe checkout). All align with backend routes; no dead endpoints in UI.

---

## 5. Click-through and endpoint checklist (manual / E2E)

Recommended manual or E2E pass before soft launch:

| # | Flow | Steps | Endpoints / success |
|---|------|--------|----------------------|
| 1 | **Landing** | Open `/` | GET /api/examples (200), hero and examples section render. |
| 2 | **Register** | /auth → Register | POST /auth/register 200 → token → redirect to /app. |
| 3 | **Login** | /auth → Login | POST /auth/login 200 → GET /auth/me 200. |
| 4 | **Dashboard** | /app (with token) | GET /api/projects, GET /api/dashboard/stats 200; “Backend connected”. |
| 5 | **New project** | /app/projects/new → Create | POST /api/projects 200 or 402 → redirect to /app/projects/:id. |
| 6 | **AgentMonitor** | /app/projects/:id | GET project, agents/status, phases, logs 200; WS connects; retry-phase if offered. |
| 7 | **Workspace plan** | /workspace → prompt → Plan | POST /api/build/plan 200; plan + suggestions. |
| 8 | **Workspace build** | Plan → Start build | POST /api/projects then progress via WS or polling. |
| 9 | **Voice (optional)** | Workspace → mic → transcribe | POST /api/voice/transcribe with file; 200 or 400/503. |
| 10 | **Share** | Dashboard → Share | POST /api/share/create 200; open /share/:token → GET /api/share/:token 200. |
| 11 | **Templates** | /templates or /app/templates | GET /api/templates 200; from-template if applicable. |
| 12 | **Tokens** | /app/tokens | GET bundles, history, usage; POST purchase (if balance allows). |

---

## 6. What would “Facebook” test at this point (pre–soft launch)?

| Category | What they’d do | Current state |
|----------|----------------|----------------|
| **Security** | 401 without token on protected routes; no secrets in frontend bundle; CORS to real origin. | Auth tests cover 401; CORS config exists; ensure no keys in frontend. |
| **Critical path** | E2E: Register → Login → New project → Build (or plan) → Project page. | No automated E2E; manual click-through above. |
| **API correctness** | Key endpoints 200/401/404 (not 500) for known inputs. | 64 tests; many routes covered; 500/503 allowed only for AI when keys missing. |
| **Availability** | Health check; DB down handled. | Health tested; startup depends on MongoDB. |
| **Abuse / flooders** | Rate limit auth and expensive endpoints. | **Not implemented** – add before or at launch. |
| **Privacy / legal** | Privacy + Terms linked; no PII in logs. | Pages exist; verify logging. |
| **Frontend errors** | No blank screen; ErrorBoundary; clear message when backend/keys missing. | Manual check. |
| **Performance** | Health/simple GETs &lt; 2s; plan/build 30–60s acceptable. | Smoke: health &lt; 5s. |
| **WebSocket** | Progress stream works end‑to‑end. | Not in pytest; manual or E2E. |
| **Payments** | Checkout + webhook in test mode. | Stripe 401/503 tested; webhook not. |

---

## 7. Will this work?

- **Backend:** 88 routes; **~22 covered by pytest** (health, root, auth, tokens, agents, patterns, templates smoke, build/phases, dashboard, projects list/create, AI chat/analyze/search/validate-and-fix, voice contract, Stripe checkout). **66 routes not covered** by tests – including build/plan, project by id, retry-phase, logs, phases, examples, share, prompts, workspace/env, export, agents/run/*, WebSocket. So: **core auth and read-only + one write path (projects create) are tested**; full build flow and many write/stream routes rely on manual or future E2E.
- **Frontend:** Routes and API calls match backend; connectivity is correct if `REACT_APP_BACKEND_URL` and CORS are set. One full click-through (register → project → plan or build) validates the critical path.
- **Flooders:** No rate limiting yet; add for auth and heavy AI/build endpoints before or at soft launch.
- **Bottom line:** It can work for soft launch after: (1) **one full click-through** (flows in §5), (2) **adding GET /api/examples** to smoke or one test so landing is covered, (3) **optional but recommended: rate limit** on login/register and optionally on /ai/chat and /build/plan, and (4) ensuring **MongoDB + env (MONGO_URL, DB_NAME, optional LLM keys)** in target environment. For “Facebook-level” depth: add E2E (e.g. Playwright) for critical path and WebSocket, then rate limiting and monitoring.

---

## 8. Recommended actions (priority)

| Priority | Action |
|----------|--------|
| **P0** | **Manual click-through:** All 12 flows in §5 (Landing, Register, Login, Dashboard, New project, AgentMonitor, Workspace plan, Workspace build, Voice optional, Share, Templates, Tokens). |
| **P1** | **Smoke or test:** Add GET `/api/examples` (200 and `examples` in body) so landing is covered. |
| **P1** | **Rate limiting:** Add per-IP (or per-user) limits for `/auth/login`, `/auth/register`; optional for `/ai/chat`, `/build/plan`. |
| **P2** | **E2E (optional):** One Playwright test: open app → login → new project → wait for project page / progress. |
| **P2** | **WebSocket:** Manual or E2E check that `/ws/projects/{id}/progress` connects and receives messages during build. |
| **P3** | **Defer:** Full load test, full a11y audit, more granular rate limits. |

---

## 9. Test run summary (today)

- **64 tests, all passing**, with backend and MongoDB available; no live server needed (in-process AsyncClient + session-scoped event loop).
- **Suites:** test_agent_dag (5), test_agent_resilience (5), test_api_contract (10), test_code_quality (5), test_crucibai_api (28), test_orchestration_e2e (6), test_smoke (5).
- **No mocks for API/contract tests:** real app, real DB; AI endpoints may return 200, 503, or 500 when keys/deps missing (tests accept all three and assert body only when 200).
