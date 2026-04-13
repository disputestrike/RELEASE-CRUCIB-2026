# Pre-Launch Audit: Click-Through, Endpoints, Connectivity, and “What Would Facebook Test?”

**Purpose:** Surface hidden blockers, untested paths, and gaps before soft launch. Includes endpoint/router/function coverage, line counts, flows, and a Facebook-style pre-launch checklist.

**Generated:** February 2026

---

## 1. Code size (today)

| Area | Lines (approx) | Notes |
|------|----------------|-------|
| **Backend (Python)** | **~4,453** | server.py ~2,420; agent_dag, agent_resilience, code_quality, orchestration, tests, proof scripts |
| **Frontend (src)** | **~10,108** | App, pages, components, ui (JS/JSX only) |
| **Total app code** | **~14,500** | Excludes node_modules, __pycache__, build artifacts |

---

## 2. Backend: endpoints and coverage

### 2.1 API routes (all under `/api`)

| Route | Method | Proof hit? | Pytest | Notes |
|-------|--------|------------|--------|-------|
| `/` | GET | ✅ | ❌* | Root message |
| `/health` | GET | ✅ | ❌* | Health check |
| `/auth/register` | POST | ✅ | ❌* | |
| `/auth/login` | POST | ✅ | ❌* | |
| `/auth/me` | GET | ✅ | ❌* | |
| `/auth/google` | GET | — | — | Redirect; not in proof |
| `/auth/google/callback` | GET | — | — | OAuth callback |
| `/tokens/bundles` | GET | ✅ | — | |
| `/tokens/purchase` | POST | — | — | Often 402 without balance |
| `/tokens/history` | GET | ✅ | — | |
| `/tokens/usage` | GET | ✅ | — | |
| `/build/phases` | GET | ✅ | ❌* | |
| `/build/plan` | POST | **❌** | — | **Not in proof_full_routes** — critical for Workspace |
| `/build/from-reference` | POST | ✅ | — | |
| `/projects` | GET | ✅ | — | |
| `/projects` | POST | **❌** | — | **Not in proof** (creates project, triggers orchestration) |
| `/projects/{id}` | GET | ✅ | — | |
| `/projects/{id}/retry-phase` | POST | **❌** | — | **Not in proof** |
| `/projects/{id}/logs` | GET | ✅ | — | |
| `/projects/{id}/phases` | GET | ✅ | — | |
| `/projects/{id}/duplicate` | POST | — | — | |
| `/projects/{id}/save-as-template` | POST | — | — | |
| `/projects/from-template` | POST | — | — | |
| `/agents` | GET | ✅ | — | |
| `/agents/status/{id}` | GET | ✅ | — | |
| `/agents/activity` | GET | ✅ | — | |
| `/agents/run/*` (17 routes) | GET/POST | ✅ | — | proof hits all 17 |
| `/exports` | GET/POST | ✅ | — | |
| `/examples` | GET | **❌** | — | **Not in proof** — used by Landing + ExamplesGallery |
| `/examples/{name}` | GET | **❌** | — | **Not in proof** |
| `/examples/{name}/fork` | POST | **❌** | — | **Not in proof** |
| `/patterns` | GET | ✅ | — | |
| `/dashboard/stats` | GET | ✅ | — | |
| `/prompts/templates` | GET | ✅ | — | |
| `/prompts/recent` | GET | ✅ | — | |
| `/prompts/saved` | GET | ✅ | — | |
| `/prompts/save` | POST | ✅ | — | |
| `/workspace/env` | GET/POST | ✅ | — | |
| `/share/create` | POST | — | — | |
| `/share/{token}` | GET | ✅ | — | |
| `/templates` | GET | ✅ | — | |
| `/ai/chat` | POST | ✅ | ❌* | |
| `/ai/chat/history/{id}` | GET | ✅ | — | |
| `/ai/chat/stream` | POST | — | — | Streaming; not in proof |
| `/ai/analyze` | POST | ✅ | ❌* | |
| `/ai/validate-and-fix` | POST | ✅ | — | |
| `/ai/explain-error` | POST | ✅ | — | |
| `/ai/suggest-next` | POST | ✅ | — | |
| `/ai/inject-stripe` | POST | ✅ | — | |
| `/ai/generate-readme` | POST | ✅ | — | |
| `/ai/generate-docs` | POST | ✅ | — | |
| `/ai/generate-faq-schema` | POST | ✅ | — | |
| `/ai/security-scan` | POST | ✅ | — | |
| `/ai/optimize` | POST | ✅ | — | |
| `/ai/accessibility-check` | POST | ✅ | — | |
| `/ai/design-from-url` | POST | ✅ | — | |
| `/ai/image-to-code` | POST | — | — | Multipart; not in proof |
| `/voice/transcribe` | POST | **❌** | ❌* | **Multipart file upload — not in proof** |
| `/files/analyze` | POST | ✅ | — | proof uses json, not file |
| `/rag/query` | POST | ✅ | — | |
| `/search` | POST | ✅ | ❌* | |
| `/export/zip` | POST | ✅ | — | |
| `/export/github` | POST | ✅ | — | |
| `/export/deploy` | POST | ✅ | — | |
| `/stripe/create-checkout-session` | POST | ✅ | — | |
| `/stripe/webhook` | POST | — | — | Webhook; not called in proof |

**WebSocket:** `/ws/projects/{project_id}/progress` — not hit by proof (would need WS client).

*❌* = test exists but **fails when backend is not running** (test_crucibai_api, test_api_contract hit live server).

### 2.2 Hidden blockers / not covered by proof

| Item | Risk | Action |
|------|------|--------|
| **POST /build/plan** | High | Used by Workspace on every plan; add to proof or pytest with mock. |
| **GET /examples**, **GET /examples/{name}**, **POST /examples/{name}/fork** | Medium | Landing + ExamplesGallery; add to proof. |
| **POST /projects** (create) | High | Creates project + starts orchestration; add with mock or test user. |
| **POST /projects/{id}/retry-phase** | Low | Add to proof with fake project id (expect 404 without real project). |
| **POST /voice/transcribe** | Medium | Multipart file; add proof with small audio file or expect 400/503. |
| **WebSocket progress** | Medium | E2E or manual; or add small WS test script. |

---

## 3. Frontend: routes and critical flows

### 3.1 Routes (App.js)

| Path | Component | Auth | Critical flow |
|------|-----------|------|---------------|
| `/` | LandingPage | No | Load, hero, examples (GET /api/examples), Try build |
| `/auth` | AuthPage | No | Login, register, Google |
| `/workspace` | Workspace | No* | Plan (POST /build/plan), build, tools, voice |
| `/app` | Layout (Dashboard) | Yes | GET /projects, GET /dashboard/stats |
| `/app/projects/new` | ProjectBuilder | Yes | POST /projects (name, description, type, requirements) |
| `/app/projects/:id` | AgentMonitor | Yes | GET /projects/:id, agents/status, phases, logs, WS progress, retry-phase |
| `/app/tokens` | TokenCenter | Yes | GET tokens/bundles, history, usage; POST purchase |
| `/app/settings` | Settings | Yes | GET/POST /workspace/env |
| `/app/workspace` | Workspace | Yes | Same as /workspace with auth |
| `/share/:token` | ShareView | No | GET /share/{token} |
| `/benchmarks` | Benchmarks | No | Static + BENCHMARK_REPORT content |
| `/pricing` | Pricing | No | GET /tokens/bundles |
| `/privacy`, `/terms` | Privacy, Terms | No | Static |
| Others | Templates, Patterns, Learn, Prompts, etc. | Mix | GET templates/patterns/prompts |

### 3.2 Click-through flows to validate

| Flow | Steps | Endpoints / checks |
|------|--------|---------------------|
| **Landing → Examples** | Open / → scroll to #examples | GET /api/examples returns 200; cards or fallback render. |
| **Landing → Sign up** | Click Get started → Register | POST /auth/register → redirect to /app. |
| **Login** | /auth → Login with email/password | POST /auth/login → token stored → GET /auth/me. |
| **Dashboard** | /app (with token) | GET /api/projects, GET /api/dashboard/stats; Layout shows “Backend connected” if health OK. |
| **New project** | /app/projects/new → pick type → name + description → Create | POST /api/projects with build_kind; redirect to /app/projects/:id. |
| **AgentMonitor** | /app/projects/:id | GET project, agents/status, phases, logs; WebSocket connects; retry-phase button if suggest_retry. |
| **Workspace plan** | /workspace → type prompt → Plan | POST /api/build/plan; plan + suggestions shown. |
| **Workspace build** | After plan → Start build (creates project) | POST /api/projects then orchestration runs; progress via WS or polling. |
| **Settings env** | /app/settings → API & Env | GET/POST /api/workspace/env. |
| **Voice (if used)** | Workspace → mic → transcribe | POST /api/voice/transcribe (multipart); needs OPENAI_API_KEY. |

### 3.3 Connectivity

| Check | How |
|-------|-----|
| Frontend → Backend | All requests use `API = REACT_APP_BACKEND_URL + '/api'`; default http://localhost:8000. |
| CORS | Backend allows `CORS_ORIGINS` (default *). For production set frontend origin. |
| Health in UI | Layout footer: GET /api/health; “Backend connected” or “Backend unavailable” + Retry. |
| WebSocket | BuildProgress uses `wsUrl = apiBaseUrl (replace http→ws) + '/ws/projects/:id/progress'`. |

---

## 4. Pytest and proof summary

| Suite | Purpose | When passing |
|-------|---------|--------------|
| **test_agent_dag.py** | DAG, phases, context | Always (no server). |
| **test_agent_resilience.py** | Criticality, fallback, timeouts | Always. |
| **test_code_quality.py** | score_generated_code | Always. |
| **test_orchestration_e2e.py** | Orchestration mocks, quality, failure recovery | Always (mocked). |
| **test_smoke.py** | Health, critical GETs no 500 | When backend is up. |
| **test_api_contract.py** | Health, root, auth, build/phases, voice 422 | **Requires backend running**; fails in CI if no server. |
| **test_crucibai_api.py** | Health, root, chat, analyze, search | **Requires backend running**; fails in CI if no server. |
| **proof_full_routes.py** | ~60+ route hits (manual script) | When backend up; ≥85% pass. |

**Gap:** Contract/API tests assume live server. For CI without server, either mock HTTP or run backend in CI and then run these.

---

## 5. What would Facebook (or a big co) test before soft launch?

(Abbreviated checklist; not all are required for a minimal soft launch.)

| Category | Examples |
|----------|----------|
| **Security** | Auth: no token → 401. No secrets in frontend bundle. CORS only to your domain. Rate limit or abuse on auth/expensive endpoints. |
| **Privacy / legal** | Privacy policy + Terms linked; data retention stated; no PII in logs (or redacted). |
| **Availability** | Health check; dependency (MongoDB) failure handled; optional circuit breaker for LLM. |
| **Critical path** | E2E: Register → Login → New Project → Build (or plan only) → Project page shows status/completed. |
| **API correctness** | Key endpoints return 200/201/401/404 (not 500) for known cases; proof_full_routes or equivalent. |
| **Frontend errors** | No blank screen; ErrorBoundary; “Add API key” when build fails for key. |
| **Performance** | Health/simple GETs &lt; 2s; build/plan can be 30–60s (acceptable). Optional: p95 latency, time to first byte. |
| **Load** | Only if you have a target (e.g. 50 concurrent). Otherwise defer. |
| **Accessibility** | Basic: focus, contrast, labels (optional for day one). |
| **Flooders / abuse** | Rate limit login/register; optional rate limit on /build/plan and /ai/chat to avoid token exhaustion. |

---

## 6. Recommended actions before soft launch

| Priority | Action |
|----------|--------|
| 1 | **Add to proof_full_routes:** GET /examples, GET /examples/{name}, POST /build/plan (minimal body), POST /projects (minimal; may 402), POST /projects/{id}/retry-phase (expect 404 without real id). |
| 2 | **Manual click-through:** Landing → Examples; Register → Dashboard; New Project → AgentMonitor; Workspace → Plan (and optionally one full build with API keys). |
| 3 | **Smoke in CI:** Run test_smoke.py (or health + 2–3 GETs) with backend started in CI; or run proof_full_routes and require ≥85% pass. |
| 4 | **Optional:** One E2E (Playwright/puppeteer): open app → login → new project → wait for “completed” or “failed” (with mocked or real LLM). |
| 5 | **Defer:** Full stress/load, full a11y audit, rate limiting (add when you have traffic/abuse concern). |

---

## 7. Will this work?

- **Backend:** ~80+ routes; proof hits most; **gaps:** /build/plan, /examples (3), POST /projects, retry-phase, voice (multipart), WS. Fixing the proof and doing one manual pass reduces hidden surprises.
- **Frontend:** Routes and flows are wired; connectivity is correct if `REACT_APP_BACKEND_URL` and CORS are set. One full click-through (register → project → build or plan) validates the critical path.
- **Tests:** Unit/orchestration tests pass without server; contract/API tests need running backend. Adding proof coverage for critical routes + smoke (or proof) in CI gives confidence.

**Bottom line:** It can work for soft launch after: (1) adding the missing proof routes or manual checks for build/plan, examples, project create, (2) one full click-through, and (3) ensuring backend + frontend + MongoDB are running in the target environment. Stress/load and “Facebook-level” depth can follow after first users.
