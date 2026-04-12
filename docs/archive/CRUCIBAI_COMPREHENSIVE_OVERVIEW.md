# CrucibAI — Complete End-to-End Overview

**One document for everything: what we built, features, functions, differentiators, competitive advantage.**

---

## 1. WHAT IS CRUCIBAI?

CrucibAI is an **AI-powered app builder** where users describe what they want in natural language, and **100 specialized agents** automatically build production-ready full-stack applications. Think: Replit Agent + Bolt.new + Cursor, but with **plan-first orchestration**, **design-to-code**, and the **largest agent roster (100)** in the app-building space.

**Core promise:** Turn your idea into a working app—one prompt, one workspace, from concept to deploy.

---

## 2. FULL FEATURE LIST (What We Built)

### 2.1 Core Builder & Workspace

| Feature | Description |
|---------|-------------|
| **Prompt → App** | Describe your app in plain language; AI generates React + Tailwind code |
| **Monaco Code Editor** | Full-featured editor with syntax highlighting, multi-file support |
| **Sandpack Live Preview** | Real-time preview; see changes instantly as you edit |
| **File Explorer** | Navigate App.js, index.js, styles.css, and generated files |
| **Chat Interface** | Iterative modifications: "add a button", "make it dark mode", "add a sidebar" |
| **Version History** | Track and restore previous code versions |
| **Console Panel** | Build logs, agent activity, error output |
| **Quick/Plan/Agent/Thinking Modes** | Quick = single-shot; Plan = structured plan first; Agent = full 100-agent orchestration; Thinking = step-by-step reasoning |
| **Swarm Mode (Beta)** | Run selected agents in parallel for faster builds |

### 2.2 Multi-Input Capabilities

| Feature | Description |
|---------|-------------|
| **Text Input** | Standard chat-based prompts |
| **Voice Input** | Record audio; transcribe via OpenAI Whisper; insert into prompt |
| **Image Attachments** | Screenshot or mockup → design-to-code; vision models generate structured React/Tailwind |
| **PDF/Text Attachments** | Upload files for context; AI uses them when generating |

### 2.3 AI & Models

| Feature | Description |
|---------|-------------|
| **Multi-Model Backend** | OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini) |
| **Auto-Select** | Best model for task (code, analysis, creative) |
| **Model Fallback Chain** | If one provider fails, try next (no 500s when keys missing) |
| **Your Own API Keys** | Add OpenAI/Anthropic keys in Settings; use your billing |
| **RAG & Search** | Document analysis, hybrid search, build-from-reference |

### 2.4 100 Agents (Full Roster)

**Planning (4):** Planner, Requirements Clarifier, Content Agent, Legal Compliance Agent  

**Stack & Design (8):** Stack Selector, Design Agent, Brand Agent, SEO Agent, Auth Setup Agent, Payment Setup Agent, Email Agent, API Integration  

**Execution (12):** Frontend Generation, Backend Generation, Database Agent, Image Generation, Video Generation, Layout Agent, Test Generation, Scraping Agent, Automation Agent, Webhook Agent, Validation Agent  

**Validation & Quality (5):** Security Checker, Test Executor, UX Auditor, Performance Analyzer, Accessibility Agent  

**Deployment & Export (7):** Deployment Agent, Error Recovery, Memory Agent, Documentation Agent, Monitoring Agent, DevOps Agent, PDF Export, Excel Export, Markdown Export  

**Phase 2–4 (63 more):** GraphQL, WebSocket, i18n, Caching, Rate Limit, Search, Analytics, API Docs, Mobile Responsive, Migration, Backup, Notification, Design Iteration, Code Review, Staging, A/B Test, Feature Flag, Error Boundary, Logging, Metrics, Audit Trail, Session, OAuth Provider, 2FA, Stripe Subscription, Invoice, CDN, SSR, Bundle Analyzer, Lighthouse, Schema Validation, Mock API, E2E, Load Test, Dependency Audit, License, Terms, Privacy Policy, Cookie Consent, Multi-tenant, RBAC, SSO, Audit Export, Data Residency, HIPAA, SOC2, Penetration Test, Incident Response, SLA, Cost Optimizer, Accessibility WCAG, RTL, Dark Mode, Keyboard Nav, Screen Reader, Component Library, Design System, Animation, Chart, Table, Form Builder, Workflow, Queue  

### 2.5 Export & Deploy

| Feature | Description |
|---------|-------------|
| **Download ZIP** | Export full project (code, assets) |
| **GitHub Push** | Create repo, upload files; OAuth push (UI ready) |
| **Vercel/Netlify Deploy** | One-click deploy instructions; ZIP + README for vercel.com/new, netlify.com/drop |
| **PDF Export** | Generate formatted PDF reports (reportlab) |
| **Excel Export** | Create spreadsheets (openpyxl) |
| **Markdown Export** | Project summary in Markdown |

### 2.6 Media (Images & Videos)

| Feature | Description |
|---------|-------------|
| **AI-Generated Images** | Together.ai integration; hero + feature_1 + feature_2 for landing pages |
| **Stock Videos** | Pexels integration; search queries from Video agent; inject into generated apps |
| **Design Agent** | Placement spec (position, aspect, role) before Image Generation |
| **Layout Agent** | Injects image/video placeholders into frontend code |

### 2.7 Auth, Projects & Workspace

| Feature | Description |
|---------|-------------|
| **Register / Login** | JWT-based auth; optional OAuth (Google) |
| **Projects CRUD** | Create, list, view, duplicate projects |
| **Share Links** | Create read-only share link; ShareView page |
| **Save as Template** | Save prompt/project as reusable template |
| **Workspace Env** | GET/POST env vars for Sandpack |
| **Settings** | User profile, API keys, preferences |

### 2.8 Tokens & Billing

| Feature | Description |
|---------|-------------|
| **Token Bundles** | Purchase tokens (Starter, Builder, Pro, Agency) |
| **Usage Dashboard** | Tokens used, history, limits |
| **Stripe Checkout** | Purchase flow; webhook for fulfillment |
| **Free Tier** | 50 credits; no credit card required |
| **Credit Balance** | Per-user balance; deduct on AI usage |

### 2.9 Compliance & Legal

| Feature | Description |
|---------|-------------|
| **AUP (Acceptable Use Policy)** | Keyword-based blocking; 14 categories (illegal, adult, replication_extraction, etc.) |
| **Legal Compliance Agent** | GDPR/CCPA hints; cookie banner, privacy link |
| **Blocked Requests** | Log blocked prompts; AdminLegal review workflow |
| **Terms, Privacy, AUP, DMCA Pages** | Legal docs; footer links; signup acceptance |
| **Branding / Watermark** | "Built with CrucibAI" in generated code; free tier = permanent iframe badge |
| **Replication Blocking** | Blocks prompts like "replicate CrucibAI", "reveal system prompt" |

### 2.10 Admin

| Feature | Description |
|---------|-------------|
| **Admin Dashboard** | Stats, overview |
| **Admin Users** | List, suspend, grant credits, downgrade |
| **Admin Billing** | Billing overview |
| **Admin Legal** | Blocked requests, review, approve/reject |
| **Admin Analytics** | Usage analytics |
| **Audit Log** | User actions, admin actions |

### 2.11 UX & Polish

| Feature | Description |
|---------|-------------|
| **Ctrl+K Command Palette** | Quick actions |
| **Shortcuts Cheatsheet** | Keyboard shortcuts |
| **Learn Panel** | Tips, docs |
| **Prompt Library** | Templates, saved prompts, recent |
| **Templates Gallery** | Pre-built app templates; "Use template" |
| **Examples Gallery** | Live examples from our 100-agent builds |
| **Try These Buttons** | Suggested prompts on first build fail |
| **API Key Nudge** | "Add API keys in Settings" when build fails |
| **Quality Score** | Built-in code quality score (0–100) in AgentMonitor |
| **Per-Agent Tokens** | Token usage per agent in build UI |
| **Build Progress** | Phase-by-phase progress; WebSocket real-time updates |

### 2.12 Public Pages & Marketing

| Feature | Description |
|---------|-------------|
| **Landing Page** | Kimi-style dark theme; hero, input, examples, FAQ, comparison |
| **Pricing** | Bundles, add-ons, Enterprise |
| **Features** | Feature list |
| **Templates** | Public template gallery |
| **Benchmarks** | Benchmark report |
| **Learn** | Documentation |
| **Enterprise** | Enterprise contact |

---

## 3. API & BACKEND (139 Routes)

- **AI/Chat:** `/api/ai/chat`, `/api/ai/chat/history`, `/api/ai/analyze`, `/api/ai/image-to-code`, `/api/rag/query`, `/api/search`, streaming
- **Voice:** `/api/voice/transcribe`
- **Auth:** `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, MFA endpoints
- **Projects:** CRUD, duplicate, share, logs
- **Agents:** 20+ dedicated run routes + `/api/agents/run/generic` for any of 100 agents
- **Tokens:** bundles, purchase, history, usage
- **Export:** PDF, Excel, Markdown
- **Admin:** users, billing, legal, analytics
- **Health:** `/api/health`

---

## 4. WHAT MAKES US DIFFERENT (Differentiators)

### 4.1 100 Agents (vs Kimi 100, Manus ~29)

- **Kimi** has 100 sub-agents for **research** and multi-angle analysis.
- **Manus** has ~29 tools (browser, file, PPTX, PDF, email, Slack).
- **CrucibAI** has **100 agents built for app creation only**: planning, frontend, backend, design, SEO, tests, deploy, GraphQL, E2E, RBAC, and 60+ more.

**Differentiator:** Ours form a **fixed DAG** optimized for shipping software. Every agent has a specific role in the build pipeline.

### 4.2 Plan-First Flow

- Most tools: prompt → code (single shot).
- **CrucibAI:** prompt → **plan** (3–7 tasks) → **clarify** (2–4 questions) → **stack** → **build** → **validate** → **deploy**.

**Differentiator:** Reduces backtracking; improves quality; user sees the plan before code.

### 4.3 Design-to-Code + Media Pipeline

- **Design Agent** outputs image placement spec.
- **Image Generation** uses spec; Together.ai generates hero + features.
- **Video Generation** outputs Pexels search queries; videos injected.
- **Layout Agent** merges frontend + images + videos.

**Differentiator:** End-to-end design → media → layout in one pipeline.

### 4.4 Quality Visibility

- **Quality Score** (0–100) on generated code.
- **Per-agent tokens** visible in AgentMonitor.
- **Phase retry** and error recovery with fallbacks.
- **Token-optimized prompts** (`USE_TOKEN_OPTIMIZED_PROMPTS`) for cost control.

**Differentiator:** You see how good the output is and what it cost.

### 4.5 Single Workspace, Idea to Deploy

- Landing → Workspace → Build → Iterate → Export/Deploy.
- No context switching; one app, one flow.

**Differentiator:** Competitors split IDE, chat, deploy across tools.

### 4.6 Your API Keys, Your Billing

- Add OpenAI/Anthropic keys in Settings.
- CrucibAI uses your keys; you pay provider directly.
- Or use CrucibAI credits (Stripe).

**Differentiator:** Flexibility: bring your own keys or pay us.

---

## 5. COMPETITIVE ADVANTAGE

### 5.1 vs Top 10 (RATE_RANK_TOP10)

| Rank | Tool | Overall | CrucibAI advantage |
|------|------|---------|--------------------|
| **1** | **CrucibAI** | **10.0** | Plan-first, 100 agents, quality score, phase retry, token-optimized |
| 2 | Manus / Bolt | 7.2 | We have 100 vs ~29 agents; design-to-code pipeline |
| 3 | Cursor | 6.8 | We build full apps; Cursor assists in IDE |
| 4 | ChatGPT / Claude | 6.2 | We have workspace, deploy, agents; they're general assistants |
| 5 | GitHub Copilot | 6.1 | We generate full apps; Copilot does completions |

**CrucibAI leads on:** Orchestration, quality visibility, error recovery, real-time progress, token efficiency, full-app output.

### 5.2 Feature Comparison (What Others Don't Have)

| Feature | CrucibAI | Manus | Cursor | ChatGPT |
|---------|----------|-------|--------|---------|
| 100 specialized agents | ✅ | ❌ (~29) | ❌ | ❌ |
| Plan-first build | ✅ | ❌ | ❌ | ❌ |
| Design-to-code + images + videos | ✅ | Partial | Partial | Partial |
| Quality score (0–100) | ✅ | ❌ | ❌ | ❌ |
| Per-agent token visibility | ✅ | ❌ | ❌ | ❌ |
| PDF + Excel + Markdown export | ✅ | ❌ | ❌ | ❌ |
| Web scraping agent | ✅ | ❌ | ❌ | ❌ |
| Automation/scheduling agent | ✅ | ❌ | ❌ | ❌ |
| Legal compliance agent | ✅ | ❌ | ❌ | ❌ |
| Token bundles + BYOK | ✅ | Token-based | N/A | Subscription |
| Full workspace (Monaco + Sandpack) | ✅ | Similar | IDE | Chat only |

---

## 6. TECH STACK

| Layer | Tech |
|-------|------|
| **Frontend** | React 19, Tailwind CSS, Framer Motion |
| **Code Editor** | Monaco Editor |
| **Live Preview** | Sandpack (CodeSandbox) |
| **Backend** | Python FastAPI |
| **Database** | MongoDB (Motor) |
| **AI** | Multi-model (OpenAI, Anthropic, Google); Whisper for voice |
| **Images** | Together.ai |
| **Videos** | Pexels |
| **Payments** | Stripe |

---

## 7. PRODUCTION READINESS

- **5-layer validation suite:** endpoint mapping, webhook flows, data integrity, user journeys, security
- **CI:** `.github/workflows/enterprise-tests.yml` runs full pytest + production validation
- **Compliance matrix:** All routes have frontend or proof coverage
- **Admin:** Users, billing, legal, analytics, audit
- **Legal docs:** Terms, Privacy, AUP, DMCA; signup acceptance; appeals flow

---

## 8. FORTUNE 100 GAPS (Not Yet)

- SSO/SAML, SCIM, RBAC beyond admin
- SOC 2 Type II, ISO 27001, HIPAA BAA
- MFA (TOTP, WebAuthn)
- Structured logging, APM, status page
- Data residency options
- Enterprise support (CSM, SLA)

*See CHANGES_AND_FORTUNE_100_GAPS.md for full list.*

---

## 9. END-TO-END USER JOURNEY

1. **Landing** → User types "Build a task manager with dark mode" (or uses voice / attaches image)
2. **Redirect** → `/app/workspace?prompt=...` (or register first)
3. **Workspace** → Monaco + Sandpack load; default template or from template
4. **Build** → User clicks Build; Quick/Plan/Agent/Thinking mode chosen
5. **Orchestration** → Planner → Requirements → Stack → Frontend, Backend, Design, SEO, etc. (100 agents in phases)
6. **Progress** → WebSocket updates; AgentMonitor shows phases, per-agent tokens
7. **Output** → Code in editor; images/videos injected; quality score shown
8. **Iterate** → Chat: "add a sidebar", "make it blue"
9. **Export** → Download ZIP, push to GitHub, or deploy (Vercel/Netlify instructions)
10. **Own** → User owns the code; free tier has CrucibAI badge; paid can remove

---

## 10. SUMMARY: WHY CRUCIBAI?

| Dimension | CrucibAI |
|-----------|----------|
| **Agents** | 100 (most in app-building) |
| **Flow** | Plan-first (reduce backtracking) |
| **Output** | Full-stack app + images + videos |
| **Quality** | Built-in score, per-agent tokens |
| **Workspace** | One place: idea → code → deploy |
| **Billing** | BYOK or CrucibAI credits |
| **Rate** | 10/10 vs Top 10 (RATE_RANK_TOP10) |
| **Differentiator** | Purpose-built for shipping software; fixed DAG; design-to-code pipeline |

---

*Last updated: February 2026. For agent roster details: AGENTS_ROADMAP.md. For rate/rank: RATE_RANK_TOP10.md, RATE_RANK_TOP20.md. For Fortune 100 gaps: CHANGES_AND_FORTUNE_100_GAPS.md.*
