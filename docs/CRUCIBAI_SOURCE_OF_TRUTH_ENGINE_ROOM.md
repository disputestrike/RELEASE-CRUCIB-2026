# CrucibAI — Source of Truth / Engine Room / Data Room

**Purpose:** Single top-tier document for investors, new team, and developers. Every feature, function, how it works, where it is, why it beats competitors, full tech spec, architecture, developer notes — nothing hidden.

**Last updated:** February 2026  
**Generated from:** MASTER_SOURCE_OF_TRUTH_PROMPT.md (implemented)

---

## 1. What & Why

### What CrucibAI Is

- **Product:** Platform where you describe what you want in plain language and get production-ready web apps, mobile apps (Expo + store pack), and automations (schedule or webhook). One product: build apps and run automations using the **same 120-agent AI swarm**. No code required.
- **One-liner:** *"The same AI that builds your app runs inside your automations."*
- **Positioning:** "Inevitable AI" — describe on Monday, live by Friday; plan-first, visible, retry; outcomes are inevitable when you describe and we build.

### Why We Built It

- **Problem:** Teams need apps, landing pages, funnels, and automations. They either code manually, hire devs, or glue multiple tools (app builder + Zapier + copywriter). No single platform connects app building and automation with one AI.
- **Solution:** One platform: describe once → we build the app and the automations. The AI that builds your site also runs your daily digest, lead follow-up, and content pipeline (via `run_agent`).
- **Unique advantage:** We are the **only** platform where (1) you build apps with a 120-agent DAG and (2) you create user automations that **invoke those same agents** as steps. N8N/Zapier have AI steps that call external APIs; they don't have an app-building swarm. Manus/Bolt build apps but don't let you create automations that call their agents. We have both and the bridge (`run_agent`).

### Who It's For

Marketers, agencies, product teams, and devs who want: landing pages, funnels, blogs, SaaS, mobile apps, and automations (daily digest, lead nurture, content refresh) — all from one platform, in days not weeks.

### Branding

- **CrucibAI:** Brand name; "crucible" (where things are forged) + AI.
- **Inevitable AI:** Tagline — outcomes are inevitable when you describe and we build.
- **Monday→Friday:** "Describe your idea on Monday. By Friday you have a live site, automations, and the copy to run ads. Same AI that builds your app runs your workflows."
- **Ads:** "You run the ads; we built the stack." (Option A — we do not have native Meta/Google Ads posting.)

---

## 2. Full Feature List (What / Function / How / Where / Beats Competitor)

| Feature | What it does | Backend / API | Frontend (route + component) | How it beats competitors |
|--------|---------------|----------------|------------------------------|---------------------------|
| **Auth** | Register, login, MFA, Google OAuth | `/api/auth/register`, `/login`, `/me`, `/verify-mfa`, `/auth/google`, `/auth/google/callback` | `/auth` → AuthPage | JWT + MFA + OAuth; no stub auth. |
| **Projects** | Create, list, get project; state, phases, logs | `/api/projects`, `/api/projects/{id}`, `/state`, `/phases`, `/logs`, `/events/snapshot` | `/app` index → Dashboard; `/app/projects/new` → ProjectBuilder; `/app/projects/:id` → AgentMonitor | Full state + phases + retry; Cursor/Manus don't expose full build state. |
| **Build** | Plan → DAG → 120 agents → real files/state | `/api/build/plan`, `/api/build/phases`; orchestration_v2; agent_dag.py, real_agent_runner | Workspace (plan submit); AgentMonitor (phases, progress, WebSocket) | 120 true agents (state/artifact/tool); Manus has fewer actors; we have named roles + real behavior. |
| **Workspace** | Edit files, Sandpack preview, chat, voice, tools | `/api/workspace/files`, `/api/ai/*`, `/api/voice/transcribe`, `/api/ai/security-scan`, `/api/ai/validate-and-fix` | `/app/workspace` → Workspace.jsx | In-browser preview (Sandpack); security scan, validate-and-fix; API key nudge + Try these. |
| **AgentMonitor** | Phases, current agent, progress %, tokens, Build state, retry, View Live | WebSocket `/ws/projects/{id}/progress`; `/api/projects/{id}/phases`, `/retry-phase`, `/agents/status/{id}` | `/app/projects/:id` → AgentMonitor | Per-phase, per-agent tokens; quality score; Build state panel (plan, requirements, stack, tool_log); retry phase. |
| **Agents (user automations)** | Schedule (cron) or webhook; executor: HTTP, email, Slack, run_agent, approval | `/api/agents`, `/api/agents/from-description`, `/api/agents/webhook/{id}`; automation/executor.py, schedule.py, workers | `/app/agents` → AgentsPage | run_agent = same 120-agent swarm as build; N8N/Zapier don't have app-building swarm. |
| **Import** | Paste, ZIP, Git URL → project workspace | `/api/projects/import` (paste, zip_base64, git_url) | Dashboard Import modal → Workspace | One flow into workspace; then build or edit. |
| **Deploy** | ZIP download, Vercel, Netlify, GitHub export | `/api/projects/{id}/deploy/zip`, `/api/export/vercel`, `/netlify`, `/github` | DeployButton, ExportCenter | Multiple export targets; live_url after Vercel/Netlify. |
| **Tokens & billing** | Bundles, purchase, usage, Stripe checkout | `/api/tokens/bundles`, `/purchase`, `/usage`; `/api/stripe/create-checkout-session`, `/stripe/webhook` | TokenCenter, Pricing, PaymentsWizard; Admin billing | Stripe wired; TokenCenter shows bundles/history; admin billing. |
| **Settings** | API keys, env vars, workspace env | `/api/workspace/env` GET/POST | `/app/settings` → Settings | Central keys + env; first-build nudge to add keys. |
| **Share** | Share project via token | Share API + `/share/:token` | ShareView | Public view without login. |
| **Templates / Patterns / Prompts** | Pre-built templates, patterns, prompt library | `/api/examples`, `/api/templates` (as used) | TemplatesGallery, PatternLibrary, PromptLibrary, ExamplesGallery | Fork examples; try these prompts. |
| **Learn / Docs / Tutorials / Shortcuts** | Learning content, shortcuts cheatsheet | Static or API as needed | LearnPublic, LearnPanel, DocsPage, TutorialsPage, ShortcutCheatsheet | Onboarding and power-user support. |
| **Pricing / Enterprise** | Public pricing, enterprise contact | `/api/tokens/bundles`, `/api/enterprise/contact` | Pricing, Enterprise | Public pricing page; enterprise form. |
| **Security / Legal** | Security page, Privacy, Terms, AUP, DMCA, Cookies | — | Security, Privacy, Terms, Aup, Dmca, Cookies | Trust and compliance pages. |
| **Admin** | Dashboard, users, billing, analytics, legal | `/api/admin/dashboard`, `/users`, `/billing`, `/analytics`, `/legal/*` | `/app/admin/*` → AdminDashboard, AdminUsers, AdminBilling, AdminAnalytics, AdminLegal | Full admin UI; RBAC. |
| **Audit log** | User action audit trail | `/api/audit/logs`, `/audit/logs/export` | `/app/audit-log` → AuditLog | Compliance and forensics. |
| **Blog / Benchmarks** | Blog posts, benchmark report | — | Blog, Benchmarks | Marketing and proof. |
| **ManusComputer** | Step/token/thinking widget in Workspace | — | ManusComputer.jsx (in Workspace) | Visual "computer" UX; can be wired to real build progress. |
| **Quality score** | 0–100 score after build | Stored in project; code_quality.score_generated_code | AgentMonitor, Dashboard badge | Visibility of build quality; retry if low. |
| **Command palette / Shortcuts** | Ctrl+K, shortcuts | — | Layout, ShortcutCheatsheet | Power-user UX. |

---

## 3. Full Tech Spec & Architecture

### Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.x, Motor (async MongoDB), uvicorn |
| Frontend | React, CRACO, Radix UI, Monaco editor, Sandpack (CodeSandbox in-browser) |
| DB | MongoDB (projects, users, agents, project_logs, agent_status, shares, etc.) |
| Payments | Stripe (checkout session, webhook signature verified) |
| Deploy | Vercel, Netlify, ZIP download, GitHub export |
| Infra | Railway-ready (Dockerfile, railway.json) |

### Scale (approximate)

| Metric | Value |
|--------|--------|
| Backend Python files | ~73 |
| Frontend JS/JSX files | ~117 |
| server.py | ~5,560 lines |
| Total primary code | ~33,600+ (Py + JS/JSX) |
| Documentation (.md) | 150+ |
| Test files | 25+ (backend tests, frontend __tests__, e2e) |

### Directory Structure (key paths)

```
NEWREUCIB/
├── .github/workflows/
│   └── enterprise-tests.yml    # CI: lint, security, frontend unit, backend integration, E2E
├── backend/
│   ├── server.py               # Main FastAPI app; all /api/* routes
│   ├── orchestration.py        # DAG, phases, run_orchestration_v2
│   ├── agent_dag.py            # 120-agent DAG config (depends_on, system_prompt)
│   ├── agent_real_behavior.py  # STATE_WRITERS, ARTIFACT_PATHS, TOOL_RUNNER_STATE_KEYS
│   ├── real_agent_runner.py    # Run single agent with LLM; tools
│   ├── project_state.py        # Load/save workspace/<project_id>/state.json
│   ├── tool_executor.py        # execute_tool(file, run, api, browser, db)
│   ├── middleware.py           # Rate limit, security headers, CORS, validation
│   ├── security_audit.py       # Internal SecurityAudit (env, secrets, auth)
│   ├── agents/                 # Base + image/video/legal agents
│   ├── automation/             # schedule.py, executor.py, models (run_agent, webhooks)
│   ├── tools/                  # file_agent, api_agent, browser_agent, deployment, database
│   ├── workers/                # automation_worker (polls and runs user agents)
│   ├── utils/                  # audit_log, rbac
│   └── tests/                  # test_security, test_endpoint_mapping, test_webhook_flows, etc.
├── frontend/
│   ├── src/
│   │   ├── pages/              # All route components (see Section 4)
│   │   ├── components/         # Layout, PublicNav, ManusComputer, BuildProgress, ui/*
│   │   ├── stores/             # useLayoutStore, useTaskStore
│   │   ├── services/, hooks/, lib/
│   └── e2e/                    # Playwright (critical-user-journey, single-source-of-truth)
├── docs/                       # All strategy, security, compliance, launch, marketing
├── ide-extensions/             # vscode, jetbrains, sublime, vim
└── scripts/                    # run-enterprise-tests.ps1, .sh
```

### Data Flow

- **Frontend → Backend:** All API calls use `API = ${REACT_APP_BACKEND_URL}/api` (default `http://localhost:8000/api`). Auth: `Authorization: Bearer <token>`. ErrorBoundary logs to `/api/errors/log`.
- **Backend:** `api_router = APIRouter(prefix="/api")`; all routes under `/api/*`. WebSocket at `/ws/projects/{id}/progress` (no `/api` prefix).
- **Backend → DB:** Motor (MongoDB); collections: projects, users, agents, project_logs, agent_status, shares, etc.
- **Build flow:** Client calls `/api/build/plan` → orchestration_v2 runs DAG → each agent via real_agent_runner → run_agent_real_behavior (state/artifact/tool) → progress via WebSocket.

---

## 4. Every Route & Where in the App

### Frontend Routes (App.js)

| Path | Component | Protection |
|------|-----------|------------|
| `/` | LandingPage | Public |
| `/auth` | AuthPage | Public |
| `/builder` | Builder | Public |
| `/workspace` | Workspace | ProtectedRoute |
| `/share/:token` | ShareView | Public |
| `/privacy`, `/terms`, `/security`, `/aup`, `/dmca`, `/cookies`, `/about` | Privacy, Terms, Security, Aup, Dmca, Cookies, About | Public |
| `/pricing`, `/enterprise`, `/features` | Pricing, Enterprise, Features | Public |
| `/templates`, `/patterns`, `/learn`, `/docs`, `/documentation`, `/tutorials`, `/shortcuts`, `/prompts`, `/benchmarks`, `/blog`, `/blog/:slug` | TemplatesPublic, PatternsPublic, LearnPublic, DocsPage, TutorialsPage, ShortcutsPublic, PromptsPublic, Benchmarks, Blog | Public |
| `/app` | Layout (shell) | ProtectedRoute |
| `/app` (index) | Dashboard | ProtectedRoute |
| `/app/workspace` | Workspace | ProtectedRoute |
| `/app/projects/new` | ProjectBuilder | ProtectedRoute |
| `/app/projects/:id` | AgentMonitor | ProtectedRoute |
| `/app/tokens`, `/app/exports` | TokenCenter, ExportCenter | ProtectedRoute |
| `/app/patterns`, `/app/templates`, `/app/prompts`, `/app/learn`, `/app/env`, `/app/shortcuts`, `/app/payments-wizard`, `/app/examples`, `/app/generate` | PatternLibrary, TemplatesGallery, PromptLibrary, LearnPanel, EnvPanel, ShortcutCheatsheet, PaymentsWizard, ExamplesGallery, GenerateContent | ProtectedRoute |
| `/app/agents`, `/app/agents/:id` | AgentsPage | ProtectedRoute |
| `/app/settings`, `/app/audit-log` | Settings, AuditLog | ProtectedRoute |
| `/app/admin`, `/app/admin/users`, `/app/admin/users/:id`, `/app/admin/billing`, `/app/admin/analytics`, `/app/admin/legal` | AdminDashboard, AdminUsers, AdminUserProfile, AdminBilling, AdminAnalytics, AdminLegal | AdminRoute |

### Backend API Routes (server.py) — Summary

- **Auth:** POST /auth/register, /auth/login, /auth/verify-mfa, GET /auth/me, /auth/google, /auth/google/callback.
- **MFA:** POST /mfa/setup, /mfa/verify, /mfa/disable, GET /mfa/status, POST /mfa/backup-code/use.
- **Projects:** GET/POST /projects; GET /projects/{id}/state, /phases, /logs; POST /projects/import; POST /projects/{id}/retry-phase.
- **Build:** GET /build/phases; POST /build/plan (triggers orchestration).
- **Agents (user):** GET/POST /agents; GET /agents/status/{project_id}, /agents/templates; POST /agents/from-description, /agents/webhook/{agent_id}; many POST /agents/run/* (planner, requirements-clarifier, stack-selector, backend-generate, etc.); POST /agents/run-internal.
- **Workspace / AI:** POST /ai/chat, /ai/chat/stream, /ai/analyze, /voice/transcribe, /ai/validate-and-fix, /ai/security-scan, /ai/image-to-code; GET /ai/chat/history/{session_id}; POST /files/analyze, /export/zip, /export/github, /export/deploy.
- **Tokens / Stripe:** GET /tokens/bundles; POST /tokens/purchase; GET /tokens/history, /tokens/usage; POST /stripe/create-checkout-session, /stripe/webhook.
- **Referrals:** GET /referrals/code, /referrals/stats.
- **Audit:** GET /audit/logs, /audit/logs/export.
- **Admin:** GET /admin/dashboard, /admin/users, /admin/billing, /admin/analytics, /admin/legal (and related).
- **Other:** POST /enterprise/contact; POST /generate/doc, /generate/slides, /generate/sheets; POST /rag/query, /search.

WebSocket: `GET /ws/projects/{project_id}/progress` — progress events for AgentMonitor/BuildProgress.

---

## 5. 120 Agents (Algorithm & Real Behavior)

- **Source files:** `backend/agent_dag.py` (DAG definition), `backend/agent_real_behavior.py` (behavior map), `backend/real_agent_runner.py` (run one agent with LLM + tools).
- **Flow:** Plan → Requirements → Stack Selector → Frontend/Backend/DB/Design/Content/Deploy phases. Each agent has `depends_on` and `system_prompt`. Execution is DAG-ordered with parallel phases.
- **Real behavior (no prompt-only):**
  - **State writers:** 18+ agents write to `workspace/<project_id>/state.json` (plan, requirements, stack, design_spec, brand_spec, memory_summary, tool_log, etc.).
  - **Artifact writers:** 80+ agents call `execute_tool(project_id, "file", { action: "write", path, content })` — real files (e.g. README.md, src/App.jsx, schema.sql).
  - **Tool runners:** Test Executor, Security Checker, UX Auditor, Performance Analyzer, Code Review, etc. run allowlisted commands; results stored in state or tool_log.
- **Verification:** `backend/verify_120_agents.py` — every DAG agent has a mapping. Matrix: `AGENTS_REAL_BEHAVIOR_MATRIX.md`.
- **User automations:** Executor in `automation/executor.py` runs steps: HTTP, email, Slack, **run_agent** (same swarm by name), approval_required. `run_agent` is the bridge: same 120-agent DAG invokable as a step in user automations.

---

## 6. Integrations & Exports

| Integration | How | Where in code |
|-------------|-----|----------------|
| MongoDB | Motor; projects, users, agents, logs | server.py, all route handlers |
| Stripe | Checkout session, webhook (signature verified) | /api/stripe/* |
| Vercel / Netlify / GitHub | Deploy or export; token in Settings | /api/export/*, deploy endpoints |
| ZIP | GET /api/projects/{id}/deploy/zip | server.py |
| Resend / SendGrid | Email action in executor | automation/executor.py; env keys |
| Slack | Webhook or chat.postMessage in executor | automation/executor.py |
| OpenAI / Anthropic | LLM for agents; keys in env or user Settings | real_agent_runner, orchestration |
| Google OAuth | /api/auth/google, callback | server.py |

---

## 7. Competitive Position (Why We Win)

- **vs Manus/Bolt:** We have 120 named agents with defined real behavior (state/artifact/tool); user automations can call same swarm via run_agent. They build apps but don't expose automations that invoke their build agents.
- **vs N8N/Zapier:** They have workflow automation; we have app building + automation with the **same** AI. run_agent step = our build swarm.
- **vs Cursor/Copilot:** They are IDE-first; we are app-outcome-first (describe → full app + automations). We lead on build/agent visibility (AgentMonitor, Build state, per-agent tokens, quality score).
- **Evidence:** RATE_RANK_TOP10, TOP20, TOP50 — CrucibAI #1, 10.0/10. Compliance matrix green; 5-layer production validation in CI; proof scripts pass when backend + DB + keys set.

---

## 8. Ratings & Rankings (The Truth)

- **Overall 10/10** (RATE_RANK_COMPARE.md): Reliability, Build flow, Deploy, Agents, Tokens & billing, UX, Compliance, Docs & onboarding all at 10.
- **Evidence:** Quality score in AgentMonitor + Dashboard; per-step tokens; API key nudge + Try these; Pricing; Enterprise; Deploy UX; 5-layer tests in CI.
- **What was left and done:** AgentMonitor (phases, event timeline, Build state, retry, Open in Workspace); quality score visible; tokens per build/agent; API key prompt; first-run improvements.

---

## 9. Where in the App (Quick Map)

- **Public:** /, /auth, /pricing, /features, /templates, /learn, /blog, /security, /privacy, /terms, etc.
- **App (logged-in):** /app → Dashboard; /app/workspace, /app/projects/:id (AgentMonitor), /app/tokens, /app/settings, /app/agents, etc.
- **Admin:** /app/admin, /app/admin/users, /app/admin/billing, /app/admin/analytics, /app/admin/legal.
- **Layout:** Layout.jsx wraps /app routes; sidebar; health check (GET /api/health) — "Backend unavailable" if fail; Retry in footer.

---

## 10. Developer Notes & Documentation

- **Run locally:** Backend: `cd backend && python -m uvicorn server:app --host 0.0.0.0 --port 8000` (or run_local.py). Frontend: `cd frontend && npm start` (default 3000). Set `REACT_APP_BACKEND_URL=http://localhost:8000` if needed.
- **Verify:** Backend: `cd backend && pytest tests -v --tb=short`. Frontend: `cd frontend && npm test -- --watchAll=false`. Security: `cd backend && python -m security_audit`. CI: `.github/workflows/enterprise-tests.yml` (lint, security, frontend unit, backend integration, E2E).
- **Key files to read:** server.py, orchestration.py, agent_dag.py, agent_real_behavior.py, real_agent_runner.py, project_state.py, tool_executor.py, automation/executor.py; Workspace.jsx, AgentMonitor, Dashboard; BACKEND_FRONTEND_CONNECTION.md, docs/CODEBASE_SOURCE_OF_TRUTH.md.
- **Endpoint map:** See BACKEND_FRONTEND_CONNECTION.md (frontend call → backend route). WebSocket: `ws://<BACKEND_URL>/ws/projects/{id}/progress`.
- **"Backend unavailable":** Layout does GET /api/health; if it fails, footer shows message. Fix: start backend on 8000; or set REACT_APP_BACKEND_URL and restart frontend; click Retry.

---

## 11. Engine Room & Data Room

- **Scale:** ~33,600+ lines primary code; 120-agent DAG; 73+ backend files, 117+ frontend files; 150+ docs.
- **Critical paths:** Auth, projects, build, agents, import, workspace, deploy, tokens, admin — all wired. No stubs in build, deploy, agents, import, tokens, admin.
- **Placeholders (intentional):** MONGO_URL/DB_NAME for deploy test; Layout image slots (data-image-slot); template HTTP targets (e.g. httpbin) in some agent templates.
- **Gaps:** Ads: Option A — "You run the ads; we built the stack." No native Meta/Google Ads action. Option C (native ad actions) = post-launch roadmap.
- **Security:** Rate limiting (global + strict auth/payment); security headers (CSP, HSTS, etc.); request validation; CORS from env; JWT + MFA; Stripe webhook signature verification; security_audit script.
- **CI:** Lint, npm audit, pip-audit, gitleaks, SecurityAudit, frontend unit, backend integration, E2E (Playwright).

---

## 12. Roadmaps & What's Left

- **Implemented:** Full build flow, 120 agents with real behavior, user automations (schedule, webhook, run_agent), import, deploy (ZIP, Vercel, Netlify, GitHub), tokens/Stripe, admin, audit log, quality score, AgentMonitor, API key nudge, Try these, Pricing, Enterprise.
- **Placeholders / optional:** True SSE streaming; one-click deploy with live URL in product; per-step tokens in Agents panel; first-run tour; outcome guarantee (no charge if not runnable) — roadmap.
- **Not built (by design):** Native Meta/Google Ads posting — messaging is Option A.

---

## 13. ManusComputer Style & UX

- **ManusComputer.jsx:** Widget in Workspace: step counter, "thinking," token bar. Can be wired to real build (versions/progress from WebSocket); currently may use local state for demo.
- **AgentMonitor:** Phases, event timeline, Build state panel (plan, requirements, stack, tool_log), per-agent tokens, quality score, retry phase, Open in Workspace, View Live (when live_url set).
- **Command palette / Shortcuts:** Ctrl+K style palette; ShortcutCheatsheet page; model selector, Tools tab in Workspace.

---

## 14. Incorporated Documents (Source of Truth)

This doc pulls from and aligns with:

- docs/CODEBASE_SOURCE_OF_TRUTH.md  
- docs/FULL_SCOPE_INVESTOR_ENGINE_ROOM.md  
- BACKEND_FRONTEND_CONNECTION.md  
- TRUTH_120_AGENTS.md  
- RATE_RANK_COMPARE.md, RATE_RANK_TOP10.md, RATE_RANK_TOP20.md, RATE_RANK_TOP50.md  
- AGENTS_REAL_BEHAVIOR_MATRIX.md, FULL_PLAN_ALL_120_AGENTS.md  
- docs/LAUNCH_SEQUENCE_AUDIT.md, CRUCIBAI_MASTER_BUILD_PROMPT.md  
- docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md, docs/MESSAGING_AND_BRAND_VOICE.md  
- OUR_SANDBOX_PREVIEW_AND_MANUS_STYLE.md  
- TESTING.md, docs/CRUCIBAI_*.md (implementation, roadmap, competitive)

---

## 15. Corrections & Gaps (Catch All)

- **ManusComputer:** Confirm whether currently wired to real build progress or local mock; doc states "can be wired."
- **4 auth tests:** Some tests skip when register returns 500 (Motor/event loop); run with live backend + CRUCIBAI_API_URL for full suite.
- **5 database agent tests:** Skip when asyncpg not installed (optional).
- **Ads:** Explicitly not built; Option A messaging. Any investor deck should say "you run the ads; we built the stack."
- **Outcome guarantee:** Not implemented; optional roadmap.

---

**End of Source of Truth / Engine Room / Data Room.**

To regenerate or extend: run **MASTER_SOURCE_OF_TRUTH_PROMPT.md** and merge updates into this file.

**Did the doc miss anything?** See **docs/CRUCIBAI_SOURCE_BIBLE_WHAT_WAS_MISSING_AND_FIXES.md** for the full list of gaps, exact fixes (including frontend double-/api), and **how to get everything** (regenerate bible, merge, export to PDF).
