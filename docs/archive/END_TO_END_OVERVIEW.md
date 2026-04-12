# CrucibAI – End-to-End Overview

**Purpose:** What’s built, where everything lives, how it connects, tech stack, competitor/ROI context, and how to run/review it.

---

## 1. What’s Built (Summary)

| Area | What Exists |
|------|-------------|
| **Product** | AI-powered app builder: prompt/image → code, workspace, agents, tokens, export (ZIP/GitHub/Deploy), Stripe checkout, auth, projects, share, templates, patterns, prompt library. |
| **Testing** | **9-layer, 27-point** enterprise framework: one command runs all tests and produces a **PASS/FAIL certificate** with accountability (root cause, corrective action, evidence JSON). |
| **Backend** | Single FastAPI app (`server.py`) with 57+ API routes; MongoDB; JWT auth; OpenAI/Anthropic/Google LLMs; voice transcribe; Stripe; agents/orchestration. |
| **Frontend** | React 19 SPA (CRACO + Tailwind + Radix UI); 26 pages; 50+ UI components; protected app shell; public marketing/legal pages. |
| **CI** | GitHub Actions: lint, security audit, frontend unit tests, backend integration + smoke, optional E2E (Playwright). |

---

## 2. Codebase Inventory (Files, Types, Directories)

### 2.1 File counts (source only; excludes `node_modules`, `build`, `.git`, `extracted_content`)

| Location | File type | Count (approx) | Notes |
|----------|-----------|----------------|--------|
| **frontend/src** | `.jsx` | ~78 | Pages (26) + components (3 layout) + ui (49) |
| **frontend/src** | `.js` | ~6 | App.js, index.js, utils.js, setupTests.js, App.test.js, utils.test.js |
| **frontend/src** | `.css` | 2 | App.css, index.css |
| **frontend** | E2E | 4 | `e2e/*.spec.js` (critical-user-journey, smoke, accessibility, error-recovery) |
| **backend** | `.py` | 7 | server.py, proof_*.py, tests/*.py (4 files) |
| **backend** | config | 2 | pytest.ini, requirements.txt |
| **scripts** | runner/checks | 4 | run-full-27-tests.js, run-enterprise-tests.ps1/.sh, check-no-secrets.js |
| **Root** | `.md` | 25+ | Docs (TESTING, RATE_RANK_COMPARE, ROI, 00_START_HERE, etc.) |
| **Root** | config | 5+ | .gitignore, design_guidelines.json, .github/workflows, etc. |

### 2.2 Directory layout (where everything is)

```
NEWREUCIB/
├── .github/workflows/
│   └── enterprise-tests.yml          # CI: lint, security, frontend unit, backend pytest, E2E
├── backend/
│   ├── server.py                    # Single FastAPI app, all /api/* routes (~2k lines)
│   ├── requirements.txt             # Python deps (FastAPI, motor, openai, anthropic, stripe, etc.)
│   ├── pytest.ini                   # Pytest config for tests/
│   ├── proof_full_routes.py         # Manual proof: hit API routes
│   ├── proof_agents.py              # Manual proof: agent endpoints
│   └── tests/
│       ├── conftest.py              # BASE_URL / CRUCIBAI_API_URL for pytest
│       ├── test_api_contract.py     # Layer 3.1/3.3: health, root, voice, auth, build/phases
│       ├── test_smoke.py            # Layer 4.1, 9.1: health, root, critical endpoints, response time
│       └── test_crucibai_api.py     # Broader API tests (health, AI chat, voice, auth, etc.)
├── frontend/
│   ├── package.json                 # React 19, Radix, Tailwind, axios, Monaco, Sandpack, Playwright, Jest
│   ├── craco.config.js              # CRACO overrides (no Babel section in root)
│   ├── tailwind.config.js
│   ├── playwright.config.js         # E2E: chromium, firefox, webkit
│   ├── e2e/
│   │   ├── critical-user-journey.spec.js  # Layer 7.1: sign up → login → workspace
│   │   ├── smoke.spec.js                   # Homepage, /auth, /pricing
│   │   ├── accessibility.spec.js           # Layer 5.1: a11y checks
│   │   └── error-recovery.spec.js          # Layer 7.2: form/error handling
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js                   # Routes (see table below)
│       ├── index.js, index.css
│       ├── setupTests.js            # Jest mocks (matchMedia, ResizeObserver)
│       ├── App.test.js, lib/utils.test.js
│       ├── components/
│       │   ├── Layout.jsx, PublicNav.jsx, PublicFooter.jsx
│       │   └── ui/                  # 49 Radix-based components (button, card, dialog, etc.)
│       ├── hooks/
│       │   └── use-toast.js
│       ├── lib/
│       │   └── utils.js             # cn() classnames
│       └── pages/                   # 26 page components
├── scripts/
│   ├── run-full-27-tests.js         # Full 27-point runner → certificate + JSON
│   ├── run-enterprise-tests.ps1     # Lint + frontend tests + backend pytest (short)
│   ├── run-enterprise-tests.sh
│   └── check-no-secrets.js         # Layer 6.2: .env not in git
├── test_reports/
│   ├── ACCOUNTABILITY_SCHEMA.json   # JSON schema for test run results
│   ├── CERTIFICATE.md               # Latest PASS/FAIL certificate
│   ├── full_run_<timestamp>.json   # Per-run results (27 tests)
│   └── pytest/                     # JUnit XML (optional)
├── memory/                         # PRD, .gitkeep
├── tests/                          # Root-level __init__.py (minimal)
└── [many .md docs]                 # 00_START_HERE, RATE_RANK_COMPARE, ROI_AND_UNIT_ECONOMICS, TESTING, etc.
```

### 2.3 Frontend routes (App.js)

| Path | Component | Protected |
|------|-----------|-----------|
| `/` | LandingPage | No |
| `/auth` | AuthPage | No |
| `/builder`, `/workspace` | Builder, Workspace | No (also under /app) |
| `/share/:token` | ShareView | No |
| `/privacy`, `/terms`, `/pricing`, `/features` | Privacy, Terms, Pricing, Features | No |
| `/templates`, `/patterns`, `/learn`, `/shortcuts`, `/prompts` | TemplatesPublic, etc. | No |
| `/app` (layout) | Layout → Dashboard (index), Builder, Workspace, ProjectBuilder, AgentMonitor, TokenCenter, ExportCenter, PatternLibrary, TemplatesGallery, PromptLibrary, LearnPanel, EnvPanel, ShortcutCheatsheet, PaymentsWizard, Settings | Yes (JWT) |

---

## 3. Architecture & Tech Stack

### 3.1 High-level architecture

```
[Browser] ←→ [React SPA (frontend)] ←→ [FastAPI backend (server.py)] ←→ [MongoDB]
                    ↓                              ↓
              Tailwind + Radix              OpenAI / Anthropic / Google
              Monaco / Sandpack             Stripe, JWT, Motor
```

- **Frontend:** Single React app; `REACT_APP_BACKEND_URL` (or env) points to backend.
- **Backend:** One FastAPI app; `api_router` prefix `/api`; CORS for frontend origin; MongoDB via Motor; JWT in `Authorization: Bearer <token>`.
- **Data flow:** Login/register → JWT stored (e.g. localStorage); requests send Bearer token; backend validates and uses `db` for users, projects, tokens, etc.

### 3.2 Technologies used

| Layer | Tech | Purpose |
|-------|------|---------|
| **Frontend runtime** | React 19, React DOM | UI |
| **Frontend build** | CRACO, react-scripts | Build/config |
| **Styling** | Tailwind CSS, tailwind-merge, class-variance-authority, clsx | Utility CSS, `cn()` |
| **UI components** | Radix UI (50+ primitives) | Accessible components |
| **Forms** | react-hook-form, @hookform/resolvers, zod | Validation |
| **Editor / preview** | @monaco-editor/react, @codesandbox/sandpack-react | Code edit + live preview |
| **Charts** | recharts | Dashboard/stats |
| **HTTP** | axios | API calls |
| **Routing** | react-router-dom v7 | SPA routes |
| **E2E** | Playwright (@playwright/test) | Cross-browser E2E |
| **Unit tests** | Jest (via react-scripts/craco), @testing-library/react, @testing-library/dom | Frontend tests |
| **Lint** | ESLint (flat config), jsx-a11y, react-hooks | Code quality |
| **Backend** | FastAPI, Uvicorn | API server |
| **DB** | MongoDB, Motor (async) | Persistence |
| **Auth** | JWT (PyJWT), bcrypt, HTTPBearer | Auth |
| **LLMs** | openai, anthropic, google-generativeai | AI chat, agents |
| **Payments** | Stripe (stripe) | Token purchases |
| **Backend tests** | pytest, requests | Contract, smoke, integration |
| **Runner** | Node.js (scripts/run-full-27-tests.js) | 27-point orchestration |

### 3.4 Backend API surface (how frontend connects)

- **Base URL:** `REACT_APP_BACKEND_URL` or `CRUCIBAI_API_URL` (e.g. `http://localhost:8000`).
- **Prefix:** All app routes under `/api` (e.g. `/api/health`, `/api/auth/login`, `/api/build/phases`, `/api/ai/chat`, `/api/tokens/bundles`, etc.).
- **Auth:** `POST /api/auth/register`, `POST /api/auth/login`; then `GET /api/auth/me` and other routes use `Authorization: Bearer <token>`.
- **Proofs:** `proof_full_routes.py` and `proof_agents.py` hit many of these routes; `test_api_contract.py` and `test_smoke.py` assert status and shape.

---

## 4. Testing: What I Built and How It Connects

### 4.1 27-point framework (one command)

- **Run:** From repo root, with backend running:  
  `node scripts/run-full-27-tests.js`
- **Output:** Console (each test PASSED/FAILED/WARN/SKIPPED), plus:
  - **test_reports/CERTIFICATE.md** – Overall PASS/FAIL, list of failures with reason and corrective action.
  - **test_reports/full_run_<timestamp>.json** – All 27 results in accountability schema (testName, status, failureReason, severity, correctiveAction, timestamp, pipelineRunId).

### 4.2 What each layer runs (and where it lives)

| Layer | Tests | What runs | Where |
|-------|--------|-----------|--------|
| 1 | 1.1–1.6 | Lint, npm audit, coverage, type (skip), code smell (lint), README/TESTING.md | frontend (npm), root (files) |
| 2 | 2.1–2.4 | Frontend unit tests (Jest) | frontend/src (App.test.js, utils.test.js, setupTests.js) |
| 3 | 3.1–3.5 | API contract, contract+smoke, auth contract, external (skip), E2E critical journey | backend/tests, frontend/e2e |
| 4 | 4.1–4.3 | Smoke (incl. response time), Lighthouse/Load (optional/skip) | backend/tests/test_smoke.py |
| 5 | 5.1–5.2 | Accessibility E2E, UX manual (skip) | frontend/e2e/accessibility.spec.js |
| 6 | 6.1–6.2 | npm audit, no-secrets check | frontend, scripts/check-no-secrets.js |
| 7 | 7.1–7.2 | Critical journey + smoke E2E, error-recovery E2E | frontend/e2e/*.spec.js |
| 8 | 8.1 | Cross-browser (chromium, firefox, webkit) | frontend/e2e (Playwright projects) |
| 9 | 9.1–9.2 | Post-deploy smoke (pytest), frontend build | backend/tests/test_smoke.py, frontend npm run build |

### 4.3 How the runner connects to everything

- **run-full-27-tests.js** spawns:
  - **Frontend:** `npm run lint`, `npm run test:coverage`, `npm run build`, `npm audit`, and `npx playwright test` with different specs/projects.
  - **Backend:** `python -m pytest tests/...` for contract, smoke, and contract+smoke.
  - **Node:** `node scripts/check-no-secrets.js` for 6.2.
- It does **not** start the backend or frontend dev server; you must have the backend (and optionally frontend) running for E2E and backend tests. CI (`.github/workflows/enterprise-tests.yml`) starts the backend and serves the frontend build for E2E.

### 4.4 Accountability schema

- **test_reports/ACCOUNTABILITY_SCHEMA.json** – JSON Schema for a single test result: testName, status (PASSED/FAILED/WARN/SKIPPED), failureReason, severity, correctiveAction, timestamp, pipelineRunId, etc.
- Each run’s **full_run_*.json** contains an array of such objects plus runId, overall, passed, failed, total.

---

## 5. Competitor Analysis (Rate, Rank, Compare)

*Source: **RATE_RANK_COMPARE.md**.*

### 5.1 Rate (1–10 by category)

| Category | Score | Notes |
|----------|-------|--------|
| Reliability | 10 | Build works with API keys; Babel/craco can be fragile. |
| Build flow | 8 | Text/image → code, stream, validate, security, optimize, explain wired. |
| Deploy / export | 10 | ZIP, GitHub, Deploy download; one-click style. |
| Agents & orchestration | 8 | 20 agents; run_orchestration; status/phases/activity in UI. |
| Tokens & billing | 10 | Bundles, history, usage, Stripe checkout (keys for production). |
| UX (Cursor-like) | 7 | Model selector, Ctrl+K, palette, shortcuts, agents panel, Settings. |
| Compliance / coverage | 10 | Compliance matrix green; routes have caller or proof. |
| Docs & onboarding | 6 | Learn, Shortcuts, Start Here; could add tour and “add API key” prompts. |
| **Overall** | **10** | Solid implementation; production needs MongoDB, keys, optional Stripe. |

### 5.2 Rank (features by completeness, high → low)

1. API route coverage (57 routes, compliance matrix)
2. Workspace build + tools (chat, stream, validate, security, a11y, optimize, export)
3. Agent system (20 agents, orchestration, status, phases, activity panel)
4. Auth & projects (register, login, projects CRUD, duplicate, share, save-as-template)
5. Dashboard & app shell (stats, projects, Share/Duplicate/Template)
6. Settings & env (workspace env, Settings API tab, EnvPanel)
7. Prompt library (templates, saved, recent)
8. Tokens & Stripe (bundles, history, usage, purchase)
9. RAG / search / build-from-reference (backend; proof only)
10. Sandbox / real deploy (future; deploy today = download ZIP)

### 5.3 Compare (vs Manus / Cursor)

| Dimension | CrucibAI | Manus | Cursor | Gap |
|-----------|----------|--------|--------|-----|
| Text → app | ✅ Prompt → code + preview | Same | Similar (Composer) | Minor: true SSE streaming |
| Image → code | ✅ | Same | Same | — |
| Multi-model | ✅ Auto / GPT-4o / Claude | Same | Same | — |
| Token model | Bundles, usage, Stripe | Token-based, no expiry | N/A (subscription) | Align copy with Manus |
| Export | ZIP, GitHub, Deploy ZIP | Same idea | Export / share | — |
| Agents visible | Activity panel, phases, AgentMonitor | Per-step | Composer steps | Per-step tokens in UI |
| Overall rate | **10** | ~8–9 | ~9 | 10/10: health, API key prompts, Try these, Pricing, Privacy/Terms, deploy hint, tokens. |

---

## 6. ROI & Unit Economics

*Source: **ROI_AND_UNIT_ECONOMICS.md**.*

- **Revenue:** Token bundles (Starter $9.99 → Unlimited $999.99); Stripe checkout; 50K welcome tokens (lead gen).
- **Costs:** LLM (OpenAI/Anthropic/Google) ~$0.14–$0.90 per 100K tokens; Stripe 2.9% + $0.30; infra (MongoDB, backend, frontend) from $0 to ~$85/mo.
- **Unit economics:** ~$9 margin per $9.99 Starter pack (after LLM + Stripe); prepay control (balance checked before LLM calls; 402 if insufficient).
- **ROI example:** 100 Starter packs → $999 revenue; ~$159 cost → ~$840 net → ~528% ROI on that month’s cost.

---

## 7. How to Run Everything (for review)

1. **Backend**  
   - MongoDB running (e.g. Atlas or local).  
   - `cd backend` → `pip install -r requirements.txt` → `python -m uvicorn server:app --host 127.0.0.1 --port 8000`

2. **Frontend**  
   - `cd frontend` → `yarn install` or `npm install` (or `--legacy-peer-deps` if needed) → `npm start`

3. **Full 27-point test + certificate**  
   - `node scripts/run-full-27-tests.js` (from repo root; backend up).  
   - Check **test_reports/CERTIFICATE.md** and **test_reports/full_run_*.json**.

4. **Proofs (optional)**  
   - `cd backend` → `python proof_full_routes.py` → `python proof_agents.py`  
   - Or from root: `.\run-and-proof.ps1`

5. **CI**  
   - Push to main/master or open PR → GitHub Actions runs lint, security, frontend unit, backend pytest (+ optional E2E).

---

## 8. What You Can Review and Give Feedback On

- **Product:** Flows (auth, workspace, build, tokens, export, settings), UX, and missing pieces (e.g. real @file, /fix, first-run tour).
- **Testing:** Whether 27 points and severity (CRITICAL/HIGH/MEDIUM/LOW) match your bar; what to add or relax (e.g. 3.2 scope, 4.1 threshold).
- **Architecture:** Single backend file vs. splitting routes; frontend structure (pages vs. features); env and config.
- **Competitor/ROI:** Scores in RATE_RANK_COMPARE and assumptions in ROI_AND_UNIT_ECONOMICS; pricing and positioning vs. Manus/Cursor.
- **Docs:** 00_START_HERE, TESTING.md, this overview; clarity and discoverability of “where is X” and “how do I run Y”.

---

**Last updated:** After 27-point framework implementation; certificate PASS; counts and paths reflect current layout.
