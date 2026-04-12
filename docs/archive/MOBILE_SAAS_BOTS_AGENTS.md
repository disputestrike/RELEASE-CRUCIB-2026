# Mobile, SaaS, Bots & AI Agents — Build Support

**Goal:** Let CrucibAI build not only full-stack web apps but also **mobile apps**, **SaaS**, **bots**, and **AI agents**.

---

## 1. What each “build kind” means

| Kind | Output | Example prompt |
|------|--------|-----------------|
| **fullstack** (default) | Web app: React frontend, backend, DB, deploy | “Build a todo app with auth” |
| **mobile** | Mobile app: React Native, Flutter, or PWA | “Build a mobile habit tracker” |
| **saas** | Web app + multi-tenant, billing (Stripe), plans | “Build a SaaS dashboard with subscriptions” |
| **bot** | Chatbot / integration bot: Slack, Discord, Telegram, webhook | “Build a Slack bot that shows standup reminders” |
| **ai_agent** | Custom AI agent: tools, prompts, orchestration (e.g. OpenAPI + instructions) | “Build an AI agent that books meetings from natural language” |

---

## 2. What we have today

- **Planner** accepts optional **build_kind** (`mobile` | `saas` | `bot` | `ai_agent`). The plan and stack are tailored to that kind.
- **Same 20-agent DAG** runs for all kinds; context from Planner/Stack Selector steers Frontend/Backend (e.g. “React Native” for mobile, “Stripe + tenants” for SaaS, “Slack event handler” for bot, “tool definitions + system prompt” for AI agent).
- **100_THINGS_TO_BUILD** includes a section of ideas for mobile, SaaS, bots, and AI agents.

---

## 3. What’s implemented

| Piece | Status |
|-------|--------|
| **build_kind** in `/build/plan` | ✅ Optional param; planner system prompt includes kind-specific instructions. |
| **Plan tailored** to mobile / SaaS / bot / ai_agent | ✅ Planner output format and guidance depend on build_kind. |
| **Orchestration** | ✅ Unchanged; agents get plan + stack in context and generate appropriate code (RN, Stripe, bot handlers, agent YAML/tools). |
| **Project type** | ✅ Projects still store `project_type`; can be `fullstack`, `mobile`, `saas`, `bot`, `ai_agent` when created from a plan with that kind. |

---

## 4. How to use

**In Workspace (or New Project):**

- **Mobile:** Set build kind to **Mobile** (or prompt: “Build a **mobile app** that …”). Planner will target React Native / Flutter / PWA; Stack Selector and Frontend/Backend will output mobile-friendly code.
- **SaaS:** Set build kind to **SaaS** (or “Build a **SaaS** … with subscriptions”). Plan will include tenants, plans, Stripe; agents will generate billing and tenant-aware code.
- **Bot:** Set build kind to **Bot** (or “Build a **Slack/Discord/Telegram bot** that …”). Plan will target event handlers, commands, webhooks; Backend/API agents will output bot server code.
- **AI agent:** Set build kind to **AI agent** (or “Build an **AI agent** that …”). Plan will target tools, system prompt, and optionally OpenAPI; agents will output agent config + tool definitions + sample prompts.

If the UI doesn’t expose a dropdown yet, include the kind in the prompt (e.g. “Build a **mobile** habit tracker” or “Build a **SaaS** CRM with Stripe”).

---

## 5. Possible future extensions

- **Mobile:** Dedicated “Mobile” agent that outputs React Native or Flutter by default; or a PWA agent that ensures installable + responsive.
- **SaaS:** Stripe webhook handler in backend seed; tenant_id on all key tables; “Plans” and “Billing” pages in the generated app.
- **Bots:** Templates for Slack/Discord/Telegram (event payload → handler); “Bot” project type that skips frontend and generates only backend + manifest.
- **AI agents:** “Agent” project type that outputs a runnable agent definition (e.g. YAML or JSON with tools + system prompt) plus a small runner (e.g. FastAPI that calls LLM with tools).

---

**Last updated:** February 2026
