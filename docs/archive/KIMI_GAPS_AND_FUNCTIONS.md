# Kimi Gaps, Rate/Rank/Compare After Implementation, and Full Function List

This document: **(1)** what we left out from Kimi in the original plan, **(2)** our rank, rate, and compare once we implement Kimi look + form + function, **(3)** a single source of truth for **all functions we are implementing** (existing + planned), with a quick project review.

---

## 1. What We Left Out from Kimi (Gaps)

These are Kimi elements we did **not** fully include in `KIMI_INSPIRED_PLAN.md`. Consider adding them to content or roadmap.

### 1.1 Content & structure

| Left out | Kimi has it | Suggested for CrucibAI |
|----------|--------------|------------------------|
| **Productized landing sections** | “Kimi for Docs”, “Kimi for Slides”, “Kimi for Sheets”, “Kimi Website Builder” — each with headline, short copy, and “Try Kimi Docs” CTA | Add “CrucibAI for Dashboards”, “CrucibAI for Landing Pages”, “CrucibAI for Internal Tools” (or similar) with short copy + CTA. |
| **Comparison table** | “Kimi AI vs Other AI Tools” — table: Tool, Best for, Strongest at, If you should pick it (vs ChatGPT, Claude, Gemini, Copilot, Perplexity, etc.) | Add “CrucibAI vs Others” table (vs Cursor, Manus, ChatGPT, Bolt, etc.) — Phase 2 optional. |
| **Key modules / stack section** | “Key Module / Research” — list of modules (Kimi K2, Kimi-Researcher, Kimi-Dev, Kimi-Audio, etc.) with one-line descriptions | Add “How CrucibAI works” or “Stack” section: Plan-first, 20 agents, Frontend/Backend/Test/Deploy, etc. |
| **Very long numbered FAQ** | 50–70 numbered questions (What is X?, Is it free?, Design-to-code?, K2 vs K2.5?, etc.) | Expand FAQ to 20–30 and number them (Kimi-style). |
| **Named modes in UI** | “Instant”, “Thinking”, “Agent”, “Agent Swarm (Beta)” as selectable modes | Add mode selector in Workspace: e.g. “Quick” vs “Plan” vs “Agent” (when agent mode exists). |
| **Free credits messaging** | “Free credits available to high tier users” for swarm | Add clear “Free tier” / “Free credits” copy on Pricing and landing. |
| **Tier names in pricing** | Free / Individual Pro / Professional / Enterprise with price ranges | We have token bundles; optionally add tier labels (Starter, Pro, Team, Enterprise) alongside. |
| **Multiple product CTAs** | “Try Kimi K2”, “Try Kimi Docs”, “Try Kimi Slides”, etc. | Add secondary CTAs: “Try workspace”, “View templates”, “See pricing”. |
| **“Log in to sync chat history”** | Shown in app mockup | Add “Sign in to save projects and sync” near landing chat or after first build. |
| **Mobile app link** | “Mobile App” in nav | Only if we have a mobile app or PWA; else skip or “Coming soon”. |
| **Third-party platforms** | “OpenRouter, Kilo Code, Hugging Face” | If we support API or integrations, add “API & integrations” line. |
| **Benchmarks section** | “How Does Kimi AI Perform on Benchmarks?” (MMLU, HumanEval, GSM8K) | Optional: “Performance” or “Quality” section with metrics if we have them. |
| **Limitations section** | “What Are the Limitations of Kimi AI?” | Add “Limitations” in FAQ or dedicated block (e.g. context limits, no offline). |
| **Future plans / roadmap** | “What Are the Future Plans for Kimi AI?” | Add “Roadmap” or “What’s next” (API, agent mode, design-to-code). |
| **Real-world use cases** | “How is Kimi AI Used in Real-World Applications?” (Customer Service, Legal, Finance, Healthcare) | Add “Use cases” section: Startups, internal tools, agencies, education. |
| **Featured cases / cards** | “Featured Agent Swarm cases” (e.g. Office Pilot, Membership Landing Page) with names | Expand “What are you building” into named “Featured builds” (e.g. “Bank software”, “Task manager”). |
| **Section tags** | Small “Benefits” tag above sections | Use small tags: “Benefits”, “How it works”, “Compare”. |
| **Two-column hero/content** | Left: large title + graphic; right: content (Key Features, Where to use) | Use two-column layout for Key Features and Where/How sections (Phase 2). |
| **Embedded app preview** | Full app mockup (sidebar + chat) on landing | Optional: add a static or simple interactive “Workspace preview” mockup. |

### 1.2 Functionality

| Left out | Kimi has it | Our status / plan |
|----------|--------------|-------------------|
| **Agent Swarm (parallel sub-agents)** | Up to 100 sub-agents, 1,500+ tool calls in parallel | In plan as “Later”; we have 20 sequential agents, not parallel swarm. |
| **Explicit “Thinking” mode** | Deeper reasoning, fewer mistakes | We have one flow; could add “Thinking” as a slower, more thorough mode. |
| **Design-to-code as named workflow** | “Upload UI screenshot → structured code” clearly named | We have `/ai/image-to-code` and attach images; plan: promote as “Design-to-code” in UI and copy. |
| **Memory / personalization** | “Learns from user interaction” | In plan as medium-term (preferences, stack, style). |
| **Long-context call-out** | 128K / 2M token context | We use model defaults; can add “Long context” line in features if we expose it. |
| **API for developers** | OpenAI-compatible API | In plan as medium-term; not in current backend. |
| **Local deployment** | “Run model locally” | In plan as later/optional. |
| **Docs/Slides/Sheets products** | Dedicated products for docs, slides, sheets | In plan as later; we focus on “build app” first. |

---

## 2. Rate, Rank & Compare After Kimi Look + Form + Function

Once we implement **Phase 1 (colors, fonts)**, **Phase 2 (content structure, accordions, footer CTA, nav icons)**, and **Phase 3 (design-to-code emphasis, agent-mode extension, structured outputs, How/Where sections, optional comparison table)**:

### 2.1 Rate (1–10) — after Kimi implementation

| Category | Current (RATE_RANK_COMPARE) | After Kimi implementation | Notes |
|----------|----------------------------|----------------------------|--------|
| **Reliability** | 10 | 10 | Unchanged; depends on keys, Babel, health. |
| **Build flow** | 8 | 9 | Same capabilities; clearer “plan first” and optional modes in UI. |
| **Deploy / export** | 10 | 10 | Unchanged. |
| **Agents & orchestration** | 8 | 8–9 | Same 20 agents; optional “agent mode” UX and per-step tokens. |
| **Tokens & billing** | 10 | 10 | Unchanged; pricing page and usage already there. |
| **UX (Cursor-like)** | 7 | 8–9 | Kimi-style look (black/white/gray, hierarchy), nav icons, accordions, footer CTA, “Try” prompts. |
| **Compliance / coverage** | 10 | 10 | Unchanged. |
| **Docs & onboarding** | 6 | 8 | “How to use” + “Where to use” + FAQ accordions + “View Documentation” CTA. |
| **Landing / positioning** | (not separate) | 9 | Kimi-style hero, What is, Key Features, Where/How, FAQ, comparison optional. |
| **Overall** | **10** | **9–10** | Stronger first impression and clarity; 10/10 when production gaps (Stripe live, health, tour) are closed. |

### 2.2 Rank (features by completeness) — after Kimi

1. **API route coverage** – unchanged (57 routes).
2. **Workspace build + tools** – unchanged; plus design-to-code promoted in copy.
3. **Agent system** – unchanged; optional agent-mode UX.
4. **Auth & projects** – unchanged.
5. **Dashboard & app shell** – unchanged.
6. **Settings & env** – unchanged (already Manus/Base44-style).
7. **Public site (Kimi-style)** – **new:** hero, What is, Key Features, Where/How, FAQ accordions, footer CTA, nav icons, optional comparison table.
8. **Prompt library** – unchanged.
9. **Tokens & Stripe** – unchanged.
10. **RAG / search / build-from-reference** – unchanged.

### 2.3 Compare (vs Kimi / Manus / Cursor) — after Kimi implementation

| Dimension | CrucibAI (after Kimi) | Kimi | Manus | Cursor | Our position |
|-----------|------------------------|------|--------|--------|--------------|
| **Look & feel** | Black/white/gray, clear hierarchy, nav icons, accordions | Same | Similar dark/pro | Similar | **On par** with Kimi for landing/site. |
| **Text → app** | Prompt → plan → code, stream, modify | Prompt → agent/swarm | Same idea | Composer | **Strong** (plan-first differentiator). |
| **Image → code** | Attach image, `/ai/image-to-code`, design-to-code copy | Design-to-code | Same | Same | **On par** when we promote it. |
| **Multi-model** | Auto / GPT-4o / Claude | K2/K2.5, modes | Similar | Similar | **On par**. |
| **Named modes** | Quick / Plan / Agent (if we add) | Instant / Thinking / Agent / Swarm | — | — | **Catch up** with mode selector. |
| **Pricing transparency** | Pricing page, Usage, tokens in sidebar | Clear tiers + API pricing | Similar | Subscription | **On par**. |
| **FAQ / support** | Expanded FAQ, accordions, Documentation CTA | 70 FAQ, accordions | Less | Docs | **Strong** after Phase 2. |
| **Comparison table** | Optional “vs others” | Yes | — | — | **Optional** differentiator. |
| **Agents visible** | 20 agents, phases, AgentMonitor | Swarm, sub-agents | Steps | Composer steps | **Good**; we don’t have swarm. |
| **Export** | ZIP, GitHub, Deploy | Same idea | Same | Export/share | **On par**. |

**Summary:** After implementation we **match Kimi** on look, content structure, and core build flow; we **differentiate** with plan-first and 20 specialized agents. We stay **behind** only on agent swarm (parallel 100 sub-agents) and optional “Thinking”/“Instant” named modes until we add them.

---

## 3. Functions We Are Implementing — Full List

### 3.1 Already in the project (backend + frontend)

**Auth & user**

- Register, login, JWT, `/auth/me`.
- Google OAuth: `/auth/google`, callback, login with token.
- Optional user (get_optional_user) for landing build.

**Build & plan**

- `POST /api/build/plan` — plan-first: returns plan text + suggestions (used by Workspace).
- `GET /api/build/phases` — list of build phases for progress UI.
- Workspace: calls `build/plan` for “big” prompts, then continues to code generation; supports `initialAttachedFiles` and prompt from landing.

**AI & chat**

- `POST /api/ai/chat` — single response.
- `POST /api/ai/chat/stream` — streamed response (chunked).
- `GET /api/ai/chat/history/{session_id}`.
- Model chain: auto / gpt-4o / claude with fallback; token deduction and balance check (prepay).

**Image / design-to-code**

- `POST /api/ai/image-to-code` — screenshot/image → React code (vision).
- `POST /api/files/analyze` — upload image/text, vision analysis for UI mockups.
- `POST /api/ai/design-from-url` — fetch image from URL, then image-to-code.
- Workspace: `handleBuild` with attached files uses image-to-code when image(s) present.

**Code quality & security**

- `POST /api/ai/validate-and-fix` — validate and fix code.
- `POST /api/ai/explain-error` — code + error → explanation.
- `POST /api/ai/suggest-next` — suggest next steps.
- `POST /api/ai/inject-stripe` — inject Stripe into code.
- `POST /api/ai/security-scan` — security scan.
- `POST /api/ai/optimize` — optimize code.
- `POST /api/ai/accessibility-check` — a11y check.

**Export & deploy**

- `POST /api/export/zip` — export files as ZIP.
- `POST /api/export/github` — push to GitHub.
- `POST /api/export/deploy` — deploy bundle (ZIP download).
- `POST /api/exports` + `GET /api/exports/{id}/download` — export history.

**Agents (20)**

- Planner, Requirements Clarifier, Stack Selector.
- Frontend Generation, Backend Generation, Database Agent, API Integration, Test Generation, Image Generation.
- Security Checker, Test Executor, UX Auditor, Performance Analyzer.
- Deployment Agent, Error Recovery, Memory Agent.
- PDF Export, Excel Export, Scraping Agent, Automation Agent.
- Endpoints: `/agents`, `/agents/status/{project_id}`, `/agents/run/<agent>`, `/agents/activity`.
- `run_orchestration(project_id, user_id)` — runs agents for a project; used when creating project.

**Projects & workspace**

- `POST /api/projects` — create (triggers orchestration).
- `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/projects/{id}/logs`, `GET /api/projects/{id}/phases`.
- `POST /api/projects/{id}/duplicate`, `POST /api/projects/{id}/save-as-template`.
- `POST /api/projects/from-template` — create from template.
- `GET /api/workspace/env`, `POST /api/workspace/env` — per-user env (API keys).

**Tokens & billing**

- `GET /api/tokens/bundles`, `POST /api/tokens/purchase`, `GET /api/tokens/history`, `GET /api/tokens/usage`.
- Balance check before LLM (MIN_BALANCE_FOR_LLM_CALL), 402 when insufficient; deduct min(usage, balance).
- Stripe: `POST /api/stripe/create-checkout-session`, `POST /api/stripe/webhook`.

**Prompts & templates**

- `GET /api/prompts/templates`, `GET /api/prompts/recent`, `POST /api/prompts/save`, `GET /api/prompts/saved`.
- `GET /api/templates` — project templates.

**Other**

- `POST /api/rag/query`, `POST /api/search` — RAG and search.
- `POST /api/voice/transcribe` — voice (if wired).
- `POST /api/build/from-reference` — build from URL + prompt.
- `POST /api/share/create`, `GET /api/share/{token}` — share links.
- `GET /api/patterns`, `GET /api/dashboard/stats` — patterns and dashboard.

**Frontend (main)**

- Landing: hero, chat input, attach files, “What are you building” chips, start build → workspace or auth.
- Workspace: plan-first for big prompts, image-to-code when images attached, chat, stream, Monaco + Sandpack, export ZIP/GitHub/Deploy, Tools (validate, security, a11y, optimize, explain error), AgentMonitor, env.
- Dashboard: projects, stats, share/duplicate/template.
- Settings: sidebar (Account, General, Usage, API & Env, Notifications, Billing, Security, Get help); General (language, theme), Usage (balance, Pricing link), Get help (Docs, support).
- Layout: token balance, Pricing plans, Documentation, Get help.
- Public: Features, Pricing, Templates, Patterns, Learn, Shortcuts, Prompts, Privacy, Terms.
- Auth: email/password, “Sign in with Google”.

### 3.2 Planned from Kimi (to implement)

**Phase 1 — Look & form**

- Kimi-style design tokens (black, white, gray, blue accent).
- Apply to Landing, PublicNav, PublicFooter, Features, Pricing, all public pages, Layout.
- Typography scale (hero, sections, body, nav).
- Optional grid pattern on hero.

**Phase 2 — Content**

- Hero: one headline + subline + CTA; optional “NEW” badge.
- “What is CrucibAI” section + bullets.
- Key Features: icon + title + description (two-column optional).
- “Where Can You Use CrucibAI” (accordion): Web app, API, Export.
- “How to Use CrucibAI” (steps 1–4).
- FAQ: expand, accordions, optional numbering.
- Footer CTA: headline + subline + “Try CrucibAI Free” + “View Documentation”.
- Nav: icons next to Features, Pricing, How it works, Documentation.

**Phase 3 — Function**

- **Design-to-code:** Promote in UI and copy; ensure images passed to vision in all relevant flows.
- **Agent mode (multi-step):** Optional explicit mode in Workspace + backend orchestration for step-by-step execution and tool use.
- **Structured outputs:** README, API docs, FAQ schema, comparison tables (prompts or small endpoints).
- **How it works + Where to use:** Content and accordions (Phase 2).
- **Optional:** “CrucibAI vs others” comparison table; named modes (Quick / Plan / Agent) in Workspace.

**Later / optional (from Kimi gaps)**

- Agent swarm / parallel agents.
- “Thinking” vs “Instant” mode.
- Personalization (preferences in system prompt).
- Public API for developers.
- Long-context call-out in features.
- Docs/Slides/Sheets-style products.
- Local deployment.
- Benchmarks, Limitations, Future plans, Real-world use cases sections.
- Productized sections (“CrucibAI for X”).
- 50+ numbered FAQ.

---

## 4. Summary

- **Left out from Kimi:** Productized “for X” sections, comparison table, key modules section, 50+ FAQ, named modes in UI, free-credits/tier copy, multiple product CTAs, sync chat history copy, mobile link, third-party platforms, benchmarks, limitations, future plans, real-world use cases, featured cases, section tags, two-column layout, embedded app preview; on the function side: agent swarm, Thinking mode, memory/personalization, API, local deployment, Docs/Slides/Sheets.
- **Rate after Kimi:** Overall 9–10; UX and Docs/onboarding go up; landing/positioning new at 9.
- **Rank after Kimi:** Public site (Kimi-style) enters as a top-level asset; rest unchanged.
- **Compare after Kimi:** We match Kimi on look and content structure; we differentiate on plan-first and 20 agents; we lag on swarm and named modes until we add them.
- **Functions:** All current backend/frontend capabilities are listed in 3.1; all planned Kimi items are listed in 3.2 and “later” in section 1.

Use this document together with `KIMI_INSPIRED_PLAN.md` and `RATE_RANK_COMPARE.md` for a full picture.
