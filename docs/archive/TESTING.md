# Enterprise-Grade Testing Framework – CrucibAI

This document maps the **9-layer, 27-point** testing pyramid to this repository and how to run each layer.

---

## Full 27-point run (recommended)

Run the **complete** enterprise framework and get a **PASS/FAIL certificate** with real results and accountability:

```bash
# From repo root. Requires: Node, Python, backend deps, frontend deps.
# Backend must be running for Layer 3 & 9 (or start it in another terminal).
node scripts/run-full-27-tests.js
```

- **Output:** Every test result (PASSED / FAILED / WARN / SKIPPED), written to `test_reports/`.
- **Certificate:** `test_reports/CERTIFICATE.md` — overall PASS/FAIL, failures with root cause and corrective action.
- **Evidence:** `test_reports/full_run_<timestamp>.json` — full results in accountability schema format.
- **Exit code:** `0` = pass (or pass with warnings); `1` = at least one **critical** failure.

Optional and E2E tests (e.g. 3.5, 5.1, 7.1, 7.2, 8.1) are marked optional; if they fail, the run is **WARN** not FAIL unless you require them.

---

## Quick reference – run tests by layer

Run frontend commands from the `frontend` directory so Jest resolves `node_modules` correctly.

```bash
# 1. Code quality (frontend)
cd frontend && npm run lint && npm run test -- --watchAll=false --coverage

# 2. Backend unit + integration + API contract
cd backend && pip install -r requirements.txt && pytest tests/ -v

# 2b. Production validation (5-layer) – endpoint mapping, webhooks, data integrity, user journeys, security
cd backend && python -m pytest tests/test_endpoint_mapping.py tests/test_webhook_flows.py tests/test_data_integrity.py tests/test_user_journeys.py tests/test_security.py -v --tb=short

# 2c. Backend coverage (target >80% on server)
cd backend && pytest tests/ --cov=server --cov-report=html --cov-report=term

# 3. Security audit (frontend)
cd frontend && npm audit

# 4. E2E (requires frontend + backend running)
cd frontend && npx playwright test
```

**Deploy & Enterprise endpoints (optional):**
- `GET /api/projects/{id}/deploy/zip` and `GET /api/projects/{id}/export/deploy` — deploy-ready ZIP (auth required).
- `POST /api/enterprise/contact` — enterprise lead capture (body: company, email, team_size, use_case, budget, message).

---

## Layer 1: Code quality & standards

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **1.1 Linting** | `cd frontend && npm run lint` | Zero ESLint errors |
| **1.2 Security scan** | `cd frontend && npm audit` | No critical/high; fix or accept |
| **1.3 Coverage** | `cd frontend && npm run test -- --watchAll=false --coverage` | Aim ≥80% on critical paths |
| **1.4 Type safety** | N/A (JS project); use JSDoc where helpful | — |
| **1.5 Code smell** | Lint + manual review | No large duplication, complexity < 10 |
| **1.6 Documentation** | README, this file, API docs | README has setup; TESTING.md has run commands |

---

## Layer 2: Unit & component tests

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **2.1 Unit tests** | `cd frontend && npm test -- --watchAll=false` | All tests pass, no timeouts |
| **2.2 Component isolation** | Same; see `src/**/*.test.js(x)` | Components render without errors |
| **2.3 Error handling** | Unit tests cover try/catch and error states | No unhandled rejections in tests |
| **2.4 Mocks** | Tests use mocks for API (see setupTests) | No real API calls in unit tests |

---

## Layer 3: Integration tests

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **3.1 API contract** | `cd backend && pytest tests/test_crucibai_api.py tests/test_api_contract.py -v` | Status codes and response shape match |
| **3.2 Database** | Same; backend uses MongoDB (ensure MONGO_URL set) | Writes/reads persist |
| **3.3 Auth** | `pytest tests/ -v -k "auth or Auth"` | Register, login, /auth/me, protected routes |
| **3.4 External APIs** | Manual / optional; backend calls OpenAI/Anthropic | Keys set; no 5xx from provider |
| **3.5 State / data flow** | E2E and frontend tests | State updates reflected in UI |

---

## Layer 4: Performance (optional in CI)

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **4.1 API response** | `cd backend && pytest tests/test_smoke.py -v` or load tool | p95 < 200ms for health/simple endpoints |
| **4.2 Frontend** | `npx lighthouse http://localhost:3000 --output=json` | LCP < 2.5s, CLS < 0.1 |
| **4.3 Load** | e.g. `npx artillery quick --count 10 --num 5 http://localhost:8000/api/health` | No errors, acceptable latency |

---

## Layer 5: Accessibility & UX

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **5.1 WCAG 2.1 AA** | `npx playwright test e2e/accessibility.spec.js` or axe DevTools | Zero critical violations |
| **5.2 UX** | Manual; forms, errors, mobile layout | Clear errors, 44px touch targets, responsive |

---

## Layer 6: Security

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **6.1 OWASP / penetration** | `npm audit`; optional OWASP ZAP | No critical vulns; inputs validated |
| **6.2 Data privacy** | Review .env not committed; HTTPS in prod | No secrets in repo; HTTPS enforced |

---

## Layer 7: End-to-end user flows

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **7.1 Critical journey** | `cd frontend && npx playwright test e2e/` | Sign up → login → workspace → build flow |
| **7.2 Error recovery** | E2E tests that simulate network/API errors | Retry or clear error message |

---

## Layer 8: Cross-browser

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **8.1 Browsers** | `npx playwright test --project=chromium --project=firefox --project=webkit` | Core flows pass on Chrome, Firefox, Safari |

---

## Layer 9: Deployment & smoke

| Test | What to run | Pass criteria |
|------|-------------|----------------|
| **9.1 Post-deploy** | `pytest backend/tests/test_smoke.py -v` with backend URL | App starts; /api/health 200; critical endpoints respond |

---

## CI pipeline (GitHub Actions)

Workflow file: `.github/workflows/enterprise-tests.yml`

- Lint frontend  
- Run frontend unit tests (with coverage)  
- Run backend pytest (unit + integration + contract + smoke)  
- Optional: E2E (Playwright) against a running stack  
- Optional: `npm audit`  

---

## 27 tests (9 layers)

| Layer | Tests | Description |
|-------|-------|-------------|
| 1 | 1.1–1.6 | Code quality: Lint, Security scan, Coverage, Type safety (skip), Code smell, Documentation |
| 2 | 2.1–2.4 | Unit & component: Unit tests, Component isolation, Error handling, Mocks |
| 3 | 3.1–3.5 | Integration: API contract, Database, Auth contract, External APIs (skip), State/E2E (optional) |
| 4 | 4.1–4.3 | Performance: API response time, Lighthouse (optional), Load (optional) |
| 5 | 5.1–5.2 | Accessibility: WCAG a11y (optional), UX manual (skip) |
| 6 | 6.1–6.2 | Security: npm audit, Data privacy (no secrets in repo) |
| 7 | 7.1–7.2 | E2E: Critical user journey (optional), Error recovery (optional) |
| 8 | 8.1 | Cross-browser (optional) |
| 9 | 9.1–9.2 | Post-deploy smoke, Frontend build |

## Accountability & test results

- **Full run + certificate:** `node scripts/run-full-27-tests.js` → `test_reports/CERTIFICATE.md`, `test_reports/full_run_<id>.json`
- Schema for test run results: `test_reports/ACCOUNTABILITY_SCHEMA.json`
- Pytest JUnit XML: `pytest tests/ -v --junitxml=test_reports/pytest/results.xml`
- Frontend coverage: `frontend/coverage/` after `npm run test -- --coverage`

---

## Go/No-Go summary

- **Go:** Lint passes, all unit + integration + contract + smoke tests pass, no critical security issues, E2E critical journey passes (if run).
- **No-Go:** Any critical security finding, auth/API contract failure, or broken critical E2E flow.
