# Fortune 100–Level Test Plan

Enterprise-grade test coverage across every line, folder, and section of the CrucibAI application.

---

## 1. Test Layers

| Layer | Scope | Tool | Location |
|-------|-------|------|----------|
| **L1** | API contract (every endpoint) | pytest | `backend/tests/test_api_full_coverage.py` |
| **L2** | Unit (agents, utils, quality) | pytest | `backend/tests/test_modules_unit.py` |
| **L3** | Integration (orchestration, auth, projects) | pytest | `backend/tests/test_*.py` |
| **L4** | Security (401, 403, no leakage) | pytest | `backend/tests/test_security.py`, `test_admin.py` |
| **L5** | Data integrity (schema, no password) | pytest | `backend/tests/test_data_integrity.py` |
| **L6** | User journeys (register → build → deploy) | pytest | `backend/tests/test_user_journeys.py` |
| **L7** | E2E critical paths | Playwright | `frontend/e2e/*.spec.js` |
| **L8** | E2E full route coverage | Playwright | `frontend/e2e/routes.spec.js` |
| **L9** | Smoke (health, public pages) | pytest + Playwright | `test_smoke.py`, `smoke.spec.js` |
| **L10** | Accessibility (WCAG) | Playwright | `frontend/e2e/accessibility.spec.js` |

---

## 2. Backend: Every API Route

Every `@api_router` endpoint must have at least one test that:
- Returns expected status (200/201/400/401/403/404/422/500) for valid/invalid input
- Validates response schema (keys present, types correct)
- For protected routes: 401 without token, 403 for wrong role
- For admin routes: 403 for non-admin, 200 for admin

**Coverage:** `server.py` (all routes), `proof_full_routes.py` (route list as source of truth).

---

## 3. Backend: Every Module

| Module | Tests |
|--------|-------|
| `agent_dag.py` | DAG structure, topological sort, phases, context truncation |
| `agent_resilience.py` | Critical agents, fallbacks, timeouts |
| `utils/rbac.py` | Role enum, permissions, has_permission |
| `utils/audit_log.py` | Audit logger init, write |
| `agents/legal_compliance.py` | legal_check_request, blocked categories |
| `quality.py` | score_generated_code, verdict |
| `code_quality.py` | score breakdown |
| `orchestration.py` | run phases, context build |
| `proof_agents.py` | Agent run stubs |
| `proof_full_routes.py` | Route list consistency |

---

## 4. Frontend: Every Page & Component

| Area | Pages/Components | Test Type |
|------|------------------|-----------|
| Public | Landing, Auth, Pricing, About, Terms, Privacy, Aup, Dmca, Cookies, Features, Enterprise, Benchmarks | E2E route load |
| App | Dashboard, Workspace, Builder, ProjectBuilder, AgentMonitor, Settings, TokenCenter, ExportCenter | E2E + unit where feasible |
| Admin | AdminDashboard, AdminUsers, AdminUserProfile, AdminBilling, AdminAnalytics, AdminLegal | E2E (with admin user) |
| Library | Patterns, Templates, Prompts, Learn, Shortcuts | E2E route load |
| Components | Layout, BuildProgress, DeployButton, QualityScore, PublicFooter, PublicNav | E2E or integration |
| UI | All `components/ui/*` | Unit (render, props) |

---

## 5. E2E: Full Route Coverage

Every route in `App.js` must load without crash:
- `/`, `/auth`, `/pricing`, `/about`, `/terms`, `/privacy`, `/aup`, `/dmca`, `/cookies`
- `/enterprise`, `/features`, `/templates`, `/patterns`, `/learn`, `/shortcuts`, `/prompts`, `/benchmarks`
- `/app`, `/app/workspace`, `/app/builder`, `/app/settings`, `/app/tokens`, `/app/exports`
- `/app/projects/new`, `/app/admin` (redirect if non-admin)

---

## 6. Run Commands

```bash
# Backend (full suite)
cd backend && python -m pytest tests/ -v --tb=short

# Backend with coverage
cd backend && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=80

# Frontend unit
cd frontend && npm test -- --watchAll=false --ci

# E2E (requires backend + frontend running)
cd frontend && npx playwright test
```

---

## 7. Success Criteria

- **Backend:** All pytest tests pass; no skipped tests unless env-dependent (e.g. live Stripe)
- **Frontend:** All Jest tests pass
- **E2E:** All Playwright specs pass (requires frontend + backend running)
- **Coverage:** ≥80% line coverage on backend core modules
- **Zero regressions:** Every route, module, and directory covered by at least one test

---

## 8. Current Status (Implemented)

| Layer | Tests | Status |
|-------|-------|--------|
| L1 API full coverage | 20 tests, 90+ routes | ✅ `test_api_full_coverage.py` |
| L2 Module unit | 18 tests (agent_dag, rbac, audit, legal, quality) | ✅ `test_modules_unit.py` |
| L3 Integration | orchestration, crucibai_api | ✅ existing |
| L4 Security + Admin | 7 admin, 3 security | ✅ `test_admin.py`, `test_security.py` |
| L5 Data integrity | 3 tests | ✅ |
| L6 User journeys | 2 tests | ✅ |
| L7 E2E critical | smoke, signup→workspace | ✅ |
| L8 E2E routes | 17 public routes | ✅ `e2e/routes.spec.js` |
| L9 Smoke | health, root | ✅ |
| L10 Accessibility | a11y | ✅ `e2e/accessibility.spec.js` |

**Backend:** 154 passed, 2 skipped (webhook env-dependent)

### Admin Fortune 100 Coverage (31 backend + 8 frontend)

| Layer | Tests | File |
|-------|-------|------|
| Access control | 4 (401, 403, regular user) | test_admin.py |
| Admin API schema | 4 (dashboard, users, analytics, profile) | test_admin.py |
| Security & RBAC | 13 (owner, operations, support, analyst, validation) | test_admin_security.py |
| Workflows | 6 (suspend, grant, export, downgrade, blocked, no-suspend-admin) | test_admin_workflows.py |
| Audit logging | 4 (suspend, grant, downgrade, required fields) | test_admin_audit.py |
| Frontend AdminDashboard | 4 (loading, data, stats, error) | AdminDashboard.test.jsx |
| Frontend AdminUsers | 4 (heading, users, empty, error) | AdminUsers.test.jsx |
