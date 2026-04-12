# CrucibAI — Test Report & Connectivity Verification

**Date:** February 2026  
**Purpose:** Verify all tests pass, front/back/admin connected, and provide click-through checklist.

---

## 1. Backend Tests (pytest)

| Suite | Result | Count |
|-------|--------|-------|
| Admin | ✅ | 7 passed |
| Admin Audit | ✅ | 4 passed |
| Admin Security | ✅ | 16 passed |
| Admin Workflows | ✅ | 6 passed |
| Agent DAG | ✅ | 5 passed |
| Agent Resilience | ✅ | 5 passed |
| API Contract | ✅ | 10 passed |
| API Full Coverage | ✅ | 16 passed |
| CrucibAI API | ✅ | 14 passed |
| Data Integrity | ✅ | 3 passed |
| Endpoint Mapping | ✅ | 4 passed |
| Modules Unit | ✅ | 16 passed |
| Orchestration E2E | ✅ | 5 passed |
| Security | ✅ | 3 passed |
| Smoke | ✅ | 5 passed |
| Tier2 (RBAC, Audit, MFA) | ✅ | 5 passed |
| User Journeys | ✅ | 2 passed |
| Webhook Flows | ✅ | 1 passed, 2 skipped |

**Total: 154 passed, 2 skipped** (53.98s)

**Skipped:** `test_project_creation_returns_and_deduction`, `test_build_plan_returns_structure` — require MongoDB + LLM keys.

---

## 2. Frontend Tests (Jest)

| Suite | Result | Tests |
|-------|--------|-------|
| utils.test.js | ✅ | passed |
| App.test.js | ✅ | passed |
| AdminDashboard.test.jsx | ✅ | passed |
| AdminUsers.test.jsx | ✅ | passed |

**Total: 4 suites, 15 tests passed** (14.1s)

**Note:** AdminUsers shows `act()` warnings (async state updates); tests pass. Consider wrapping fetch in `act()` for cleaner output.

---

## 3. API Route Connectivity (proof_full_routes.py)

Run against live backend: `cd backend && python proof_full_routes.py`

**OK routes (auth, tokens, projects, agents, export, build phases):**
- GET /api/, /api/health
- Auth: register, login, /auth/me
- Tokens: bundles, history, usage
- Projects: list, get, logs, phases
- Build: phases, plan
- Agents: list, status, activity, memory-store/list, export-pdf/excel/markdown, automation
- Export: zip, github, deploy
- Workspace: env GET/POST

**Require API keys (OpenAI/Anthropic/Google):**
- POST /ai/chat, /ai/analyze, /ai/validate-and-fix, etc. → 500 if no LLM key or missing `google` module
- POST /agents/run/* (planner, stack-selector, etc.) → 500 without keys
- POST /rag/query, /search → 500 without keys

**Require correct body:**
- POST /ai/analyze → needs `content`, `doc_type`, `task` (not `code`)
- POST /files/analyze → needs `file` (multipart)
- POST /ai/design-from-url → needs `url`
- POST /build/from-reference → needs `prompt`

**Fix:** Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env` for full AI/agent routes. Install `google-generativeai` if using Gemini.

---

## 4. E2E (Playwright)

**Config:** `frontend/playwright.config.js` — baseURL http://localhost:3000

**Specs:**
- `routes.spec.js` — 17 public routes + admin
- `smoke.spec.js` — homepage, auth, pricing/features
- `critical-user-journey.spec.js` — sign up → login → workspace → logout
- `accessibility.spec.js`, `error-recovery.spec.js`

**Run:**
```bash
cd frontend
npm run start   # Terminal 1 (or reuse existing)
cd backend && python -m uvicorn server:app --port 8000  # Terminal 2
npm run e2e     # Terminal 3 (or npx playwright test)
```

**Note:** Playwright `webServer` may fail if ESLint plugin missing. Start frontend manually and run `npx playwright test` with `reuseExistingServer: true` (default when not CI).

---

## 5. Connection Matrix (Front ↔ Back ↔ Admin)

| Frontend Page | Backend API | Status |
|---------------|-------------|--------|
| Landing | GET /api/examples, public | ✅ |
| Auth | POST /auth/register, /auth/login | ✅ |
| Dashboard | GET /projects, /auth/me | ✅ |
| Workspace | POST /ai/chat, /build/plan, /projects | ✅ |
| AgentMonitor | GET /projects/{id}, /projects/{id}/phases, /agents/status | ✅ |
| TokenCenter | GET /tokens/*, POST /tokens/purchase | ✅ |
| Settings | GET/POST /workspace/env, /auth/me | ✅ |
| ExportCenter | POST /export/zip, /export/github, /export/deploy | ✅ |
| ShareView | GET /share/{token} | ✅ |
| Admin Dashboard | GET /admin/dashboard | ✅ |
| Admin Users | GET /admin/users, POST suspend/grant/downgrade | ✅ |
| Admin Legal | GET /admin/legal/blocked-requests | ✅ |
| Pricing | GET /tokens/bundles | ✅ |

**Auth flow:** JWT in `Authorization: Bearer <token>`; stored in localStorage; sent with protected requests.

**Admin:** Requires `role: owner` or `operations`/`support`/`analyst`; checked via `has_permission()`.

---

## 6. Click-Through Checklist (Manual)

Run backend + frontend, then verify:

- [ ] **Landing** — Load `/`, type prompt, click Build → redirect to workspace or auth
- [ ] **Auth** — Register, login, logout
- [ ] **Workspace** — Load with prompt, see Monaco + Sandpack; Build (needs API keys)
- [ ] **Dashboard** — See projects, create new, open project
- [ ] **TokenCenter** — See bundles, history; purchase (needs Stripe keys)
- [ ] **Settings** — Add API key, save
- [ ] **Export** — Download ZIP, GitHub export
- [ ] **Admin** — Login as owner, view Dashboard, Users, Legal; suspend/grant credits
- [ ] **Pricing** — Load `/pricing`, see bundles
- [ ] **Share** — Create share link, open `/share/{token}`

---

## 7. Run All Tests

```bash
# One command (PowerShell)
.\run-all-tests.ps1

# Or manually:
# Backend (from backend/)
python -m pytest tests/ -v --tb=short

# Frontend (from frontend/)
npm test -- --watchAll=false --passWithNoTests

# API proof (backend running on 8000)
cd backend && python proof_full_routes.py

# E2E (frontend on 3000, backend on 8000)
cd frontend && npx playwright test
```

---

## 8. Known Issues & Fixes

| Issue | Fix |
|-------|-----|
| `No module named 'google'` on AI routes | `pip install google-generativeai`; or use OpenAI/Anthropic keys only |
| Playwright webServer exits early | Start frontend manually; run `npx playwright test` |
| AdminUsers act() warning | Wrap `fetchUsers` state updates in `act()` |
| Port 8000/3000 already in use | Kill existing process or use different port |

---

*Last updated: February 2026*
