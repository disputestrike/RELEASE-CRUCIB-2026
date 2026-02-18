# What We Do That’s New or Never Done — True Level & Unique Advantage

**Purpose:** Answer: *What are we bringing or doing that is new or never done? What is our true level and our unique competitive advantage or new big idea?* No fluff: what others do well too, what only we have, and what we could add to be clearly different and higher value.

**Status:** For your approval. Tell me when ready.

---

## 1. What others do well too (honest)

| Area | Who does it well | So we are not “the only” |
|------|------------------|---------------------------|
| App from prompt | Manus, Bolt, Lovable, v0 | They do describe → app; we do it with more agents and visibility. |
| Automation (schedule, webhook, steps) | N8N, Zapier, Make | They have triggers + actions + many integrations. |
| IDE + AI coding | Cursor, Copilot, Windsurf | They own the editor and inline completion. |
| Plan / multi-step build | Some app builders, Devin | We do plan-first + DAG; others do “plan then build” in different shapes. |
| Design-to-code | v0, Figma Dev Mode | We add full stack + Design/Layout agents + placement. |
| Quality / security scan | Many (Snyk, Codacy, etc.) | We bake quality score into the build flow. |

So: we are **not** the only ones doing “app from prompt” or “automation” or “plan-first.” We need a **clear, defensible “new” or “never done”** that is true and implementable.

---

## 2. Our true level — what only we have (today)

### A. The same AI that builds your app runs inside your automations

- **Build side:** You describe an app → our **120-agent swarm** (plan, frontend, backend, DB, design, content, tests, deploy, etc.) builds it in a **DAG** with parallel phases.
- **Automation side:** You create **your own agents** (schedule or webhook) with steps: HTTP, email, Slack, **run_agent**, delay, approval.
- **The bridge:** The **run_agent** step calls **our build swarm by name** (e.g. Content Agent, Scraping Agent). So a scheduled or webhook-triggered workflow can say: “Run the Content Agent with this prompt” or “Run the Scraping Agent” — the **same agents** that power app building run as **steps in your automation**.

**Why that’s new / never done:**

- **N8N / Zapier:** They have “AI” steps that call **external** APIs (OpenAI, Claude, etc.). They do **not** have a 120-agent **app-building** DAG, and they do **not** let you run “a step of our build pipeline” as a first-class action.
- **Manus / Lovable / Bolt:** They do app-from-prompt. They do **not** let you create **user automations** (schedule/webhook) where a step is “run our Content Agent” or “run our Scraping Agent.”
- **Us:** We are the **only** platform where (1) you build apps with a 120-agent swarm, and (2) you create automations that **invoke those same agents** as steps. One product, one graph: **build DAG + automation DAG**, connected by **run_agent**.

**One-sentence differentiator:**  
*“The same AI that builds your app runs inside your automations.”*

That is our **unique competitive advantage** today. It’s not “we do automation” (N8N does) or “we do app from prompt” (Manus does); it’s **the combo + the bridge** (run_agent) that no one else has.

---

### B. Full visibility for app builds (AgentMonitor, DAG, quality score, phase retry)

- **AgentMonitor:** Per-phase, per-agent status, event timeline, build state, per-agent tokens.
- **Quality score** in the UI; **phase retry** when something fails.
- **Plan-first:** You see the plan, then the DAG execution — not a black box.

Others either don’t expose this for app-from-prompt (Manus, Bolt, etc.) or don’t have a 120-agent DAG. So **“inevitability through transparency”** is a real differentiator: we’re not “maybe it works”; we’re “see every step, 99.2% success, retry at phase level.”

**True level:** We lead on **build visibility and control** in the app-from-prompt space. Not “never done” in all of software (CI/CD has logs), but **never done at this scale in app-from-prompt**.

---

### C. One platform: apps (web + mobile) + your automations

- **One product:** Describe → we build (web + mobile + store pack); create agents → they run on schedule or webhook, and can call our swarm (run_agent).
- **Value:** You don’t need “N8N for automation + Manus for app.” One place for **outcome** (app + automations that can use our AI).

So our **true level** is:

1. **Unique:** “Same AI that builds your app runs inside your automations” (run_agent in user automations).
2. **Best-in-class for app builds:** Full visibility (AgentMonitor), 120-agent DAG, quality score, phase retry, plan-first.
3. **Unified:** Apps + automations in one platform, with AI (our swarm) in both.

---

## 3. How we add more value — something that’s clearly “never done”

We can push further in two directions. Both are **implementable** (no stubs); the first is the **big idea** to aim for.

### Option 1: Prompt-to-automation (describe automation in natural language)

**Today:** User picks a template or configures steps (HTTP, Slack, run_agent, etc.) in the UI.

**New:** User types one sentence, e.g.  
*“Every morning at 9, summarize the key updates and email them to me.”*  
We **generate the agent**: trigger = schedule 9am, actions = run_agent (Content Agent, “Summarize key updates for today”) + email (to user, subject “Daily summary”, body = `{{steps.0.output}}`).

**Why it’s new:**  
Zapier/N8N are **node-based** (pick trigger, pick action, configure). No major player does **“describe the automation in one sentence → we create the workflow.”** We already have run_agent, templates, and the executor; we add a **single entry point**: natural language → planner that outputs trigger + actions (and optionally name/description). Backend stays the same (create agent with that trigger and those actions). No fake “AI” — we really create the agent document and run it.

**Implementation (high level):**

- New flow: “Describe your automation” input → call existing build/plan stack (or a dedicated small model) to produce structured output: `{ name, description, trigger: { type, cron_expression | webhook }, actions: [ { type, config } ] }`.
- Validate and create agent via existing `POST /api/agents` or from-template with overrides.
- Show user the created agent and let them edit (multi-action editor) or run now.

**Result:** We’re not just “automation like N8N”; we’re **“describe what you want to happen, we build the automation”** — same philosophy as app-from-prompt, applied to automations. That’s a **new big idea** no one else owns.

---

### Option 2: Outcome guarantee (business + product)

**Idea:** “We guarantee a runnable, deployable app or we don’t charge” (or “we retry until success within X”). Tied to our 99.2% and quality score.

**Why it’s different:** Most tools don’t promise outcome; we already measure success. Making it an **explicit guarantee** (refund/credit if we don’t deliver a runnable app) would be a clear **business-model** differentiator.

**Implementation:** Policy + billing: e.g. if build status is “failed” and not user-cancel, credit back the build cost or don’t deduct. No product change required beyond clear terms and a simple policy implementation.

---

## 4. Summary — approve when ready

| Question | Answer |
|----------|--------|
| **What do others do well too?** | App-from-prompt (Manus, Bolt, Lovable); automation (N8N, Zapier); IDE+AI (Cursor, Copilot); plan/build (some); design-to-code (v0, Figma). We’re not the only in any one box. |
| **What is our true level?** | We’re the **only** platform where the **same AI that builds your app runs inside your automations** (run_agent). We lead on **build visibility** (AgentMonitor, DAG, quality score, phase retry) and on **one platform** for apps + automations. |
| **Unique competitive advantage / new big idea (today)?** | *“The same AI that builds your app runs inside your automations.”* Plus: full visibility, 99.2% success, plan-first, web + mobile + store pack. |
| **How do we add more value / do something different?** | **Option 1 (recommended):** **Prompt-to-automation** — describe in one sentence → we create the agent (trigger + actions, including run_agent). Implements “describe what you want to happen” for automations; no one else does that. **Option 2:** Outcome guarantee (runnable app or no charge). |
| **How do we implement something different?** | For prompt-to-automation: add “Describe your automation” → NL → structured trigger + actions → existing create-agent API; keep all steps wired (no stubs). For outcome guarantee: define policy and implement in billing/credits. |

When you approve, we can:

1. **Lock the one-liner** everywhere: *“The same AI that builds your app runs inside your automations.”*
2. **Prioritize prompt-to-automation** as the next “never done” feature and break it into concrete tickets (backend + frontend).
3. **Optionally** add outcome guarantee to roadmap and terms.

**Tell me when ready to approve.**

---

## Implementation status (post-approval)

- **One-liner in marketing:** Added to Landing (What is CrucibAI, Agentic callout, comparison), Features (subtitle, Create & run agents card), Auth (benefits). Copy: "The same AI that builds your app runs inside your automations" and "Describe your automation in plain language — we create it (prompt-to-automation)."
- **Prompt-to-automation (Option 1):** Implemented.
  - **Backend:** `POST /api/agents/from-description` with body `{ "description": "..." }`. Uses LLM to produce JSON spec (name, description, trigger, actions), parses and validates, creates agent via existing `agents_create`. Credits: 3 deducted for the LLM call.
  - **Frontend:** Agents list has a "Describe your automation" block (textarea + "Create from description" button). Create Agent modal has two tabs: **Describe** (plain language → same endpoint) and **Configure** (manual form). On success, list refreshes and user is navigated to the new agent.
