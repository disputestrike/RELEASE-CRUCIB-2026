# CrucibAI — Codebase Source of Truth

**Purpose:** Single reference for what we have built: size, structure, directories, and connectivity. Use this to know exactly what exists and where.

**Last updated:** February 2026

---

## 1. Scale (approximate)

| Category | Count | Notes |
|----------|--------|--------|
| **Backend Python files** | 71 | `backend/**/*.py` (excl. __pycache__) |
| **Frontend source files (JS/JSX)** | 116 | `frontend/src/**/*.{js,jsx}` |
| **Backend server (server.py)** | ~5,560 lines | Main API, routes, orchestration, agents, import, deploy |
| **Total lines of code (primary)** | ~37,000+ | Py + JS/JSX excluding node_modules, build, coverage |
| **Documentation (.md)** | 150+ | Root + docs/ + backend/ etc. |
| **Test files** | 25+ | backend/tests/, frontend/src/**/__tests__/, e2e |

---

## 2. Directory structure (what we have)

```
NEWREUCIB/
├── .github/
│   └── workflows/
│       └── enterprise-tests.yml    # CI: lint, security (npm audit, pip-audit, gitleaks, SecurityAudit), frontend unit, backend integration, E2E
├── backend/
│   ├── agents/                     # Base agent, image/video/legal agents
│   ├── automation/                 # Schedule, executor, models, constants (user agents, run_agent, webhooks)
│   ├── tools/                      # file_agent, api_agent, browser_agent, deployment_operations, database_operations
│   ├── workers/                    # automation_worker (runs user agents)
│   ├── utils/                      # audit_log, rbac
│   ├── tests/                      # test_security, test_endpoint_mapping, test_webhook_flows, test_data_integrity, test_user_journeys, test_admin*, test_orchestration_e2e, etc.
│   ├── server.py                   # Main FastAPI app: auth, projects, build, agents, import, deploy, workspace files, dependency-audit, security-scan, Stripe, admin
│   ├── middleware.py               # RateLimit (global + strict auth/payment), SecurityHeaders, HTTPSRedirect, RequestTracker, RequestValidation
│   ├── security_audit.py           # Internal SecurityAudit (env, secrets, auth, compliance)
│   ├── orchestration.py            # DAG, phases, run_orchestration_v2
│   ├── agent_dag.py                # 120-agent DAG config
│   ├── agent_real_behavior.py      # Real behavior per agent (state, tool, artifact)
│   ├── real_agent_runner.py         # Run single agent with LLM
│   ├── project_state.py            # Load/save state (plan, stack, reports, tool_log)
│   ├── code_quality.py / quality.py
│   └── ...
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── pages/                  # LandingPage, Workspace, Dashboard, AgentMonitor, AgentsPage, Settings, Admin*, Pricing, Security, etc.
│   │   ├── components/             # PublicFooter, PublicNav, Layout, DeployButton, BuildProgress, QualityScore, ui/*
│   │   ├── services/               # Collaboration, CollaborativeEditing
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── utils/
│   └── e2e/                        # Playwright E2E (critical-user-journey)
├── docs/                           # All strategy, security, bring-code, compliance, launch audit, marketing
├── memory/                         # PRD
├── scripts/
├── ide-extensions/                 # vscode, jetbrains, sublime, vim
└── tests/                          # (if any at root)
```

---

## 3. Critical paths (all wired, no stubs in flow)

| Path | Backend | Frontend | Admin |
|------|---------|----------|--------|
| **Auth** | /api/auth/register, login, me, verify-mfa; Google OAuth; JWT + MFA | AuthPage, Layout (token) | — |
| **Projects** | POST/GET /api/projects; GET /api/projects/:id/state, /phases, /logs, /events/snapshot | Dashboard, ProjectBuilder, AgentMonitor | — |
| **Build** | /api/build/phases, /plan; orchestration_v2; DAG + 120 agents; build_kind web/mobile | Workspace, AgentMonitor (progress WS) | — |
| **Agents (user automations)** | /api/agents, /from-description, /agents/status/:id; automation/schedule, executor; webhook run | AgentsPage, Dashboard | — |
| **Import** | POST /api/projects/import (paste, zip_base64, git_url); GET workspace/files, workspace/file | Dashboard Import modal → Workspace ?projectId= | — |
| **Workspace** | GET/POST workspace files; /ai/security-scan, /accessibility-check, /validate-and-fix; project_id stored for scan | Workspace (editor, tools, chat) | — |
| **Deploy** | GET /api/projects/:id/deploy/zip; POST deploy/vercel, deploy/netlify | DeployButton, ExportCenter | — |
| **Tokens / billing** | /api/tokens/bundles, purchase, usage; POST /api/stripe/create-checkout-session; webhook | TokenCenter, Pricing, PaymentsWizard | Admin billing |
| **Security** | Rate limits (global + auth/payment); Security headers; HTTPS redirect (env); CORS from env; Security scan stored on project | Security page, Learn, Settings | — |
| **Admin** | /api/admin/dashboard, users, billing, analytics, legal | AdminDashboard, AdminUsers, AdminBilling, AdminAnalytics, AdminLegal | Full admin UI |

---

## 4. Connectivity summary

- **Frontend → Backend:** All API calls use `API` base (env); auth via Bearer token; ErrorBoundary logs to /api/errors/log.
- **Backend → DB:** MongoDB (projects, users, agents, project_logs, agent_status, shares, etc.).
- **Admin:** AdminRoute protects /app/admin/*; backend /api/admin/* requires admin role; dashboard, users, billing, analytics, legal all wired.
- **Webhooks:** Stripe (checkout completed); user agent webhooks (secret in query/header); run-internal for internal agents.
- **Real, not stubs:** Orchestration runs real agents (agent_real_behavior, real_agent_runner); automation executor runs steps (HTTP, run_agent, delay, etc.); import writes to project workspace; security scan stores result on project; dependency-audit runs npm/pip in project workspace.

---

## 5. How to verify (master audit)

Run:

1. **Backend tests:** `cd backend && pytest tests -v --tb=short`
2. **Frontend tests:** `cd frontend && npm test -- --watchAll=false`
3. **Security audit:** `cd backend && python -m security_audit`
4. **CI:** Push to main; `.github/workflows/enterprise-tests.yml` runs lint, security (npm audit, pip-audit, gitleaks, SecurityAudit), frontend unit, backend integration, E2E.

See **CRUCIBAI_MASTER_BUILD_PROMPT.md** and **docs/LAUNCH_SEQUENCE_AUDIT.md** for the full audit checklist.
