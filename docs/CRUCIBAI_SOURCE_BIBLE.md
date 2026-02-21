# CrucibAI Source Bible

**The Complete Source of Truth — Every Function, Every Connection, Every Competitive Edge**

**Version:** 1.0  
**Date:** February 21, 2026  
**Classification:** Confidential — Investor / Developer / Team  
**Author:** CrucibAI Engineering  
**Codebase Snapshot:** `main` branch, commit `ee396a5`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision and Value Proposition](#2-product-vision-and-value-proposition)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Backend: Complete API Reference (178 Routes)](#5-backend-complete-api-reference)
6. [Frontend: Complete Page and Component Reference](#6-frontend-complete-page-and-component-reference)
7. [The 123-Agent DAG: Every Agent, Its Purpose, and Dependencies](#7-the-123-agent-dag)
8. [Orchestration Engine: How Builds Work End-to-End](#8-orchestration-engine)
9. [Quality Gate System](#9-quality-gate-system)
10. [Authentication and Security Architecture](#10-authentication-and-security-architecture)
11. [Automation Engine (Agents Page)](#11-automation-engine)
12. [Payments and Token Economy](#12-payments-and-token-economy)
13. [Deployment and Export System](#13-deployment-and-export-system)
14. [Admin Panel: Complete Reference](#14-admin-panel)
15. [Data Room: Database Schema and Collections](#15-data-room)
16. [Engine Room: Middleware, Performance, and Observability](#16-engine-room)
17. [Connectivity Map: How Everything Connects](#17-connectivity-map)
18. [Competitive Analysis: How CrucibAI Beats Every Competitor](#18-competitive-analysis)
19. [Gap Analysis: What Is Missing, Broken, or Incomplete](#19-gap-analysis)
20. [Roadmap: What Comes Next](#20-roadmap)
21. [Environment Variables Reference](#21-environment-variables)
22. [Developer Onboarding Guide](#22-developer-onboarding)
23. [Appendix: File Inventory](#23-appendix-file-inventory)

---

## 1. Executive Summary

CrucibAI is a full-stack AI application builder and automation platform. The core thesis is simple: **state the idea, we build it.** A user types a natural-language prompt — "build me a SaaS dashboard with Stripe billing" — and CrucibAI's 123-agent orchestration engine plans, generates, tests, secures, and deploys the complete application. No product limit: web apps, mobile apps (Expo + App Store / Play Store pack), SaaS, bots, agents, dashboards, landing pages, trading platforms, and more.

The platform is not just a code generator. It is a **unified build-and-automate platform** where the same AI agents that build applications can be invoked inside user-created automations (scheduled tasks, webhooks, chained workflows). This is the key differentiator that no competitor offers.

**By the numbers:**

| Metric | Value |
|--------|-------|
| Total lines of code | 55,467 |
| Backend API routes | 178 |
| AI agents in DAG | 123 |
| Frontend pages | 42 |
| Frontend components | 23 |
| Parallel orchestration phases | 7 |
| Supported LLM providers | 4 (OpenAI, Anthropic, Google Gemini, user-supplied) |
| Deployment targets | 4 (Vercel, Netlify, ZIP, GitHub) |
| Admin panel views | 6 (Dashboard, Users, User Profile, Billing, Analytics, Legal) |
| Middleware layers | 7 (Rate Limit, Security Headers, HTTPS Redirect, CORS, Request Validation, Request Tracker, Performance Monitoring) |

---

## 2. Product Vision and Value Proposition

### The Problem

Building software today requires assembling dozens of tools: a code editor, a design tool, a deployment pipeline, a CI/CD system, a testing framework, an automation platform, and more. Existing AI code generators (Lovable, Bolt, Cursor) solve one slice — they generate code — but they do not plan, test, secure, deploy, or automate. Automation platforms (n8n, Zapier, Make) handle workflows but cannot build applications.

### The CrucibAI Solution

CrucibAI collapses the entire software lifecycle into a single prompt-driven platform:

1. **Plan** — The Planner agent produces a structured plan with features, design language, color palette, and component list.
2. **Build** — A DAG of 123 specialized agents executes in parallel phases: frontend, backend, database, API integration, design, SEO, content, auth, payments, email, and more.
3. **Test** — Security Checker, Test Executor, UX Auditor, Performance Analyzer, and Accessibility Agent validate the output.
4. **Deploy** — One-click deployment to Vercel, Netlify, or ZIP download. GitHub export available.
5. **Automate** — Users create automations (schedule or webhook) that invoke the same AI agents as steps. The same AI that builds the app runs inside the automations.

### The Unique Competitive Advantage

> **"The same AI that builds your app runs inside your automations."**

No other platform offers this. Lovable generates code but cannot automate. n8n automates but cannot build. CrucibAI does both, and the two capabilities share the same 123-agent engine. A user can:

- Build a SaaS app with Stripe billing in one prompt.
- Create an automation that runs the Content Agent every Monday to refresh landing page copy.
- Chain a Scraping Agent → Content Agent → Email Agent automation that monitors competitors and sends weekly reports.
- Use the `run_agent` action type to invoke any of the 123 agents as a step in any automation.

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│  React 18 + CRACO + Radix UI + Monaco Editor + Sandpack         │
│  42 pages, 23 components, Framer Motion animations              │
├─────────────────────────────────────────────────────────────────┤
│                          ↕ HTTP / WebSocket                     │
├─────────────────────────────────────────────────────────────────┤
│                     BACKEND (FastAPI + Uvicorn)                 │
│  178 API routes, 7 middleware layers, JWT + MFA auth            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Orchestration │  │  Automation  │  │    Admin     │          │
│  │   Engine      │  │   Engine     │  │   Panel      │          │
│  │ (123 agents)  │  │ (executor)   │  │   (RBAC)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                  │                                     │
│  ┌──────┴──────────────────┴───────────────────────────┐        │
│  │              LLM Provider Layer                      │        │
│  │  OpenAI / Anthropic / Gemini / User-supplied keys    │        │
│  └──────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│                     DATABASE (MongoDB)                           │
│  Collections: users, projects, project_logs, agent_status,      │
│  user_agents, agent_runs, shares, credit_transactions           │
├─────────────────────────────────────────────────────────────────┤
│                     EXTERNAL SERVICES                           │
│  Stripe (payments) · Vercel/Netlify (deploy) · GitHub (export)  │
│  Google OAuth · SMTP (email) · Slack (webhooks)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Repository Structure

```
newcrucib/
├── backend/
│   ├── server.py              # Main FastAPI app (5,580 lines) — all 178 routes
│   ├── orchestration.py       # DAG orchestration engine — parallel phase execution
│   ├── agent_dag.py           # 123-agent DAG configuration with dependencies
│   ├── agent_real_behavior.py # Real behavior definitions per agent
│   ├── real_agent_runner.py   # LLM execution for individual agents
│   ├── project_state.py       # Project state persistence (plan, stack, reports)
│   ├── quality.py             # Code quality scoring (0-100)
│   ├── code_quality.py        # Extended quality analysis
│   ├── middleware.py           # 7 middleware classes
│   ├── security_audit.py      # Internal security audit
│   ├── agents/                # Specialized agent implementations
│   ├── automation/            # Schedule, executor, models for user agents
│   ├── tools/                 # file_agent, api_agent, browser_agent, deployment, database
│   ├── workers/               # Automation worker (runs user agents)
│   ├── utils/                 # audit_log, rbac
│   └── tests/                 # Backend test suite
├── frontend/
│   ├── src/
│   │   ├── pages/             # 42 page components
│   │   ├── components/        # 23 reusable components
│   │   ├── services/          # Collaboration, CollaborativeEditing
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utility helpers
│   │   ├── styles/            # Global CSS, responsive, effects
│   │   └── App.js             # Route definitions (296 lines)
│   └── e2e/                   # Playwright E2E tests
├── docs/                      # 30+ strategy, security, compliance documents
├── ide-extensions/            # VS Code, JetBrains, Sublime, Vim extensions
├── scripts/                   # Utility scripts
├── memory/                    # PRD and project memory
├── Dockerfile                 # Multi-stage production build
├── railway.json               # Railway deployment config
└── *.md                       # 40+ documentation files at root
```

---

## 4. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend Framework** | React 18 | Component-based UI |
| **Build Tool** | CRACO (Create React App Configuration Override) | Webpack config customization |
| **UI Library** | Radix UI | Accessible component primitives |
| **Code Editor** | Monaco Editor (`@monaco-editor/react`) | In-browser code editing |
| **Live Preview** | Sandpack (`@codesandbox/sandpack-react`) | Real-time code preview |
| **Animations** | Framer Motion | Page transitions, micro-interactions |
| **Icons** | Lucide React | 1,000+ icon library |
| **Routing** | React Router DOM v6 | Client-side routing with nested layouts |
| **HTTP Client** | Axios | API communication |
| **Backend Framework** | FastAPI | Async Python web framework |
| **ASGI Server** | Uvicorn | Production-grade ASGI server |
| **Database** | MongoDB (Motor async driver) | Document store for all data |
| **Auth** | JWT (PyJWT) + bcrypt + TOTP (pyotp) | Token auth with MFA |
| **Payments** | Stripe (stripe-python) | Checkout sessions, webhooks |
| **LLM Providers** | OpenAI, Anthropic, Google Gemini | Multi-provider AI with fallback chain |
| **Deployment** | Docker, Railway, Vercel, Netlify | Multi-target deployment |
| **CI/CD** | GitHub Actions | Automated testing pipeline |

---

## 5. Backend: Complete API Reference

The backend exposes **178 API routes** through a single FastAPI application (`server.py`, 5,580 lines). All routes are prefixed with `/api/` via the `api_router`. Below is the complete reference organized by domain.

### 5.1 Authentication and User Management (16 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/auth/register` | Register new user (email, password, name) | No |
| POST | `/api/auth/signup` | Alias for register (compatibility) | No |
| POST | `/api/auth/login` | Login with email/password, returns JWT | No |
| POST | `/api/auth/verify-mfa` | Verify TOTP code after login | No (MFA temp token) |
| GET | `/api/auth/me` | Get current user profile | Yes |
| POST | `/api/mfa/setup` | Generate TOTP secret and QR code | Yes |
| POST | `/api/mfa/verify` | Verify and enable MFA | Yes |
| POST | `/api/mfa/disable` | Disable MFA | Yes |
| GET | `/api/mfa/status` | Check MFA enabled status | Yes |
| POST | `/api/mfa/backup-code/use` | Use backup code for MFA recovery | No (MFA temp token) |
| GET | `/api/audit/logs` | Get user audit log entries | Yes |
| GET | `/api/audit/logs/export` | Export audit logs as CSV | Yes |
| GET | `/api/auth/google` | Initiate Google OAuth flow | No |
| GET | `/api/auth/google/callback` | Google OAuth callback handler | No |
| GET | `/api/users/me/deploy-tokens` | Get user's Vercel/Netlify tokens | Yes |
| PATCH | `/api/users/me/deploy-tokens` | Update deploy tokens | Yes |

**How it works:** Registration hashes the password with bcrypt and stores the user in MongoDB. Login verifies credentials and returns a JWT token (HS256, configurable expiry). If MFA is enabled, login returns a temporary MFA token instead, and the client must call `/verify-mfa` with the TOTP code. Google OAuth uses the authorization code flow with `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### 5.2 AI and Generation (14 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/ai/chat` | General AI chat (non-streaming) | Yes |
| GET | `/api/ai/chat/history/{session_id}` | Get chat history for a session | Yes |
| POST | `/api/ai/chat/stream` | Streaming AI chat (SSE) | Yes |
| POST | `/api/ai/analyze` | Analyze code or text | Yes |
| POST | `/api/ai/image-to-code` | Convert screenshot/image to code | Yes |
| POST | `/api/ai/validate-and-fix` | Validate code and auto-fix errors | Yes |
| POST | `/api/ai/quality-gate` | Run quality gate scoring on code | Yes |
| POST | `/api/ai/explain-error` | Explain a code error in plain English | Yes |
| POST | `/api/ai/suggest-next` | Suggest next features/improvements | Yes |
| POST | `/api/ai/inject-stripe` | Inject Stripe payment code into app | Yes |
| POST | `/api/ai/generate-readme` | Generate README for project | Yes |
| POST | `/api/ai/generate-docs` | Generate documentation | Yes |
| POST | `/api/ai/generate-faq-schema` | Generate FAQ schema markup | Yes |
| POST | `/api/ai/security-scan` | Run security scan on code | Yes |
| POST | `/api/ai/optimize` | Optimize code for performance | Yes |
| POST | `/api/ai/accessibility-check` | Check code for accessibility issues | Yes |
| POST | `/api/ai/design-from-url` | Clone design from a URL | Yes |

**How it works:** Each AI route uses the `_call_llm_with_fallback` function, which implements a model chain with automatic fallback. The chain tries providers in order (e.g., Gemini → OpenAI → Anthropic) based on available API keys. User-supplied keys (stored in Settings) take priority over platform keys. Token usage is tracked and deducted from the user's credit balance.

### 5.3 Content Generation (3 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/generate/doc` | Generate a document (PDF/Word) | Yes |
| POST | `/api/generate/slides` | Generate a slide deck | Yes |
| POST | `/api/generate/sheets` | Generate a spreadsheet | Yes |

### 5.4 Build and Project Management (12 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/build/plan` | Generate a build plan from prompt | Yes |
| GET | `/api/build/phases` | Get standard build phase definitions | Yes |
| POST | `/api/build/from-reference` | Build from a reference URL/image | Yes |
| GET | `/api/projects/{id}/phases` | Get current phase status for project | Yes |
| GET | `/api/projects/{id}/logs` | Get build logs for project | Yes |
| GET | `/api/projects/{id}/events/snapshot` | Get event snapshot (SSE fallback) | Yes |
| POST | `/api/projects/{id}/retry-phase` | Retry a failed build phase | Yes |
| GET | `/api/projects/{id}/workspace/files` | List workspace files | Yes |
| GET | `/api/projects/{id}/workspace/file` | Read a specific workspace file | Yes |
| GET | `/api/projects/{id}/dependency-audit` | Run npm/pip audit on project | Yes |
| POST | `/api/projects/{id}/duplicate` | Duplicate a project | Yes |
| POST | `/api/projects/{id}/save-as-template` | Save project as reusable template | Yes |

**How it works:** The `/build/plan` endpoint is the entry point for all builds. It takes a user prompt, detects the build kind (web, mobile, SaaS, trading, etc.), and generates a structured plan using the LLM. The plan includes features, design language, color palette, and component list. Optionally, it runs in "swarm mode" where the plan and follow-up suggestions are generated in parallel. After the plan is approved, the orchestration engine (`orchestration.py`) executes the 123-agent DAG.

### 5.5 Agent Orchestration (35+ routes)

Individual agent execution routes follow the pattern `POST /api/agents/run/{agent-name}`:

| Agent Route | Agent Name | Purpose |
|-------------|-----------|---------|
| `/agents/run/planner` | Planner | Generate project plan |
| `/agents/run/requirements-clarifier` | Requirements Clarifier | Clarify ambiguous requirements |
| `/agents/run/stack-selector` | Stack Selector | Choose tech stack |
| `/agents/run/backend-generate` | Backend Generation | Generate backend code |
| `/agents/run/database-design` | Database Agent | Design database schema |
| `/agents/run/api-integrate` | API Integration | Wire API endpoints |
| `/agents/run/test-generate` | Test Generation | Generate test suite |
| `/agents/run/image-generate` | Image Generation | Generate image assets |
| `/agents/run/test-executor` | Test Executor | Execute tests |
| `/agents/run/deploy` | Deployment Agent | Generate deploy config |
| `/agents/run/memory-store` | Memory Agent | Store project memory |
| `/agents/run/memory-list` | Memory Agent | List stored memories |
| `/agents/run/export-pdf` | PDF Export | Export project as PDF |
| `/agents/run/export-excel` | Excel Export | Export as spreadsheet |
| `/agents/run/export-markdown` | Markdown Export | Export as Markdown |
| `/agents/run/scrape` | Scraping Agent | Scrape data sources |
| `/agents/run/automation` | Automation Agent | Suggest automations |
| `/agents/run/automation-list` | Automation Agent | List automations |
| `/agents/run/design` | Design Agent | Generate design spec |
| `/agents/run/layout` | Layout Agent | Inject image placeholders |
| `/agents/run/seo` | SEO Agent | Generate SEO metadata |
| `/agents/run/content` | Content Agent | Generate landing copy |
| `/agents/run/brand` | Brand Agent | Generate brand guidelines |
| `/agents/run/documentation` | Documentation Agent | Generate README |
| `/agents/run/validation` | Validation Agent | Generate validation rules |
| `/agents/run/auth-setup` | Auth Setup Agent | Generate auth flow |
| `/agents/run/payment-setup` | Payment Setup Agent | Generate Stripe integration |
| `/agents/run/monitoring` | Monitoring Agent | Generate monitoring setup |
| `/agents/run/accessibility` | Accessibility Agent | Generate a11y improvements |
| `/agents/run/devops` | DevOps Agent | Generate CI/CD config |
| `/agents/run/webhook` | Webhook Agent | Generate webhook endpoints |
| `/agents/run/email` | Email Agent | Generate email setup |
| `/agents/run/legal-compliance` | Legal Compliance Agent | Generate GDPR/CCPA hints |
| `/agents/run/generic` | Generic Agent | Run any agent by name |
| `/agents/run-internal` | Internal Runner | Run agent internally (token auth) |

### 5.6 User Agents / Automations (8 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/agents` | Create a new user agent | Yes |
| GET | `/api/agents` | List user's agents | Yes |
| GET | `/api/agents/templates` | Get agent templates | Yes |
| GET | `/api/agents/status/{project_id}` | Get agent status for project | Yes |
| GET | `/api/agents/activity` | Get recent agent activity | Yes |
| POST | `/api/agents/webhook/{agent_id}` | Trigger agent via webhook | No (secret in query) |

### 5.7 Tokens and Billing (6 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/tokens/bundles` | Get available token bundles | Yes |
| POST | `/api/tokens/purchase` | Purchase tokens (Stripe) | Yes |
| GET | `/api/tokens/history` | Get token transaction history | Yes |
| GET | `/api/tokens/usage` | Get token usage analytics | Yes |
| POST | `/api/stripe/create-checkout-session` | Create Stripe checkout | Yes |
| POST | `/api/stripe/webhook` | Stripe webhook handler | No (signature verified) |

### 5.8 Referrals (2 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/referrals/code` | Get user's referral code | Yes |
| GET | `/api/referrals/stats` | Get referral statistics | Yes |

### 5.9 Deploy and Export (8 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/export/zip` | Export project as ZIP | Yes |
| POST | `/api/export/github` | Export to GitHub repository | Yes |
| POST | `/api/export/deploy` | Generic deploy trigger | Yes |
| GET | `/api/projects/{id}/deploy/files` | Get deploy file manifest | Yes |
| GET | `/api/projects/{id}/deploy/zip` | Download deploy ZIP | Yes |
| GET | `/api/projects/{id}/export/deploy` | Get deploy status | Yes |
| POST | `/api/projects/{id}/deploy/vercel` | Deploy to Vercel | Yes |
| POST | `/api/projects/{id}/deploy/netlify` | Deploy to Netlify | Yes |

### 5.10 Workspace and Tools (10 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/workspace/env` | Get workspace environment | Yes |
| POST | `/api/workspace/env` | Set workspace environment | Yes |
| GET | `/api/settings/capabilities` | Get platform capabilities | Yes |
| GET | `/api/projects/{id}/preview-token` | Get preview token | Yes |
| GET | `/api/projects/{id}/preview` | Serve project preview | No (token in query) |
| POST | `/api/tools/browser` | Browser tool for agents | Yes |
| POST | `/api/tools/file` | File tool for agents | Yes |
| POST | `/api/tools/api` | API tool for agents | Yes |
| POST | `/api/tools/database` | Database tool for agents | Yes |
| POST | `/api/tools/deploy` | Deploy tool for agents | Yes |

### 5.11 Templates, Examples, Patterns (7 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/templates` | List project templates | Yes |
| POST | `/api/projects/from-template` | Create project from template | Yes |
| GET | `/api/examples` | List example projects | Yes |
| GET | `/api/examples/{name}` | Get specific example | Yes |
| POST | `/api/examples/{name}/fork` | Fork an example | Yes |
| GET | `/api/patterns` | List design patterns | Yes |
| POST | `/api/exports` | Create export record | Yes |
| GET | `/api/exports` | List exports | Yes |

### 5.12 Sharing (2 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| POST | `/api/share/create` | Create shareable link | Yes |
| GET | `/api/share/{token}` | View shared project | No |

### 5.13 Prompts (4 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/prompts/templates` | Get prompt templates | Yes |
| GET | `/api/prompts/recent` | Get recent prompts | Yes |
| POST | `/api/prompts/save` | Save a prompt | Yes |
| GET | `/api/prompts/saved` | Get saved prompts | Yes |

### 5.14 Dashboard (1 route)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/dashboard/stats` | Get user dashboard statistics | Yes |

### 5.15 Admin Panel (14 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/admin/dashboard` | Admin dashboard stats | Admin |
| GET | `/api/admin/analytics/overview` | Analytics overview | Admin |
| GET | `/api/admin/analytics/daily` | Daily analytics | Admin |
| GET | `/api/admin/analytics/weekly` | Weekly analytics | Admin |
| GET | `/api/admin/analytics/report` | Analytics report | Admin |
| GET | `/api/admin/users` | List all users | Admin |
| GET | `/api/admin/users/{id}` | Get user details | Admin |
| POST | `/api/admin/users/{id}/grant-credits` | Grant credits to user | Admin |
| POST | `/api/admin/users/{id}/suspend` | Suspend user | Admin |
| POST | `/api/admin/users/{id}/downgrade` | Downgrade user plan | Admin |
| GET | `/api/admin/users/{id}/export` | Export user data | Admin |
| GET | `/api/admin/billing/transactions` | List billing transactions | Admin |
| GET | `/api/admin/fraud/flags` | Get fraud flags | Admin |
| GET | `/api/admin/legal/blocked-requests` | Get blocked legal requests | Admin |
| POST | `/api/admin/legal/review/{id}` | Review legal request | Admin |
| GET | `/api/admin/referrals/links` | Get referral links | Admin |
| GET | `/api/admin/referrals/leaderboard` | Referral leaderboard | Admin |
| GET | `/api/admin/segments` | Get user segments | Admin |

### 5.16 Miscellaneous (6 routes)

| Method | Route | Purpose | Auth Required |
|--------|-------|---------|---------------|
| GET | `/api/` | API root / health | No |
| GET | `/api/health` | Health check | No |
| GET | `/api/brand` | Get brand configuration | No |
| POST | `/api/errors/log` | Log frontend errors | No |
| POST | `/api/enterprise/contact` | Enterprise contact form | No |
| GET | `/api/voice/transcribe` | Transcribe audio to text | Yes |
| POST | `/api/files/analyze` | Analyze uploaded file | Yes |
| POST | `/api/rag/query` | RAG query (retrieval-augmented generation) | Yes |
| POST | `/api/search` | Web search | Yes |

### 5.17 WebSocket

| Protocol | Route | Purpose |
|----------|-------|---------|
| WebSocket | `/ws/projects/{project_id}/progress` | Real-time build progress updates |

The WebSocket endpoint streams build events to the frontend during orchestration. Events include: `phase_start`, `phase_complete`, `agent_start`, `agent_complete`, `agent_error`, `build_completed`, `build_failed`, and `progress` (percentage updates).

---

## 6. Frontend: Complete Page and Component Reference

### 6.1 Routing Architecture

The frontend uses React Router v6 with nested layouts. The route structure is:

```
/ .......................... LandingPage (public)
/auth ...................... AuthPage (login/register/MFA)
/builder ................... Builder (public code playground)
/workspace ................. Workspace (protected, standalone)
/share/:token .............. ShareView (public)
/privacy ................... Privacy policy
/terms ..................... Terms of service
/security .................. Security page
/aup ....................... Acceptable Use Policy
/dmca ...................... DMCA policy
/cookies ................... Cookie policy
/about ..................... About page
/pricing ................... Pricing page
/enterprise ................ Enterprise contact
/features .................. Features showcase
/templates ................. Public templates gallery
/patterns .................. Public patterns gallery
/learn ..................... Public learn center
/docs ...................... Documentation
/tutorials ................. Tutorials
/shortcuts ................. Keyboard shortcuts
/prompts ................... Public prompt library
/benchmarks ................ Performance benchmarks
/blog ...................... Blog listing
/blog/:slug ................ Blog post

/app ....................... Protected Layout (3-column)
  /app ..................... Dashboard (home)
  /app/builder ............. Builder
  /app/workspace ........... Workspace
  /app/projects/new ........ ProjectBuilder
  /app/projects/:id ........ AgentMonitor
  /app/tokens .............. TokenCenter
  /app/exports ............. ExportCenter
  /app/patterns ............ PatternLibrary
  /app/templates ........... TemplatesGallery
  /app/prompts ............. PromptLibrary
  /app/learn ............... LearnPanel
  /app/env ................. EnvPanel
  /app/shortcuts ........... ShortcutCheatsheet
  /app/payments-wizard ..... PaymentsWizard
  /app/examples ............ ExamplesGallery
  /app/generate ............ GenerateContent
  /app/agents .............. AgentsPage
  /app/agents/:id .......... AgentsPage (detail)
  /app/settings ............ Settings
  /app/audit-log ........... AuditLog
  /app/admin ............... AdminDashboard (admin only)
  /app/admin/users ......... AdminUsers (admin only)
  /app/admin/users/:id ..... AdminUserProfile (admin only)
  /app/admin/billing ....... AdminBilling (admin only)
  /app/admin/analytics ..... AdminAnalytics (admin only)
  /app/admin/legal ......... AdminLegal (admin only)
```

### 6.2 Core Pages (Detailed)

**Dashboard.jsx (538 lines)** — The home screen. Features intent detection that distinguishes between "build" prompts (navigates to Workspace with `autoStart: true`) and "chat" prompts (responds conversationally inline). Includes voice recording with VoiceWaveform visualization, model selector (Auto/GPT-4o/Claude/Gemini), quick-start chips (Landing page, Automation, Import code, SaaS MVP, Mobile app, API backend), and chat thread display.

**Workspace.jsx (2,100+ lines)** — The primary build workspace. This is the most complex page in the application. It features:
- **Monaco code editor** with multi-file tab support
- **Sandpack live preview** with real-time rendering
- **InlineAgentMonitor** showing build progress with per-phase status
- **Chat interface** for iterative modifications
- **Voice input** with waveform visualization
- **Auto-fix** error boundary that catches Sandpack errors and auto-repairs code
- **Deploy modal** with Vercel/Netlify/ZIP options
- **Dev mode toggle** that switches between simple chat view and full IDE view
- **Multi-file output parsing** via `parseMultiFileOutput()` function
- **WebSocket connection** for real-time build progress
- **Quality score display** in the agent monitor

**AuthPage.jsx (499 lines)** — Login, registration, and MFA verification. Supports email/password auth and Google OAuth. Password strength indicator, disposable email detection, and animated transitions.

**AgentMonitor.jsx (602 lines)** — Real-time build monitoring dashboard. Shows per-phase progress, per-agent status (running/complete/failed), token usage, logs, and quality score. Connects via WebSocket for live updates.

**AgentsPage.jsx (322 lines)** — User automation management. Create, edit, enable/disable, and run automations. Supports schedule (cron) and webhook triggers. Shows run history with status and duration.

**Settings.jsx** — User settings including API keys (OpenAI, Anthropic, Gemini), deploy tokens (Vercel, Netlify), MFA setup, and profile management.

**LandingPage.jsx** — Public marketing page with hero section, feature showcase, pricing preview, and CTA.

### 6.3 Components (Detailed)

| Component | Lines | Purpose |
|-----------|-------|---------|
| **EverythingSupport.jsx** | 396 | Comprehensive support/help panel |
| **VoiceInput.jsx** | 335 | Voice recording with transcription |
| **VibeCoding.jsx** | 316 | "Vibe coding" mode for creative prompts |
| **AdvancedIDEUX.jsx** | 311 | Advanced IDE features (multi-cursor, etc.) |
| **RightPanel.jsx** | 259 | Right sidebar with preview, code, terminal tabs |
| **DeployButton.jsx** | 259 | Deploy modal with Vercel/Netlify/ZIP/GitHub |
| **InlineAgentMonitor.jsx** | 253 | Inline build progress monitor with quality score |
| **OnboardingTour.jsx** | 242 | First-time user onboarding flow |
| **Sidebar.jsx** | 226 | Left navigation sidebar with task list |
| **ExampleLayout.jsx** | 211 | Layout wrapper for example projects |
| **Layout.jsx** | 203 | 3-column layout wrapper (sidebar + main + right) |
| **ErrorBoundary.jsx** | 182 | Global error boundary with error logging |
| **ManusComputer.jsx** | 147 | Manus-style computer interface component |
| **SandpackErrorBoundary.jsx** | 126 | Sandpack-specific error boundary with auto-fix |
| **VoiceWaveform.jsx** | 114 | Audio waveform visualization during recording |
| **Layout3Column.jsx** | 93 | CSS Grid 3-column layout implementation |
| **BuildProgress.jsx** | 90 | Build progress bar with phase indicators |
| **PremiumInput.jsx** | 86 | Styled input with premium effects |
| **PublicFooter.jsx** | 68 | Public page footer |
| **PremiumButton.jsx** | 62 | Styled button with premium effects |
| **PremiumCard.jsx** | 60 | Styled card with premium effects |
| **PublicNav.jsx** | 38 | Public page navigation |
| **QualityScore.jsx** | 35 | Quality score display component |

---

## 7. The 123-Agent DAG

The CrucibAI orchestration engine uses a Directed Acyclic Graph (DAG) of 123 specialized AI agents. Each agent has a defined purpose, system prompt, dependency list, and criticality level. Agents execute in parallel phases — agents within the same phase run concurrently, while phases execute sequentially.

### 7.1 Agent Criticality Levels

| Level | Behavior on Failure | Agents |
|-------|-------------------|--------|
| **Critical** | Stop entire build | Planner, Stack Selector |
| **High** | Use fallback output, continue | Requirements Clarifier, Frontend Generation, Backend Generation, Database Agent |
| **Medium** | Skip agent, continue | API Integration, Test Generation, Security Checker, Test Executor, Auth Setup, Payment Setup, Deployment Agent |
| **Low** | Skip silently | All others (Image Generation, UX Auditor, SEO Agent, etc.) |

### 7.2 Parallel Execution Phases

The 123 agents are organized into 7 parallel execution phases:

**Phase 1 — Planning:**
- Planner (critical)

**Phase 2 — Requirements and Strategy:**
- Requirements Clarifier, Stack Selector, Content Agent, Legal Compliance Agent

**Phase 3 — Core Generation:**
- Frontend Generation, Backend Generation, Database Agent, Design Agent, SEO Agent, Brand Agent, Auth Setup Agent, Payment Setup Agent, Email Agent

**Phase 4 — Integration and Assets:**
- API Integration, Test Generation, Image Generation, Scraping Agent, Automation Agent

**Phase 5 — Validation and Quality:**
- Security Checker, Test Executor, UX Auditor, Performance Analyzer, Layout Agent, Validation Agent, Accessibility Agent, Webhook Agent

**Phase 6 — Deployment and Recovery:**
- Deployment Agent, Error Recovery, Memory Agent

**Phase 7 — Export and Documentation:**
- PDF Export, Excel Export, Markdown Export, Documentation Agent, Monitoring Agent, DevOps Agent

### 7.3 Complete Agent List (123 Agents)

| # | Agent Name | Category | Dependencies | Purpose |
|---|-----------|----------|-------------|---------|
| 1 | Planner | Planning | None | Generate structured project plan |
| 2 | Requirements Clarifier | Planning | Planner | Clarify ambiguous requirements |
| 3 | Stack Selector | Planning | Planner | Choose optimal tech stack |
| 4 | Native Config Agent | Mobile | Stack Selector | React Native/Expo configuration |
| 5 | Store Prep Agent | Mobile | Native Config Agent | App Store/Play Store preparation |
| 6 | Frontend Generation | Core | Stack Selector | Generate React/Vue/Angular frontend |
| 7 | Backend Generation | Core | Stack Selector | Generate FastAPI/Express backend |
| 8 | Database Agent | Core | Stack Selector | Design database schema |
| 9 | API Integration | Integration | Backend Generation | Wire API endpoints |
| 10 | Test Generation | Quality | Frontend + Backend | Generate test suites |
| 11 | Image Generation | Assets | Design Agent | Generate image assets |
| 12 | Video Generation | Assets | Design Agent | Generate video content |
| 13 | Security Checker | Validation | Frontend + Backend | Security audit (3-5 items) |
| 14 | Test Executor | Validation | Test Generation | Execute tests |
| 15 | UX Auditor | Validation | Frontend Generation | Accessibility/UX audit |
| 16 | Performance Analyzer | Validation | Frontend + Backend | Performance optimization tips |
| 17 | Deployment Agent | Deploy | Stack Selector | Deploy configuration |
| 18 | Error Recovery | Deploy | Deployment Agent | Failure point analysis |
| 19 | Memory Agent | Deploy | Planner | Project memory storage |
| 20 | PDF Export | Export | Planner | PDF summary generation |
| 21 | Excel Export | Export | Planner | Spreadsheet generation |
| 22 | Markdown Export | Export | Planner | Markdown summary |
| 23 | Scraping Agent | Integration | Stack Selector | Data source identification |
| 24 | Automation Agent | Integration | Stack Selector | Automation suggestions |
| 25 | Design Agent | Design | Planner | Image placement specification |
| 26 | Layout Agent | Design | Frontend + Design | Inject image placeholders |
| 27 | SEO Agent | Marketing | Deployment Agent | Meta tags, OG, schema |
| 28 | Content Agent | Marketing | Planner | Landing copy generation |
| 29 | Brand Agent | Marketing | Planner | Colors, fonts, tone |
| 30 | Documentation Agent | Export | Frontend + Backend | README generation |
| 31 | Validation Agent | Quality | Frontend + Backend | Zod/Yup schemas |
| 32 | Auth Setup Agent | Security | Backend Generation | JWT/OAuth flow |
| 33 | Payment Setup Agent | Payments | Backend Generation | Stripe integration |
| 34 | Monitoring Agent | DevOps | Deployment Agent | Sentry/analytics setup |
| 35 | Accessibility Agent | Quality | Frontend Generation | a11y improvements |
| 36 | DevOps Agent | DevOps | Deployment Agent | CI/CD, Dockerfile |
| 37 | Webhook Agent | Integration | Backend Generation | Webhook endpoint design |
| 38 | Email Agent | Integration | Backend Generation | Transactional email |
| 39 | Legal Compliance Agent | Legal | Planner | GDPR/CCPA compliance |
| 40-53 | Phase 2 Agents | Extended | Various | GraphQL, WebSocket, i18n, Caching, Rate Limit, Search, Analytics, API Docs, Mobile Responsive, Migration, Backup, Notification, Design Iteration, Code Review |
| 54-78 | Phase 3 Agents | Advanced | Various | Staging, A/B Test, Feature Flag, Error Boundary, Logging, Metrics, Audit Trail, Session, OAuth Provider, 2FA, Stripe Subscription, Invoice, CDN, SSR, Bundle Analyzer, Lighthouse, Schema Validation, Mock API, E2E, Load Test, Dependency Audit, License, Terms, Privacy Policy, Cookie Consent |
| 79-102 | Phase 4 Agents | Enterprise | Various | Multi-tenant, RBAC, SSO, Audit Export, Data Residency, HIPAA, SOC2, Penetration Test, Incident Response, SLA, Cost Optimizer, Accessibility WCAG, RTL, Dark Mode, Keyboard Nav, Screen Reader, Component Library, Design System, Animation, Chart, Table, Form Builder, Workflow, Queue |
| 103-117 | Vibe/Creative Agents | Creative | Various | Vibe Analyzer, Voice Context, Video Tutorial, Aesthetic Reasoner, Team Preferences, Collaborative Memory, Real-time Feedback, Mood Detection, Accessibility Vibe, Performance Vibe, Creativity Catalyst, IDE Integration Coordinator, Multi-language Code, Team Collaboration, User Onboarding, Customization Engine |
| 118-123 | Tool Agents | Tools | Various | Browser Tool, File Tool, API Tool, Database Tool, Deployment Tool |

---

## 8. Orchestration Engine

The orchestration engine (`orchestration.py`) is the heart of CrucibAI. It executes the 123-agent DAG with parallel phases, retry logic, fallback handling, and real-time progress reporting.

### 8.1 Core Function: `run_orchestration_with_dag()`

This async function is the main entry point for all builds. It:

1. Loads the project state (plan, stack, previous outputs).
2. Iterates through the 7 parallel phases.
3. Within each phase, runs all agents concurrently using `asyncio.gather()`.
4. Each agent runs through `_run_single_agent_with_retry()` which handles:
   - Context building from previous agent outputs
   - LLM call with model chain fallback
   - Timeout handling (configurable per agent)
   - Retry logic (up to 2 retries for high/critical agents)
   - Failure handling based on criticality level
5. Emits WebSocket events for real-time progress.
6. Stores results in project state.
7. Returns the complete build output.

### 8.2 Agent Execution Pipeline

```
User Prompt
    ↓
build/plan → Planner Agent → Structured Plan
    ↓
Orchestration Engine starts
    ↓
Phase 1: [Planner] → plan_text
    ↓
Phase 2: [Requirements Clarifier, Stack Selector, Content Agent, Legal] → parallel
    ↓
Phase 3: [Frontend, Backend, DB, Design, SEO, Brand, Auth, Payment, Email] → parallel
    ↓
Phase 4: [API Integration, Tests, Images, Scraping, Automation] → parallel
    ↓
Phase 5: [Security, Test Executor, UX, Performance, Layout, Validation, a11y, Webhook] → parallel
    ↓
Phase 6: [Deploy, Error Recovery, Memory] → parallel
    ↓
Phase 7: [PDF, Excel, Markdown, Docs, Monitoring, DevOps] → parallel
    ↓
Quality Gate → Score 0-100
    ↓
WebSocket: build_completed
    ↓
Frontend renders code in Sandpack preview
```

### 8.3 LLM Provider Chain

The `_get_model_chain()` function builds a fallback chain based on available API keys:

```python
# Default chain (all keys available):
["gemini-2.5-flash", "gpt-4o-mini", "claude-3-haiku"]

# If PREFER_LARGEST_MODEL=true:
["gemini-2.5-pro", "gpt-4o", "claude-3.5-sonnet"]

# Fallback behavior:
# Try provider 1 → if fails → try provider 2 → if fails → try provider 3
```

Users can supply their own API keys in Settings, which take priority over platform keys. The `_effective_api_keys()` function merges user keys with platform keys.

---

## 9. Quality Gate System

The quality gate (`quality.py`) scores generated code on a 0-100 scale across four dimensions:

### 9.1 Scoring Breakdown

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| **Frontend** | 25% | Has imports (>2), has components, has styling (className/style), has routing, lines of code (>50) |
| **Backend** | 25% | Has routes (@app/router), has auth (token/jwt), has error handling (try/except), has validation (schema/pydantic), lines of code (>50) |
| **Database** | 25% | Has tables (CREATE TABLE), has relationships (FOREIGN KEY), has indexes |
| **Tests** | 25% | Has test functions (def test_/it()), has assertions (assert/expect), has setup (beforeEach/setUp), lines of code (>20) |

### 9.2 Verdict Mapping

| Score | Verdict | Color |
|-------|---------|-------|
| 90-100 | Production Ready | Green |
| 80-89 | Good Quality | Green |
| 60-79 | Needs Improvement | Amber |
| 40-59 | Significant Issues | Orange |
| 0-39 | Major Rework Needed | Red |

The quality score is displayed in the InlineAgentMonitor component with a color-coded badge (ShieldCheck icon).

---

## 10. Authentication and Security Architecture

### 10.1 Authentication Flow

```
Registration:
  Client → POST /api/auth/register (email, password, name)
  Server → bcrypt hash password → store in MongoDB → return JWT

Login (no MFA):
  Client → POST /api/auth/login (email, password)
  Server → verify bcrypt → return JWT

Login (with MFA):
  Client → POST /api/auth/login (email, password)
  Server → verify bcrypt → return MFA temp token (short-lived)
  Client → POST /api/auth/verify-mfa (temp_token, totp_code)
  Server → verify TOTP → return JWT

Google OAuth:
  Client → GET /api/auth/google → redirect to Google
  Google → GET /api/auth/google/callback → verify code → create/find user → return JWT
```

### 10.2 Middleware Stack (7 Layers)

| Layer | Class | Purpose |
|-------|-------|---------|
| 1 | `HTTPSRedirectMiddleware` | Redirect HTTP to HTTPS in production |
| 2 | `RateLimitMiddleware` | Global rate limiting (60 req/min default, stricter for auth/payment) |
| 3 | `SecurityHeadersMiddleware` | X-Content-Type-Options, X-Frame-Options, CSP, HSTS |
| 4 | `CORSMiddleware` | Cross-origin resource sharing from env `CORS_ORIGINS` |
| 5 | `RequestValidationMiddleware` | Suspicious header detection, payload size limits |
| 6 | `RequestTrackerMiddleware` | Request logging with timing |
| 7 | `PerformanceMonitoringMiddleware` | Slow request detection and alerting |

### 10.3 Security Features

- **JWT tokens** with HS256 signing and configurable expiry
- **bcrypt** password hashing with salt
- **TOTP MFA** with pyotp (RFC 6238 compliant)
- **Backup codes** for MFA recovery
- **Disposable email detection** blocks temporary email services
- **Rate limiting** with per-IP and per-user buckets
- **RBAC** for admin routes (admin_role check)
- **Stripe webhook signature verification**
- **Security audit** module (`security_audit.py`) for internal checks

---

## 11. Automation Engine

The automation engine allows users to create scheduled or webhook-triggered workflows that invoke the same AI agents used in builds.

### 11.1 Trigger Types

| Type | Configuration | Example |
|------|--------------|---------|
| **Schedule** | Cron expression | `0 9 * * *` (daily at 9am) |
| **Webhook** | Secret in query/header | `POST /api/agents/webhook/{id}?secret=xxx` |
| **Manual** | API call | `POST /api/agents/run-internal` |

### 11.2 Action Types

| Type | Description | Configuration |
|------|------------|---------------|
| **HTTP** | Make HTTP request | method, url, headers, body |
| **Email** | Send email | to, subject, body (via Resend/SendGrid) |
| **Slack** | Send Slack message | webhook_url, message |
| **run_agent** | Invoke CrucibAI agent | agent_name, prompt |
| **Delay** | Wait before next step | seconds |
| **Approval** | Pause for human approval | approver |

### 11.3 Output Chaining

Actions can reference previous step outputs using the pattern `{{steps.N.output}}`. The executor substitutes these references at runtime, enabling data flow between steps.

### 11.4 Unique Competitive Advantage

> The `run_agent` action type is what makes CrucibAI unique. No other platform allows users to invoke the same AI agents that build applications as steps in automations. A user can create an automation that runs the Content Agent every Monday to refresh their landing page copy, or chain a Scraping Agent → Content Agent → Email Agent to monitor competitors.

---

## 12. Payments and Token Economy

### 12.1 Credit System

Users have a `credit_balance` stored in MongoDB. Credits are consumed when AI operations run. The conversion is handled by `_tokens_to_credits()`.

### 12.2 Stripe Integration

| Flow | Endpoint | Description |
|------|----------|-------------|
| **Checkout** | `POST /api/stripe/create-checkout-session` | Creates a Stripe checkout session for token purchase |
| **Webhook** | `POST /api/stripe/webhook` | Handles `checkout.session.completed` event, credits user |
| **Bundles** | `GET /api/tokens/bundles` | Returns available token bundles with pricing |

### 12.3 Token Bundles

The bundles are defined in the backend and returned by the `/tokens/bundles` endpoint. Users purchase bundles through Stripe checkout, and credits are automatically applied on webhook confirmation.

---

## 13. Deployment and Export System

### 13.1 Deployment Targets

| Target | Method | How It Works |
|--------|--------|-------------|
| **Vercel** | `POST /api/projects/{id}/deploy/vercel` | Uses Vercel API with user's token from Settings |
| **Netlify** | `POST /api/projects/{id}/deploy/netlify` | Uses Netlify API with user's token from Settings |
| **ZIP** | `GET /api/projects/{id}/deploy/zip` | Packages project files into downloadable ZIP |
| **GitHub** | `POST /api/export/github` | Creates/pushes to GitHub repository |

### 13.2 Production Deployment (Self-Hosted)

The Dockerfile uses a multi-stage build:

1. **Stage 1 (Node.js):** Builds the React frontend with `npm run build`
2. **Stage 2 (Python):** Installs backend dependencies, copies built frontend to `./static`, runs uvicorn

Railway deployment is configured via `railway.json` with automatic Dockerfile detection.

**Required environment variables for deployment:**

| Variable | Required | Purpose |
|----------|----------|---------|
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | Database name (default: `crucibai`) |
| `JWT_SECRET` | Yes | JWT signing secret |
| `OPENAI_API_KEY` | Recommended | Primary LLM provider |
| `ANTHROPIC_API_KEY` | Optional | Fallback LLM provider |
| `GEMINI_API_KEY` | Optional | Fallback LLM provider |
| `STRIPE_SECRET_KEY` | Optional | Stripe payments |
| `STRIPE_WEBHOOK_SECRET` | Optional | Stripe webhook verification |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth |
| `FRONTEND_URL` | Optional | Frontend URL for CORS/redirects |
| `CORS_ORIGINS` | Optional | Allowed CORS origins |
| `ADMIN_USER_IDS` | Optional | Comma-separated admin user IDs |

---

## 14. Admin Panel

The admin panel is accessible at `/app/admin` and protected by the `AdminRoute` component (checks `user.admin_role`). Backend routes under `/api/admin/*` require the `get_current_admin()` dependency.

### 14.1 Admin Views

| View | Route | Features |
|------|-------|----------|
| **Dashboard** | `/app/admin` | Total users, active users, new signups, revenue, active projects |
| **Users** | `/app/admin/users` | Search, list, view profiles, grant credits, suspend, downgrade |
| **User Profile** | `/app/admin/users/:id` | Detailed user info, projects, credits, referrals, actions |
| **Billing** | `/app/admin/billing` | Transaction history, revenue tracking |
| **Analytics** | `/app/admin/analytics` | Daily/weekly analytics, overview charts, reports |
| **Legal** | `/app/admin/legal` | Blocked requests, legal review queue |

---

## 15. Data Room: Database Schema

CrucibAI uses MongoDB with the following collections:

| Collection | Purpose | Key Fields |
|-----------|---------|------------|
| `users` | User accounts | id, email, password_hash, name, admin_role, credit_balance, mfa_secret, referral_code, api_keys, deploy_tokens, created_at |
| `projects` | Build projects | id, user_id, prompt, plan, state, phases, build_kind, quality_score, created_at |
| `project_logs` | Build event logs | project_id, event_type, agent_name, data, timestamp |
| `agent_status` | Per-agent build status | project_id, agent_name, status, output, tokens_used, duration |
| `user_agents` | User automations | id, user_id, name, trigger_type, trigger_config, actions, enabled, run_count |
| `agent_runs` | Automation run history | id, agent_id, user_id, triggered_by, status, started_at, finished_at, output_summary |
| `shares` | Shared project links | token, project_id, user_id, created_at |
| `credit_transactions` | Token purchase/usage | user_id, amount, type, stripe_session_id, timestamp |
| `prompts` | Saved prompts | user_id, text, category, created_at |
| `exports` | Export records | user_id, project_id, type, url, created_at |
| `templates` | Project templates | name, description, files, category |
| `examples` | Example projects | name, description, files, category |

---

## 16. Engine Room: Middleware, Performance, and Observability

### 16.1 Rate Limiting

The `RateLimitMiddleware` implements a token bucket algorithm with configurable limits:

| Endpoint Pattern | Limit | Window |
|-----------------|-------|--------|
| Global default | 60 requests | Per minute |
| `/api/auth/*` | 10 requests | Per minute |
| `/api/stripe/*` | 5 requests | Per minute |
| `/api/build/*` | 20 requests | Per minute |

### 16.2 Security Headers

Every response includes:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

### 16.3 Performance Monitoring

The `PerformanceMonitoringMiddleware` logs request duration and flags slow requests (>5s). The `RequestTrackerMiddleware` assigns unique request IDs for tracing.

---

## 17. Connectivity Map

This section maps every frontend-to-backend connection, showing exactly where each API call originates and what it does.

### 17.1 Authentication Flow

```
AuthPage.jsx
  → POST /api/auth/register    (registration form)
  → POST /api/auth/login        (login form)
  → POST /api/auth/verify-mfa   (MFA code entry)
  → GET  /api/auth/google       (Google OAuth button)

Layout.jsx
  → GET  /api/auth/me           (on mount, verify token)
  → GET  /api/dashboard/stats   (sidebar stats)

Settings.jsx
  → POST /api/mfa/setup         (enable MFA)
  → POST /api/mfa/verify        (verify MFA setup)
  → POST /api/mfa/disable       (disable MFA)
  → GET  /api/workspace/env     (load API keys)
  → POST /api/workspace/env     (save API keys)
  → GET  /api/users/me/deploy-tokens  (load deploy tokens)
  → PATCH /api/users/me/deploy-tokens (save deploy tokens)
```

### 17.2 Build Flow

```
Dashboard.jsx
  → POST /api/build/plan        (generate plan from prompt)
  → navigates to /app/workspace with plan in location.state

Workspace.jsx
  → POST /api/ai/chat/stream    (streaming build, SSE)
  → POST /api/ai/chat           (non-streaming build)
  → WS   /ws/projects/{id}/progress  (real-time progress)
  → POST /api/ai/validate-and-fix    (auto-fix errors)
  → POST /api/ai/quality-gate        (quality scoring)
  → POST /api/ai/explain-error       (error explanation)
  → POST /api/ai/suggest-next        (next feature suggestions)

AgentMonitor.jsx
  → GET  /api/projects/{id}/phases   (phase status)
  → GET  /api/projects/{id}/logs     (build logs)
  → POST /api/projects/{id}/retry-phase  (retry failed phase)
  → WS   /ws/projects/{id}/progress  (real-time updates)
```

### 17.3 Automation Flow

```
AgentsPage.jsx
  → GET  /api/agents             (list user agents)
  → POST /api/agents             (create agent)
  → GET  /api/agents/templates   (get templates)
  → GET  /api/agents/activity    (recent activity)

External Trigger:
  → POST /api/agents/webhook/{id}?secret=xxx  (webhook trigger)

Internal:
  → Scheduler → POST /api/agents/run-internal  (cron trigger)
  → Executor runs actions: HTTP → Email → Slack → run_agent → delay → approval
```

### 17.4 Payment Flow

```
Pricing.jsx / TokenCenter.jsx / PaymentsWizard.jsx
  → GET  /api/tokens/bundles     (load bundles)
  → POST /api/stripe/create-checkout-session  (start checkout)
  → Stripe hosted checkout page
  → Stripe → POST /api/stripe/webhook  (payment confirmed)
  → Server credits user account

TokenCenter.jsx
  → GET  /api/tokens/history     (transaction history)
  → GET  /api/tokens/usage       (usage analytics)
```

---

## 18. Competitive Analysis

### 18.1 CrucibAI vs. Competitors — Feature Matrix

| Feature | CrucibAI | Lovable | Bolt.new | Cursor | Manus | n8n | Zapier |
|---------|----------|---------|----------|--------|-------|-----|--------|
| **AI Code Generation** | 123 agents | Single LLM | Single LLM | Single LLM | Multi-agent | No | No |
| **Full-Stack Generation** | Frontend + Backend + DB | Frontend only | Frontend only | Editor assist | Full-stack | No | No |
| **Mobile App Generation** | Expo + Store Pack | No | No | No | Yes | No | No |
| **Live Preview** | Sandpack real-time | Yes | Yes | No | Yes | No | No |
| **Agent Orchestration** | 7-phase DAG | No | No | No | Yes | No | No |
| **Quality Gate** | 0-100 scoring | No | No | No | No | No | No |
| **User Automations** | Schedule + Webhook | No | No | No | No | Yes | Yes |
| **Same AI in Automations** | Yes (run_agent) | No | No | No | No | No | No |
| **Self-Hosted** | Docker + Railway | No | No | No | No | Yes | No |
| **MFA Authentication** | TOTP + Backup Codes | No | No | No | No | No | No |
| **Admin Panel** | Full RBAC | No | No | No | No | No | No |
| **Stripe Billing** | Built-in | No | No | No | No | No | Built-in |
| **Multi-LLM Support** | 4 providers | 1 | 1 | 2 | Multiple | No | No |
| **Voice Input** | Whisper transcription | No | No | No | No | No | No |
| **Image-to-Code** | Yes | No | Yes | No | Yes | No | No |
| **Deploy Targets** | Vercel, Netlify, ZIP, GitHub | Vercel | Netlify | No | Yes | No | No |
| **IDE Extensions** | VS Code, JetBrains, Sublime, Vim | No | No | Native | No | No | No |

### 18.2 Why CrucibAI Wins

**vs. Lovable:** Lovable generates frontend-only code with a single LLM call. CrucibAI generates full-stack applications (frontend + backend + database + tests + deployment config) using 123 specialized agents with quality scoring. Lovable has no automation capability; CrucibAI's automation engine lets users invoke the same AI agents in scheduled workflows.

**vs. Bolt.new:** Bolt generates frontend code in a sandboxed environment. CrucibAI goes further with backend generation, database design, security scanning, accessibility checking, and one-click deployment to multiple targets. Bolt has no user management, no billing, no admin panel.

**vs. Cursor:** Cursor is an AI-enhanced code editor — it assists developers who already know how to code. CrucibAI is a platform for non-developers and developers alike — it builds complete applications from natural language. Cursor has no deployment, no automation, no agent orchestration.

**vs. Manus:** Manus is the closest competitor in terms of multi-agent orchestration. However, CrucibAI differentiates with: (1) the automation engine where agents are invokable in user workflows, (2) self-hosted deployment option, (3) built-in billing and admin panel, (4) 123 agents vs. Manus's estimated 50, (5) quality gate scoring.

**vs. n8n / Zapier:** These are pure automation platforms with no code generation capability. CrucibAI combines both: build applications AND automate workflows, with the unique ability to use the same AI agents in both contexts.

---

## 19. Gap Analysis: What Is Missing, Broken, or Incomplete

This section provides an honest assessment of what needs work. Every item is categorized by severity and effort.

### 19.1 Critical Gaps (Must Fix)

| # | Issue | Location | Impact | Effort |
|---|-------|----------|--------|--------|
| 1 | **Dashboard intent detection needs backend AI** | `Dashboard.jsx` `detectIntent()` | Currently uses keyword matching; should use LLM for accurate intent classification | Medium |
| 2 | **WebSocket connection may fail silently** | `Workspace.jsx` WS handler | No reconnection logic; if WS drops during build, user loses progress visibility | Medium |
| 3 | **Task saving endpoint not implemented** | `Workspace.jsx` → `POST /api/tasks` | Frontend calls `/api/tasks` to save completed builds, but this route does not exist in `server.py` | Low |
| 4 | **Voice transcription requires backend** | `Dashboard.jsx` voice handler | Frontend records audio but the transcription call to `/api/voice/transcribe` needs a running backend with Whisper or equivalent | Low |

### 19.2 Important Gaps (Should Fix)

| # | Issue | Location | Impact | Effort |
|---|-------|----------|--------|--------|
| 5 | **No real-time collaboration** | `services/Collaboration.js` | Files exist but collaboration is not wired end-to-end | High |
| 6 | **Agent DAG phases 2-4 agents are LLM-prompt-only** | `agent_dag.py` agents 40-123 | These agents have system prompts but no specialized tool integration (they generate text, not execute actions) | High |
| 7 | **No end-to-end tests running in CI** | `frontend/e2e/` | Playwright tests exist but CI workflow may not be fully configured | Medium |
| 8 | **Deploy tokens stored in user document** | `server.py` deploy-tokens | Vercel/Netlify tokens stored in MongoDB user document — should use encrypted secrets | Medium |
| 9 | **No email verification on registration** | `server.py` `/auth/register` | Users can register with any email without verification | Low |

### 19.3 Nice-to-Have Improvements

| # | Issue | Location | Impact | Effort |
|---|-------|----------|--------|--------|
| 10 | **Prompt library is static** | `server.py` `/prompts/templates` | Templates are hardcoded; should be admin-configurable | Low |
| 11 | **No project versioning/history** | `server.py` projects | Users cannot revert to previous build versions | Medium |
| 12 | **No team/organization support** | Entire platform | Single-user only; no shared workspaces | High |
| 13 | **Mobile app preview** | `Workspace.jsx` | Sandpack shows web preview only; no mobile device frame | Medium |
| 14 | **No offline/PWA support** | Frontend | App requires internet connection | Low |

---

## 20. Roadmap

### Phase 1: Current (Implemented)
- 123-agent DAG with 7 parallel phases
- Full-stack generation (web + mobile)
- Automation engine (schedule + webhook + run_agent)
- Stripe billing and token economy
- Admin panel with RBAC
- Multi-LLM support (OpenAI, Anthropic, Gemini)
- MFA authentication
- Deploy to Vercel, Netlify, ZIP, GitHub
- Quality gate scoring
- Voice input with transcription
- Image-to-code conversion

### Phase 2: Next Quarter
- Real-time collaboration (multi-user editing)
- Project versioning and rollback
- Enhanced agent tool integration (agents execute real operations, not just generate text)
- Email verification on registration
- Encrypted secrets storage for deploy tokens
- WebSocket reconnection logic
- Team/organization support (shared workspaces)

### Phase 3: Future
- Mobile device frame preview
- Plugin marketplace for community agents
- White-label deployment for enterprise
- On-premise installation guide
- SOC 2 Type II certification
- HIPAA compliance mode
- Custom LLM provider support (Ollama, local models)

---

## 21. Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `MONGO_URL` | Yes | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | Yes | `crucibai` | Database name |
| `JWT_SECRET` | Yes | None | JWT signing secret |
| `OPENAI_API_KEY` | Recommended | None | OpenAI API key |
| `ANTHROPIC_API_KEY` | Optional | None | Anthropic API key |
| `GEMINI_API_KEY` | Optional | None | Google Gemini API key |
| `GOOGLE_API_KEY` | Optional | None | Google API key (fallback for Gemini) |
| `LLM_API_KEY` | Optional | None | Generic LLM API key (fallback) |
| `STRIPE_SECRET_KEY` | Optional | None | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Optional | None | Stripe webhook signing secret |
| `GOOGLE_CLIENT_ID` | Optional | None | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Optional | None | Google OAuth client secret |
| `FRONTEND_URL` | Optional | `http://localhost:3000` | Frontend URL for CORS and redirects |
| `CORS_ORIGINS` | Optional | None | Comma-separated allowed origins |
| `ADMIN_USER_IDS` | Optional | None | Comma-separated admin user IDs |
| `CRUCIBAI_PUBLIC_API_KEYS` | Optional | None | Public API keys for external access |
| `CRUCIBAI_INTERNAL_TOKEN` | Optional | None | Internal agent run token |
| `PREFER_LARGEST_MODEL` | Optional | `false` | Use largest available model |
| `RUN_IN_SANDBOX` | Optional | `1` | Enable sandbox execution |
| `SMTP_HOST` | Optional | None | SMTP server for emails |
| `SMTP_PORT` | Optional | `587` | SMTP port |
| `SMTP_USER` | Optional | None | SMTP username |
| `SMTP_PASSWORD` | Optional | None | SMTP password |
| `SMTP_FROM` | Optional | `noreply@crucibai.com` | SMTP from address |
| `ENTERPRISE_CONTACT_EMAIL` | Optional | None | Enterprise contact email |
| `CRUCIBAI_BRANDING_URL` | Optional | None | Custom branding URL |
| `BACKEND_PUBLIC_URL` | Optional | `http://localhost:8000` | Public backend URL |
| `API_BASE_URL` | Optional | `http://localhost:8000` | API base URL |

---

## 22. Developer Onboarding Guide

### 22.1 Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/disputestrike/newcrucib.git
cd newcrucib

# 2. Start the backend
cd backend
pip install -r requirements.txt
export MONGO_URL="mongodb://localhost:27017"
export DB_NAME="crucibai"
export JWT_SECRET="your-secret-here"
export OPENAI_API_KEY="sk-..."  # or GEMINI_API_KEY
uvicorn server:app --host 0.0.0.0 --port 8000

# 3. Start the frontend (new terminal)
cd frontend
npm install
npm start
# Opens http://localhost:3000

# 4. (Optional) Use the PowerShell script
.\run-dev.ps1
```

### 22.2 Key Files to Understand First

1. **`backend/server.py`** — The entire backend in one file. Start here to understand all routes.
2. **`backend/orchestration.py`** — How builds work. Read `run_orchestration_with_dag()`.
3. **`backend/agent_dag.py`** — The 123-agent configuration. Understand dependencies and phases.
4. **`frontend/src/App.js`** — All routes and the auth context.
5. **`frontend/src/pages/Workspace.jsx`** — The most complex page. Understand the build flow.
6. **`frontend/src/pages/Dashboard.jsx`** — The home screen with intent detection.
7. **`frontend/src/components/Layout.jsx`** — The 3-column layout wrapper.

### 22.3 Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Single-file backend** | All 178 routes in `server.py` for simplicity and fast iteration. Can be split later. |
| **MongoDB over SQL** | Flexible schema for diverse project types. No migrations needed. |
| **Multi-LLM with fallback** | Resilience — if one provider is down, the system continues. |
| **Sandpack for preview** | Real-time rendering without a server. Runs entirely in the browser. |
| **JWT over sessions** | Stateless auth scales horizontally. MFA adds security layer. |
| **CRA over Vite** | Established tooling with CRACO for customization. Migration to Vite planned. |

---

## 23. Appendix: File Inventory

### 23.1 Backend Files

| File | Lines | Purpose |
|------|-------|---------|
| `server.py` | 5,580 | Main FastAPI application with all 178 routes |
| `orchestration.py` | ~500 | DAG orchestration engine |
| `agent_dag.py` | ~400 | 123-agent DAG configuration |
| `agent_real_behavior.py` | ~300 | Real behavior definitions per agent |
| `real_agent_runner.py` | ~200 | LLM execution for agents |
| `project_state.py` | ~150 | Project state persistence |
| `quality.py` | ~120 | Code quality scoring |
| `code_quality.py` | ~100 | Extended quality analysis |
| `middleware.py` | ~330 | 7 middleware classes |
| `security_audit.py` | ~200 | Internal security audit |
| `automation/models.py` | ~80 | Pydantic models for agents |
| `automation/executor.py` | ~200 | Action executor (HTTP, email, Slack, run_agent) |
| `automation/scheduler.py` | ~100 | Cron scheduler for agents |
| `tools/file_agent.py` | ~100 | File operations tool |
| `tools/api_agent.py` | ~100 | API calling tool |
| `tools/browser_agent.py` | ~100 | Browser automation tool |
| `tools/deployment_operations.py` | ~100 | Deployment operations |
| `tools/database_operations.py` | ~100 | Database operations |

### 23.2 Frontend Files (Key)

| File | Lines | Purpose |
|------|-------|---------|
| `App.js` | 296 | Route definitions, auth context, theme |
| `pages/Workspace.jsx` | 2,100+ | Primary build workspace |
| `pages/Dashboard.jsx` | 538 | Home screen with intent detection |
| `pages/Builder.jsx` | 686 | Public code playground |
| `pages/BlogPost.jsx` | 598 | Blog post viewer |
| `pages/AgentMonitor.jsx` | 602 | Build monitoring dashboard |
| `pages/AuthPage.jsx` | 499 | Login/register/MFA |
| `pages/LandingPage.jsx` | ~400 | Public marketing page |
| `pages/AgentsPage.jsx` | 322 | Automation management |
| `pages/DocsPage.jsx` | 337 | Documentation |
| `pages/Settings.jsx` | ~300 | User settings |
| `pages/TokenCenter.jsx` | ~250 | Token management |
| `pages/Pricing.jsx` | ~200 | Pricing page |
| `components/Layout.jsx` | 203 | 3-column layout |
| `components/Sidebar.jsx` | 226 | Navigation sidebar |
| `components/InlineAgentMonitor.jsx` | 253 | Build progress monitor |
| `components/RightPanel.jsx` | 259 | Right sidebar |
| `components/DeployButton.jsx` | 259 | Deploy modal |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document Title** | CrucibAI Source Bible |
| **Version** | 1.0 |
| **Date** | February 21, 2026 |
| **Total API Routes** | 178 |
| **Total AI Agents** | 123 |
| **Total Lines of Code** | 55,467 |
| **Total Frontend Pages** | 42 |
| **Total Frontend Components** | 23 |
| **Repository** | github.com/disputestrike/newcrucib |
| **Branch** | main |
| **Last Commit** | ee396a5 |

---

*This document is the single source of truth for CrucibAI. Every function, every route, every agent, every connection is documented here. Share it with investors, developers, and team members. Nothing is hidden.*
