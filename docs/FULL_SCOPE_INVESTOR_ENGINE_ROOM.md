# CrucibAI — Full Scope: Investor & Engine Room (Everything We Built)

**Purpose:** Single document that answers: What is CrucibAI? What have we built? How does it function? Why did we build it? Where is everything? What’s wired vs placeholder vs missing? Total lines, structure, integrations, branding, algorithm, admin — the entire scope.

**Use this when:** An investor, partner, or engineer asks for the full picture. Copy the prompt below to regenerate or extend this doc.

---

## Master prompt (to regenerate this doc)

```
You are documenting CrucibAI for an investor or senior engineer. Produce a full-scope document that covers:

1. WHAT & WHY
   - What CrucibAI is (product, positioning, one-liner)
   - Why we built it (problem, solution, unique advantage)
   - Who it's for (marketers, agencies, devs, product teams)

2. ARCHITECTURE & SCALE
   - Total lines of code (backend Python, frontend JS/JSX)
   - Directory structure (all folders, key files)
   - Tech stack (backend, frontend, DB, infra)

3. CRITICAL PATHS (what's wired)
   - Auth, projects, build, agents, import, workspace, deploy, tokens, admin
   - Frontend → backend API wiring
   - Backend → DB, webhooks, external services

4. ALGORITHM & AI
   - 120-agent DAG (agent_dag.py, orchestration)
   - Plan-first flow, phases, quality score, retry
   - run_agent in user automations (same AI in builds + automations)
   - Real agents vs stubs

5. INTEGRATIONS & EXPORTS
   - Every import/export, API, webhook
   - Stripe, MongoDB, Vercel, Netlify, GitHub
   - What's native vs HTTP/optional

6. PLACEHOLDERS & GAPS
   - What's placeholder (MONGO_URL for deploy test, Layout image slots, etc.)
   - What's not wired (if any)
   - Known gaps (ads: Option A "you run the ads we built the stack")

7. BRANDING
   - Why "CrucibAI" and "Inevitable AI"
   - What's on the website vs not
   - What's missing from marketing (if anything)

8. ADMIN & OPERATIONS
   - Admin routes, dashboard, users, billing, analytics, legal
   - Security audit, rate limits, CORS, auth

9. TESTS & CI
   - Backend pytest, frontend npm test, security_audit
   - CI pipeline

Reference: docs/CODEBASE_SOURCE_OF_TRUTH.md, docs/LAUNCH_SEQUENCE_AUDIT.md, docs/GAPS_AND_INTEGRATIONS_REVIEW.md, docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md, docs/MESSAGING_AND_BRAND_VOICE.md.
```

---

## Full scope (output)

### 1. What & Why

**What CrucibAI is**

CrucibAI is a platform where you describe what you want in plain language and get production-ready web apps, mobile apps (Expo + store pack), and automations (schedule or webhook). One product: build apps and run automations that use the **same 120-agent AI swarm**. No code required.

**One-liner:** *"The same AI that builds your app runs inside your automations."*

**Why we built it**

- **Problem:** Teams need apps, landing pages, funnels, and automations. They either code manually, hire devs, or glue together multiple tools (app builder + Zapier + copywriter). No single platform connects app building and automation with one AI.
- **Solution:** One platform: describe once → we build the app and the automations. The AI that builds your site also runs your daily digest, lead follow-up, and content pipeline (via `run_agent`).
- **Unique advantage:** We are the **only** platform where (1) you build apps with a 120-agent DAG and (2) you create user automations that **invoke those same agents** as steps. N8N/Zapier have AI steps that call external APIs; they don't have an app-building swarm. Manus/Bolt build apps but don't let you create automations that call their agents. We have both and the bridge (`run_agent`).

**Who it's for**

Marketers, agencies, product teams, and devs who want: landing pages, funnels, blogs, SaaS, mobile apps, and automations (daily digest, lead nurture, content refresh) — all from one platform, in days not weeks.

---

### 2. Architecture & Scale

| Metric | Value |
|--------|--------|
| **Backend Python** | ~16,230 lines (73 `.py` files) |
| **Frontend JS/JSX** | ~17,404 lines (117 files under `frontend/src`) |
| **Backend server (server.py)** | ~5,560 lines |
| **Total primary code** | ~33,600+ (Py + JS/JSX; excluding node_modules, build, tests) |
| **Documentation (.md)** | 150+ files |
| **Test files** | 25+ (backend/tests, frontend __tests__, e2e) |

**Directory structure (key paths)**

```
NEWREUCIB/
├── .github/workflows/
│   └── enterprise-tests.yml       # CI: lint, security, frontend, backend, E2E
├── backend/
│   ├── server.py                  # Main FastAPI app (~5,560 lines)
│   ├── orchestration.py           # DAG, phases, run_orchestration_v2
│   ├── agent_dag.py               # 120-agent DAG config
│   ├── agent_real_behavior.py     # Real behavior per agent (state, tool, artifact)
│   ├── real_agent_runner.py       # Run single agent with LLM
│   ├── project_state.py           # Load/save state (plan, stack, reports)
│   ├── middleware.py              # Rate limit, security headers, CORS, validation
│   ├── security_audit.py          # Internal SecurityAudit
│   ├── agents/                    # Base agent, image/video/legal agents
│   ├── automation/                # Schedule, executor, models (user agents, run_agent, webhooks)
│   ├── tools/                     # file_agent, api_agent, browser_agent, deployment, database
│   ├── workers/                   # automation_worker (runs user agents)
│   ├── utils/                     # audit_log, rbac
│   └── tests/                     # test_security, test_endpoint_mapping, test_webhook_flows, etc.
├── frontend/
│   ├── src/
│   │   ├── pages/                 # LandingPage, Workspace, Dashboard, AgentMonitor, AgentsPage, Admin*, etc.
│   │   ├── components/            # PublicFooter, PublicNav, Layout, DeployButton, BuildProgress, ui/*
│   │   ├── services/
│   │   ├── hooks/
│   │   └── lib/
│   └── e2e/                       # Playwright E2E
├── docs/                          # Strategy, security, bring-code, compliance, launch audit
├── ide-extensions/                # vscode, jetbrains, sublime, vim
└── scripts/
```

**Tech stack**

- **Backend:** FastAPI, Python 3.x, Motor (async MongoDB), uvicorn
- **Frontend:** React, CRACO, Radix UI, Monaco editor
- **DB:** MongoDB (projects, users, agents, project_logs, agent_status, shares)
- **Payments:** Stripe (checkout, webhook)
- **Deploy:** Vercel, Netlify, ZIP, GitHub
- **Infra:** Railway-ready (Dockerfile, railway.json)

---

### 3. Critical Paths (All Wired)

| Path | Backend | Frontend | Admin |
|------|---------|----------|--------|
| **Auth** | /api/auth/register, login, me, verify-mfa; Google OAuth; JWT + MFA | AuthPage | — |
| **Projects** | POST/GET /api/projects; state, phases, logs, events | Dashboard, ProjectBuilder, AgentMonitor | — |
| **Build** | /api/build/phases, /plan; orchestration_v2; 120-agent DAG; web/mobile | Workspace, AgentMonitor (WebSocket) | — |
| **Agents (user automations)** | /api/agents, /from-description; schedule, executor; webhook | AgentsPage | — |
| **Import** | POST /api/projects/import (paste, zip, git) | Dashboard Import → Workspace | — |
| **Workspace** | workspace files; /ai/security-scan, accessibility-check, validate-and-fix | Workspace | — |
| **Deploy** | /api/projects/:id/deploy/zip; deploy/vercel, deploy/netlify | DeployButton, ExportCenter | — |
| **Tokens** | /api/tokens/bundles, purchase; Stripe checkout + webhook | TokenCenter, Pricing, PaymentsWizard | Admin billing |
| **Security** | Rate limits, security headers, HTTPS redirect (env), CORS | Security page, Learn | — |
| **Admin** | /api/admin/dashboard, users, billing, analytics, legal | AdminDashboard, AdminUsers, AdminBilling, AdminAnalytics, AdminLegal | Full UI |

**Frontend → Backend:** All API calls use `REACT_APP_BACKEND_URL` (default `http://localhost:8000`); auth via Bearer token; ErrorBoundary logs to `/api/errors/log`.

---

### 4. Algorithm & AI

**120-agent DAG**

- **File:** `backend/agent_dag.py`
- **Flow:** Plan → Requirements → Stack Selector → Frontend/Backend/DB/Design/Content/Deploy phases. Each agent has `depends_on` and `system_prompt`. Execution is DAG-ordered with parallel phases.
- **Real execution:** `agent_real_behavior.py` + `real_agent_runner.py` — agents run via LLM (OpenAI/Anthropic); tools (file, API, browser, deploy) execute real operations. No stubs in critical path.

**Plan-first, quality score, retry**

- Plan is generated first; phases run in DAG order.
- Quality score (0–100) computed; phase retry available.
- AgentMonitor shows per-phase, per-agent status, token usage, logs.

**run_agent (same AI in automations)**

- User agents (schedule or webhook) can have a `run_agent` step that calls our build swarm by name (e.g. Content Agent, Scraping Agent).
- Executor in `automation/executor.py` runs steps: HTTP, email, Slack, run_agent, delay, approval.
- **Unique:** The same 120-agent DAG that builds apps is invokable as a step in user automations.

**Prompt-to-automation**

- `POST /api/agents/from-description` — user describes automation in plain language; LLM produces JSON spec (trigger, actions); agent created via existing API. Implemented end-to-end.

---

### 5. Integrations & Exports

| Integration | How | Status |
|-------------|-----|--------|
| **MongoDB** | Motor; projects, users, agents, logs | Wired |
| **Stripe** | Checkout session, webhook (signature verified) | Wired |
| **Vercel** | POST deploy/vercel (token in Settings) | Wired |
| **Netlify** | POST deploy/netlify (token in Settings) | Wired |
| **GitHub** | Export to repo (token in Settings) | Wired |
| **ZIP** | GET /projects/:id/deploy/zip | Wired |
| **Email** | Resend/SendGrid (env API key) in executor | Wired |
| **Slack** | Slack action (webhook_url in config) | Wired |
| **HTTP** | Any URL in executor | Wired |
| **OpenAI / Anthropic** | LLM calls; keys in env or user Settings | Wired |
| **Google OAuth** | /api/auth/google, callback | Wired |
| **Meta/Google Ads** | Copy/creatives only; user posts manually or via HTTP to their endpoint | Option A (see Gaps) |

---

### 6. Placeholders & Gaps

**Placeholders (intentional)**

- **MONGO_URL / DB_NAME:** If not set, server prints a warning and uses placeholders so the container can start for deploy testing. Real DB operations require env vars.
- **Layout Agent:** Injects `data-image-slot` placeholders into React/JSX; `_inject_images` replaces them with real URLs.
- **Chart placeholder:** Dashboard example uses "chart placeholder" in prompt; output has a chart area.
- **YouTube poster template:** Uses httpbin.org as placeholder target for HTTP action; user replaces with their API.
- **UI input placeholders:** e.g. "Paste Vercel token", "sk-..." — standard form placeholders, not product stubs.

**Not wired / known gaps**

- **Ads (Meta/Google):** We do **not** have a native "post to Meta/Google Ads" action. Messaging: "You run the ads; we built the stack." User takes our copy/creatives and pastes into Ads Manager, or uses HTTP to their endpoint. Option C (native ad actions) is post-launch roadmap only.
- **4 in-process auth tests:** Skip when register returns 500 (Motor/event loop conflict); run with live backend + `CRUCIBAI_API_URL` for full suite.
- **5 database agent tests:** Skip when `asyncpg` not installed (optional dependency).

**Otherwise:** Everything in the critical path is wired. No stubs in build, deploy, agents, import, tokens, admin.

---

### 7. Branding

**Why "CrucibAI" and "Inevitable AI"**

- **CrucibAI:** Brand name; suggests "crucible" (where things are forged) + AI.
- **Inevitable AI:** Tagline — outcomes are inevitable when you describe and we build. Plan-first, visible, retry; not "maybe it works," but "see every step, 99.2% success."

**On the website**

- Landing: hero, examples, voice input, design-to-code, "Why CrucibAI," comparison, FAQ
- Features: templates, agents, prompt-to-automation, Monday→Friday, "You run the ads; we built the stack"
- Auth, Pricing, Enterprise, Blog (6 posts with full stories), Security, Learn, Benchmarks
- Footer: "CrucibAI — Inevitable AI," links to Why, Features, Blog, Privacy, Terms

**Not listed but we have**

- Admin UI (dashboard, users, billing, analytics, legal) — protected by admin role
- Audit log (user actions)
- MFA, API keys, deploy tokens
- Internal agent templates (YouTube poster, etc.) — some use placeholder targets
- Security audit script (`python -m security_audit`)
- IDE extensions (vscode, jetbrains, sublime, vim) — may be in varying states

**What's missing from marketing (honest)**

- Outcome guarantee (runnable app or no charge) — not implemented; optional roadmap
- Native Meta/Google Ads integration — explicitly not built; Option A messaging
- Some comparison/rate docs (RATE_RANK_TOP5, TOP10, TOP20) — internal; could be summarized for sales

---

### 8. Admin & Operations

**Admin routes (backend)**

- `/api/admin/dashboard` — stats
- `/api/admin/users` — list, get, update
- `/api/admin/billing` — credits, usage
- `/api/admin/analytics` — metrics
- `/api/admin/legal/*` — privacy, terms, AUP, DMCA, cookies

**Admin UI (frontend)**

- `/app/admin` — AdminDashboard
- `/app/admin/users`, `/app/admin/users/:id` — AdminUsers, AdminUserProfile
- `/app/admin/billing`, `/app/admin/analytics`, `/app/admin/legal`

**Protection:** AdminRoute + backend RBAC; only users with admin role can access.

**Security**

- Rate limiting (global + strict for auth/payment)
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Request validation (max body, block suspicious patterns)
- CORS from env
- JWT + MFA, bcrypt, no secrets in responses
- Stripe/webhook signature verification
- Disposable email block, referral caps
- Security audit: `python -m security_audit` → SECURITY_AUDIT_REPORT.md

---

### 9. Tests & CI

**Backend**

- `cd backend && pytest tests -v --tb=short`
- ~188 passed, ~13 skipped (asyncpg, in-process auth, network-dependent)
- Coverage: test_security, test_endpoint_mapping, test_webhook_flows, test_data_integrity, test_user_journeys, test_admin*, test_orchestration_e2e, etc.

**Frontend**

- `cd frontend && npm test -- --watchAll=false`
- ~15 tests across 4 suites

**Security audit**

- `cd backend && python -m security_audit`
- Generates SECURITY_AUDIT_REPORT.md; no critical issues when env configured

**CI (`.github/workflows/enterprise-tests.yml`)**

- Lint (ESLint, etc.)
- Security (npm audit, pip-audit, gitleaks, SecurityAudit)
- Frontend unit
- Backend integration
- E2E (Playwright)

---

## Summary

| Category | Status |
|----------|--------|
| **Product** | Full-stack app builder + user automations; same AI in both |
| **Scale** | ~33,600 lines primary code; 120-agent DAG; 73 backend + 117 frontend files |
| **Critical paths** | Auth, projects, build, agents, import, workspace, deploy, tokens, admin — all wired |
| **Placeholders** | MONGO/DB for deploy test; Layout image slots; template HTTP targets |
| **Gaps** | Ads: Option A ("you run the ads we built the stack"); no native Meta/Google |
| **Branding** | CrucibAI — Inevitable AI; Monday→Friday; same AI in builds + automations |
| **Tests & CI** | Backend, frontend, security audit, CI pipeline in place |

---

## 10. Full Functional Capabilities (from code) — Automation, Marketing, Billing, Everything

Everything the app **actually does**, derived from the code, not docs.

### 10.1 Automation (user agents — schedule and webhook)

**Triggers:**
- **Schedule (cron):** e.g. `0 9 * * *` (9am daily), `0 */6 * * *` (every 6h). `automation/schedule.py` computes `next_run_at`; `automation_worker.py` polls and runs due agents.
- **Webhook:** POST `/api/agents/webhook/:id?secret=...` — secret in query or header; dedupe window 60s; rate limit 100/min per agent.

**Actions (executor runs in order):**
- **HTTP:** GET, POST, PUT, PATCH, DELETE. Config: `method`, `url`, `headers`, `body`. Timeout 120s.
- **Email:** Resend or SendGrid (env `RESEND_API_KEY` or `SENDGRID_API_KEY`). Config: `to`, `subject`, `body`. Body can use `{{steps.0.output}}` (previous step output).
- **Slack:** Webhook (incoming) or `chat.postMessage` (channel + token). Config: `webhook_url` or `channel`+`token`, `text`, optional `blocks`.
- **run_agent:** Call our build swarm by name (Content Agent, Scraping Agent, etc.). Config: `agent_name`, `prompt`. Prompt can use `{{steps.0.output}}`. Runs via `run-internal` or callback.
- **approval_required:** Pause before step; return `waiting_approval`; resume via approve/reject.

**Step chaining:** `{{steps.0.output}}`, `{{steps.1.output}}` in body/text/prompt — replaced with actual step output.

**Agent templates (pre-built):**
- Daily digest (9am, Content Agent → summarize)
- YouTube poster (5pm, HTTP to httpbin placeholder)
- Lead finder (webhook, Scraping Agent → Slack)
- Inbox summarizer (webhook, Content Agent → email)
- Status checker (every 6h, HTTP → Slack)

**Internal (dogfooding) agents (SEED_INTERNAL_AGENTS=1):**
- Daily digest (9am, Content Agent)
- Deployment health check (every 6h, HTTP to health URL)
- Lead sync (webhook, HTTP to lead endpoint)
- Content refresh (8am, Content Agent → blog idea)
- Error report (7am, HTTP to health)

**Prompt-to-automation:**
- POST `/api/agents/from-description` — user describes in plain language; LLM produces JSON (name, description, trigger, actions); agent created. Costs 3 credits.

**Frontend:** AgentsPage — list agents, create (Describe or Configure), view runs, copy webhook URL, Run now, enable/disable, edit.

---

### 10.2 Marketing (Content Agent, landing pages, ad-ready copy)

**Content Agent:**
- Part of 120-agent DAG. Writes landing copy: hero headline, 3 feature blurbs (2 lines each), CTA text.
- Used in builds (plan → frontend → content) and in user automations via `run_agent`.

**Landing pages and funnels:**
- `build_kind: "landing"` — single page or simple multi-section (hero, features, CTA, optional waitlist/form).
- Examples: "Landing + waitlist", "Stripe subscription SaaS", "Build a landing page with hero, features section, and email waitlist signup."
- Free tier: `landing_only: true` — 50 credits, landing pages only. Full apps require paid credits.

**Ad-ready copy:**
- Content Agent generates headlines, body, CTA. User (or their stack) pushes to Meta/Google.
- Messaging: "You run the ads; we built the stack." No native Meta/Google action (Option A).

---

### 10.3 Monday→Friday, Bill today, Start making money

**Plans (CREDIT_PLANS):**

| Plan    | Credits | Price (mo) | Notes                |
|---------|---------|------------|----------------------|
| Free    | 50      | $0         | Landing only         |
| Starter | 100     | $12.99     | Fast builds          |
| Builder | 500     | $29.99     | Fast builds          |
| Pro     | 2000    | $79.99     | Priority speed       |
| Agency  | 10000   | $199.99    | Priority speed       |

**Add-ons:** Light (50, $7), Dev (250, $30).

**Annual:** 17% off — Starter $129, Builder $299, Pro $799, Agency $1999.

**Credits:**
- 1 credit = 1000 tokens (legacy).
- Builds deduct credits by token usage; agent runs deduct 5 credits per run.
- 402 when insufficient credits.

**Stripe:**
- POST `/api/stripe/create-checkout-session` — creates Stripe Checkout; redirects to Stripe Pay.
- POST `/api/stripe/webhook` — signature verified; `checkout.session.completed` → add credits to user, insert token_ledger.
- Token bundles: tiers (excl. free) + add-ons.

**Frontend:** TokenCenter (bundles, history, usage, purchase), Pricing (plans, annual toggle), PaymentsWizard (guided buy), AdminBilling.

**Message:** "Describe your idea on Monday. By Friday you can have a live site, automations for leads and content, and the copy to run ads." "You run the ads; we built the stack."

---

### 10.4 AI endpoints (all from server.py)

| Endpoint                 | Purpose                                      |
|--------------------------|----------------------------------------------|
| POST /ai/chat            | Chat (sync)                                  |
| POST /ai/chat/stream     | Chat (stream)                                |
| GET /ai/chat/history/:id | Chat history                                 |
| POST /voice/transcribe   | Whisper transcription                        |
| POST /ai/image-to-code   | Design-from-image                            |
| POST /ai/analyze         | Analyze code                                 |
| POST /ai/validate-and-fix| Validate and fix code                        |
| POST /ai/quality-gate    | Score generated code                         |
| POST /ai/explain-error   | Explain error                                |
| POST /ai/suggest-next    | Suggest next steps                           |
| POST /ai/security-scan   | Security scan (stored on project)            |
| POST /ai/accessibility-check | a11y check                              |
| POST /ai/optimize        | Optimize code                                |
| POST /ai/design-from-url | Design spec from URL                         |
| POST /ai/inject-stripe   | Inject Stripe checkout                       |
| POST /ai/generate-readme | Generate README                              |
| POST /ai/generate-docs   | Generate API docs                            |
| POST /ai/generate-faq-schema | Generate FAQ schema                    |
| POST /generate/doc       | Generate doc                                 |
| POST /generate/slides    | Generate slides                              |
| POST /generate/sheets    | Generate CSV/JSON data                       |

---

### 10.5 Build, import, deploy, workspace

**Build:**
- Plan → DAG phases → 120 agents (Planner, Content, Frontend, Backend, Design, etc.).
- WebSocket `/api/projects/:id/events` for real-time progress.
- Quality score (0–100), phase retry.
- build_kind: web, mobile, landing.

**Import:**
- POST `/api/projects/import` — paste, zip_base64, git_url. Creates project, writes files to workspace.
- Dashboard Import modal → Workspace with project_id.

**Deploy:**
- GET `/api/projects/:id/deploy/zip` — ZIP of deploy_files.
- POST `/api/projects/:id/deploy/vercel`, `/deploy/netlify` — deploy with token from Settings.

**Workspace:**
- GET/POST workspace files; Monaco editor; chat; tools (security scan, accessibility, validate-and-fix); export ZIP/GitHub/deploy.

---

### 10.6 Auth, admin, security

**Auth:** Register, login, me, verify-mfa; Google OAuth; JWT; MFA (TOTP); API keys in Settings.

**Admin:** Dashboard, users (list, get, update), billing, analytics, legal. AdminRoute + RBAC.

**Security:** Rate limits (global + strict auth/payment); security headers; CORS; HTTPS redirect (env); request validation; disposable email block; referral caps.

---

**References:** docs/CODEBASE_SOURCE_OF_TRUTH.md, docs/LAUNCH_SEQUENCE_AUDIT.md, docs/GAPS_AND_INTEGRATIONS_REVIEW.md, docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md, docs/MESSAGING_AND_BRAND_VOICE.md.
