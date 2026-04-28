# CrucibAI — Grounding & Competitive Intelligence: Master Handoff

**Purpose:** Single handoff artifact for builders and leadership. It consolidates everything the repo has used to *ground* product decisions: competitor capabilities, our implementations, explicit gaps, where code lives, and **what not to claim** without evidence.

**Audience:** Engineers, PM, GTM. Read this before changing orchestration, workspace UX, positioning, or benchmarks.

**Last updated:** 2026-04-25

**How to use this doc**

1. **Tier A (code-grounded):** Treat `CRUCIBAI_COMPETITOR_MATRIX.md`, `CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md`, `gap_analysis_manus_internal_logic.md`, `proof/INDUSTRY_GAP_CROSSWALK.md`, `proof/benchmarks/competitor_methodology.md` as the honesty baseline.
2. **Tier B (positioning / narrative):** `COMPARE_CRUCIBAI_VS_KIMI_AI.md`, `CRUCIBAI_CAPABILITIES_vs_MANUS.md` (archive), and some Top-10 writeups contain **strong marketing claims**. Cross-check against Tier A before external use.
3. **Tier C (stale or superseded):** Older rate/rank files may cite **20 agents** or **115 agents**; current brand direction is **120-agent swarm** (see `BRAND_IMPLEMENTATION_PLAN_INEVITABLE_AI.md`, `COMPETITIVE_ASSESSMENT_KIMI_MANUS_AND_US.md`). **Reconcile agent counts from `backend/agent_dag.py` and `verify_120_agents.py` before publishing.**

---

## Part 0 — Conflicts you must not ignore

| Topic | Conflicting signals in repo | Resolution for the team |
|-------|------------------------------|-------------------------|
| **Agent count** | 20 (KIMI_GAPS, KIMI_CROSSWALK, older API lists), 115 (`CRUCIBAI_COMPETITIVE_RANKING.md`), 120 (brand, assessment), 123 (archive `CRUCIBAI_CAPABILITIES_vs_MANUS.md`) | **Single source of truth = code** (`agent_dag.py`, verification scripts). Messaging locked to **120** per brand plan; update old docs when touched. |
| **vs Kimi** | `COMPARE_CRUCIBAI_VS_KIMI_AI.md` says CrucibAI wins every dimension 10/10; `HOW_WE_COMPARE_TO_MANUS_KIMI_TOP.md` says they win on **deep autonomy / long tool chains** | **Use the honest frame:** we win on **app-from-prompt + orchestrated build + visibility + proof spine**; we do **not** win on **foundation-model benchmarks** or **Kimi-class Office/doc product**. |
| **Automation** | `UNIQUE_COMPETITIVE_ADVANTAGE...` and code have `run_agent` + worker; `AGENTS_STRATEGY_N8N_ZAPIER_SPACE.md` historically stressed gaps | **Verify prod:** `backend/automation/executor.py`, `backend/workers/automation_worker.py`, `automation_tasks` / user agents in `db_pg.py`. N8N parity (integration catalog, visual builder) is still **not** claimed. |
| **Manus agent count** | `HOW_WE_COMPARE` says ~3 agents; archive capabilities doc says Manus ~50 | External Manus architecture is **not** verified here; use **archetype** language (checklist Manus) for engineering gaps. |

---

## Part 1 — Evaluation axes (shared rubric)

From `docs/CRUCIBAI_COMPETITOR_MATRIX.md`. All competitors in Part 2 can be mapped to these.

| Axis | ID | What it tests |
|------|-----|----------------|
| Durable run & rehydration | **A1** | `job_id`, URL, task binding, reload |
| Live trace (SSE, events, not chat-only) | **A2** | Activity feed, `brain_guidance` vs full event mapping |
| Terminal | **A3** | Session, execute, audit, policy |
| Orchestration | **A4** | Plan → DAG → `run-auto`, preflight, spec guardian |
| Preview & artifacts | **A5** | Sandpack, `dev_server_url`, export / handoff |
| Proof & verification | **A6** | `GET /api/jobs/{id}/proof`, benchmarks, memos |
| Simulation / What-If | **A7** | Pre-run risk (`WhatIfPage`, `/runtime/what-if`) |
| Extensibility | **A8** | Connectors, MCP-style, skills, capabilities API |
| Workspace / IDE surfaces | **A9** | Unified vs classic vs Manus vs IDE routes |
| Advisory vs job truth | **A10** | Dashboard `/ai/chat` vs orchestrator stream |

**Legend:** **M** match, **+** differentiator (when productized), **P** partial, **G** gap, **D** deliberate non-goal / different topology.

---

## Part 2 — Competitor encyclopedia (capabilities + our stance)

### 2.1 Kimi AI (K2 / K2.5 — Moonshot)

**Sources:** `docs/COMPETITIVE_ASSESSMENT_KIMI_MANUS_AND_US.md`, `docs/archive/COMPARE_CRUCIBAI_VS_KIMI_AI.md`, `docs/archive/KIMI_CROSSWALK.md`, `docs/archive/KIMI_GAPS_AND_FUNCTIONS.md`, `docs/archive/KIMI_COMPLIANCE_MATRIX.md`, `docs/archive/KIMI_INSPIRED_PLAN.md`, `docs/archive/KIMI_QA.md`, `docs/archive/HOW_WE_COMPARE_TO_MANUS_KIMI_TOP.md`.

#### 2.1.1 What Kimi is (market framing)

- General **assistant + agentic** product: research, coding, multimodal, long context.
- **K2.5** positioning (from your inputs): strong on **vision reasoning**, **multi-agent**, **circle-to-edit** style UX, **Office/agent** flows for Excel/PPT/Word/PDF, benchmark narratives vs GPT/Gemini class models.
- **Agent Swarm:** product story includes **many parallel sub-agents** and high tool-call volume (your docs cite up to **100** sub-agents for large tasks).
- **Modes:** Instant / Thinking / Agent / Swarm-style experiences in their UX framing.
- **Ecosystem:** Kimi Docs, Slides, Sheets, Website Builder narratives; API story for developers.

#### 2.1.2 Kimi-aligned **product surface** we mapped to CrucibAI (KIMI_CROSSWALK)

| Kimi element | Intended CrucibAI mapping | Implementation notes |
|--------------|---------------------------|----------------------|
| Deep black UI, white/gray type, blue accent, grid | CSS/Tailwind tokens (`--kimi-*`), `grid-pattern-kimi` | Landing/public pages |
| Hero: “Hello, Welcome to …” | Landing hero copy | Match structure |
| NEW badge (e.g. K2.5) | “Plan-first & Swarm mode” style badge | Copy |
| “What is …” + bullets | Section + bullets | Content |
| Key Features (icons) | Two-column features | Content |
| Where / How accordions & steps | Public sections | Content |
| FAQ numbered | Accordion FAQ | Expand toward Kimi depth optionally |
| Footer CTA + Documentation | `PublicFooter` | Wired |
| Nav icons | `PublicNav` (Features, Pricing, etc.) | Wired |
| Comparison table | “CrucibAI vs Other AI Tools” | Optional / Phase |
| Modes: Instant / Thinking / Agent / Swarm | Quick / Plan / Agent / Thinking / Swarm (beta) in Workspace | **Verify** parity in current `UnifiedWorkspace` vs crosswalk |
| Design-to-code | `POST /api/ai/image-to-code`, attachments | Promote in UX |
| Plan-first | `POST /api/build/plan`, big-build path | Core |
| Swarm plan | `build/plan?swarm=true`, parallel suggestions, token multiplier | Core where enabled |
| Structured outputs | README / docs / FAQ schema endpoints | Backend |
| Limitations & roadmap sections | Landing sections | Content |
| Use cases | Real-world section | Content |
| Sign in to sync | Landing hint when logged out | UX |

#### 2.1.3 Kimi capabilities we **do not** fully replicate (KIMI_GAPS §1)

**Content / marketing structure (optional parity)**

- Productized **“Kimi for X”** vertical sections → we may add **“CrucibAI for …”** slices.
- **50–70 FAQ** items → we have fewer; optional expansion.
- **Benchmarks** block (MMLU, HumanEval, …) → only if we have **our** proof, not their model scores.
- **Mobile app** nav link → only with real app/PWA.
- **Third-party platforms** (OpenRouter, HF, …) → if/when true.
- **Embedded full app mockup** on landing → optional.
- **Featured swarm case cards** → optional.

**Functionality**

- **100 parallel sub-agents** swarm at Kimi scale → our architecture is **DAG + named agents + Swarm mode** on plan; **not** the same as their internal swarm implementation.
- **Thinking mode** as a dedicated product lane → we have Thinking-style chat handling in crosswalk; **verify** against current chat routes.
- **Memory / personalization** “learns from user” → roadmap in Kimi docs.
- **OpenAI-compatible public API** as first-class → partial / evolving; **check** `server.py` and routes for current API surface.
- **Local model deployment** → not our default wedge.
- **Dedicated Docs/Slides/Sheets products** like Kimi → we have **export/generation** paths; not separate “Kimi Docs” SKU.

#### 2.1.4 Honest **where we win vs Kimi** (synthesis)

| Dimension | CrucibAI | Kimi |
|-----------|----------|------|
| **Lane** | **Applications:** plan-first, full-stack app factory, deploy/export, proof/job spine | **General intelligence + docs/slides + model benchmarks** |
| **Visibility** | AgentMonitor, phases, job stream, proof API | Less emphasis on **per-agent app-build transparency** in our framing |
| **Outcome story** | 99.2% / “inevitable” **for app builds** (when substantiated) | Benchmark and **Office** narratives |
| **Same-AI in automations** | `run_agent` + automation executor + worker (code exists) | External AI steps in workflow tools, not our 120-agent build DAG |

#### 2.1.5 Where **Kimi leads** (do not claim we beat without proof)

- **Foundation model benchmarks** (GPT/Gemini class comparisons).
- **General Office document** editing in one shot.
- **Circle-to-edit** live on page (we: design-to-code / screenshot flows).
- **Native trillion-param Kimi model** — we are **BYOK / multi-provider** architecture.

#### 2.1.6 Kimi → engineering backlog (from gaps)

1. Mode selector parity (Quick / Plan / Agent / Thinking / Swarm) — **UX + API contract**.
2. Expand FAQ / comparison table / vertical sections — **content**.
3. Personalization / memory — **memory layer** (`memory/vector_db.py` + policies).
4. Public API packaging — **docs + auth + rate limits**.
5. Swarm: clarify **user-visible** definition vs Kimi’s parallel sub-agents — **product + metrics**.

---

### 2.2 Manus (vendor archetype + your checklist)

**Sources:** `gap_analysis_manus_internal_logic.md`, `docs/CrucibAI_vs_Manus_Architecture_Deep_Dive.md`, `docs/CRUCIBAI_COMPETITOR_MATRIX.md` §3.5, `docs/archive/CRUCIBAI_CAPABILITIES_vs_MANUS.md`, `validation_checklist.md` (referenced in control plane).

#### 2.2.1 Typical Manus-class **user promises** (from your research)

- Prompt → working product quickly; **premium** web output; deploy story.
- **Generalist agent** in **sandbox** (browser, terminal, filesystem).
- **Context engineering** (state machine, disk as memory, recovery).
- Rankings / social proof in their marketing (we may not have equivalent).

#### 2.2.2 Manus **internal logic** six layers vs us (`gap_analysis_manus_internal_logic.md`)

| Layer | They want | We have | Gap / action |
|-------|-----------|---------|----------------|
| **1 Intake** | Intent JSON schema + **clarification gate** blocks run | `ClarificationAgent` heuristics | **G:** normalized intent object; **hard UI gate** on ambiguity |
| **2 Planning** | Dynamic DAG + **Diagnostic Agent** repair | `controller_brain.py`, `agent_dag.py`, replan triggers | **G:** explicit diagnostic/repair agent feeding DAG |
| **3 Coding** | Contract-first, style inhalation | Scaffold, Pydantic | **G:** contract compiler (e.g. TS from models); style context injection |
| **4 Execution** | Pre-flight, atomic edits, blast radius, **single file_writer** | `virtual_fs`, permissions, tools | **G:** audit single conduit to disk; stronger blast radius |
| **5 Verification** | Per-node `verification_cmd`, proof.json w/ “why”, hallucination checks | `verifier.py`, proof services, E2E tests | **G:** mandatory verify on every node; richer proof narrative |
| **6 Delivery** | Smoke (browser/curl), forensic diff, 5s poll, unified completion report | Deploy routes, `present_results` | **G:** mandatory smoke; diff artifact; completion report contract |

#### 2.2.3 Matrix marks vs Manus archetype (A1–A10)

Summarized: **strong** on A1, A2, A4, A5, A6, A7; **P/G** on clarify-first UI, checklist breadth vs code, workspace consolidation, dual-brain clarity.

---

### 2.3 OpenAI Codex **class** (durable run, artifacts, preview, background)

**Source:** `CRUCIBAI_COMPETITOR_MATRIX.md` §3.1, `CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md` B2.1.

| Capability | Our implementation | Gap |
|------------|-------------------|-----|
| Durable run in URL | `job_id`, jobs API | Task without `jobId` early → stream gap (**C6** in control plane) |
| Single transcript of tools + files | `events`, `brain_guidance` | **P:** map more event types to feed |
| Preview first-class | `PreviewPanel`, dev-preview, Sandpack, WS | **P:** data must populate `dev_server_url` / files |
| Background automation | orchestrator, long jobs | Host health dependent |

---

### 2.4 Cursor **class** (IDE-native, local tree truth)

**Source:** Matrix §3.2, Control plane B2.2.

| Capability | Us | Note |
|------------|-----|------|
| Local repo + LSP | **D** | Hosted job workspace |
| Fast edit loop | **D** | Orchestrated builds |
| Proof + job | **+** | Governed deliverables |
| Chat as truth | **G** if implied | Must label **advisory** vs **job** |

---

### 2.5 Claude Code **class** (single tree, terminal depth)

**Source:** Matrix §3.3, Control plane B2.3.

| Capability | Us | Note |
|------------|-----|------|
| One CWD mental model | **M** via `job_id` | |
| Terminal as actuator | **M** `terminal.py`, `JobTerminalStrip.jsx` | |
| Raw local shell | **D** | Server-side policy |
| Many workspace routes | **G** | Consolidation |

---

### 2.6 Goose **class** (connectors, MCP, user environment)

**Source:** Matrix §3.4, Control plane B2.4.

| Capability | Us | Note |
|------------|-----|------|
| Many integrations | **P/G** | Capabilities API honesty |
| On-device execution | **D** | Server-centric |
| Job + proof unified | **M** | |

---

### 2.7 “Monday → Friday” Top 5 (positioning set)

**Source:** `docs/archive/RATE_RANK_TOP5_MONDAY_FRIDAY.md`

| # | Competitor | Type | Their strength (per doc) | Our differentiator (per doc) |
|---|------------|------|--------------------------|------------------------------|
| 1 | CrucibAI | App + automation | Full outcome in one platform | 120-agent swarm, same AI in automations, export |
| 2 | Manus / Bolt | App-from-prompt | Speed to app | We add automations + copy + run_agent story |
| 3 | N8N | Automation | Integrations, self-host | We add app-from-prompt + mobile + GTM assets |
| 4 | Lovable | App-from-prompt | Simple full-stack | We add swarm + user agents + automation |
| 5 | Zapier | Automation | Connector count | We build full app + stack; they connect SaaS |

**Dimensions scored there:** Mon→Fri delivery, full-stack sharp, same AI build+auto, one platform, export/own.

---

### 2.8 Tier 1 market list (alternate framing)

**Source:** `docs/RATE_RANK_CURRENT.md` §5

1. CrucibAI  
2. Manus / Bolt  
3. Cursor  
4. **Kimi AI (K2)**  
5. v0 (Vercel)  

Use this when the question is **“top tools buyers compare”** vs **Monday→Friday Top 5**.

---

### 2.9 Top 10 app builders table (landscape)

**Source:** `docs/Top_10_AI_App_Builders_Competitive_Analysis_2026.md`

Listed platforms: CrucibAI, Manus AI, Lovable, Cursor, Windsurf, Replit Agent, Bolt.new, Devin, v0, Base44 — with category, LLM, differentiator, audience. Use for **market map**, not as verified benchmark order.

---

### 2.10 N8N / Zapier / Make (automation lane)

**Source:** `docs/AGENTS_STRATEGY_N8N_ZAPIER_SPACE.md`

| Capability | They have | We have | Gap |
|------------|-----------|---------|-----|
| Trigger catalog | Cron, webhooks, SaaS events | Partial | **G** first-class triggers |
| Visual flow builder | Yes | App build focus | **D** / different |
| Integration nodes | Hundreds–thousands | HTTP, Slack, email, run_agent | **G** breadth |
| Hosted execution | Yes | Worker + executor (verify deploy) | Ops productization |
| User agent run history UI | Yes | Project build logs | **G** per automation run UX |
| Human-in-the-loop steps | Some | Limited | **G** |
| Agent marketplace | Ecosystem | Templates | **G** |

---

### 2.11 Integrations & ads

**Source:** `docs/GAPS_AND_INTEGRATIONS_REVIEW.md`

- **Not implemented:** Native Meta Ads / Google Ads campaign posting.
- **Why:** OAuth, compliance, credential storage, API churn.
- **Launch stance:** “You run the ads; we built the stack.”
- **Workaround:** HTTP action to user endpoint.

---

## Part 3 — CrucibAI implementation map (where things live)

### 3.1 Control plane spine (jobs, orchestration, proof)

| Concern | Files (from matrix & control plane) |
|---------|--------------------------------------|
| Plan, DAG, run-auto | `backend/routes/orchestrator.py`, `build_dag_from_plan`, `create_step` |
| Jobs, stream, proof API | `backend/routes/jobs.py`, `GET /api/jobs/{id}/stream`, `GET /api/jobs/{id}/proof` |
| DB model | `backend/db_pg.py` — `jobs`, `job_steps`, `job_events`, `proof_items`, `build_plans` |
| Preflight / spec guardian | `build_preflight_report`, `spec_guardian`, `evaluate_goal_against_runner` |
| Frontend stream & feed | `frontend/src/hooks/useJobStream.js`, `WorkspaceActivityFeed.jsx`, `UnifiedWorkspace.jsx` |
| What-If | `frontend/src/pages/WhatIfPage.jsx`, `POST /runtime/what-if` |
| Terminal | `backend/routes/terminal.py`, `backend/terminal_integration.py`, `frontend/src/workspace10/JobTerminalStrip.jsx` |
| Trust / production posture | `backend/routes/trust.py` |
| Capabilities honesty | `GET /api/settings/capabilities`, Settings → Engine room |
| MCP adapter | `backend/services/mcp_client.py` (narrow) |
| Automation | `backend/automation/executor.py`, `backend/automation/models.py`, `backend/workers/automation_worker.py` |

### 3.2 Workspace / routing (A9)

**Routes (non-exhaustive):** `UnifiedWorkspace`, `WorkspaceManus`, `workspace-classic`, `ide` — see `frontend/src/App.js`. **Backlog:** consolidate shells.

### 3.3 Industry crosswalk (themes → files)

**Source:** `proof/INDUSTRY_GAP_CROSSWALK.md`

| Theme | Files |
|-------|--------|
| One brain | `backend/orchestration/planner.py`, `agent_selection_logic.py` |
| One runtime / visible flow | `backend/server.py`, `event_bus.py`, `backend/api/routes/job_progress.py` |
| One memory strategy | `backend/memory/vector_db.py` |
| Verification contract | `backend/orchestration/preview_gate.py`, `backend/agents/preview_validator_agent.py` |

### 3.4 Feature list snapshot (legacy API inventory)

**Source:** `docs/archive/KIMI_GAPS_AND_FUNCTIONS.md` §3.1 — detailed **route-by-route** list (auth, build/plan, ai/chat, image-to-code, export, agents, tokens, Stripe, RAG, voice, etc.). Use when auditing **route coverage**; **verify** each route still exists in current `server.py` / routers after refactors.

---

## Part 4 — Consolidated backlog (prioritized for builders)

### 4.1 From control plane audit (user pain → code)

1. **TASK-JOB-BINDING:** Every task gets `jobId` as soon as plan returns; sidebar URLs always include it.  
2. **WORKSPACE-TRACE:** Map **all** critical event types to visible activity (not only `brain_guidance`) or add non-chat activity list.  
3. **PREVIEW-DATA:** Railway/prod verification that `job` gets `dev_server_url` / files for PreviewPanel.  
4. **FILE PULL:** Orchestrator always writes to job workspace; tree not empty silently.  
5. **FAILED-RUN UX:** Never lose failure DTO; E2E on failed jobs.  
6. **PERSISTENCE (optional):** Server-side chat or event read model per job for cross-device.

### 4.2 From Manus internal logic gaps

- Normalized **IntentSchema** + **clarify-first UI gate**.  
- **Diagnostic Agent** / explicit repair steps in DAG.  
- **Contract compiler** + **style context**.  
- **Single file-writer conduit** audit + blast radius enforcement.  
- **verification_cmd** on every DAG node; proof.json “why”.  
- Delivery: **smoke**, **forensic diff**, **completion report**, **final poll** contract.

### 4.3 From Kimi gap analysis

- Mode parity, FAQ depth, optional benchmarks **only with our data**, personalization, API packaging, vertical landing sections.

### 4.4 From integrations review

- Native ad platforms → **post-launch** only if committed.

### 4.5 From benchmark methodology

- Load competitor JSON under `proof/benchmarks/competitor_runs/` before claiming benchmark **#1**.

---

## Part 5 — Proof & evidence rules

| Artifact | Path | Rule |
|----------|------|------|
| Competitor comparison output | `proof/benchmarks/competitor_comparison_latest.json` | Must have non-empty comparisons for public benchmark claims |
| Scorecard | `proof/benchmarks/COMPETITOR_COMPARISON_SCORECARD.md` | Regenerate after runs |
| Methodology | `proof/benchmarks/competitor_methodology.md` | Same prompts, same rubric, same timeouts |

---

## Part 6 — Full document index (grep starting points)

### 6.1 Tier A — code-grounded

- `docs/CRUCIBAI_COMPETITOR_MATRIX.md`
- `docs/CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md`
- `docs/CRUCIBAI_CONTROL_PLANE_IMPLEMENTATION.md`
- `gap_analysis_manus_internal_logic.md`
- `proof/INDUSTRY_GAP_CROSSWALK.md`
- `proof/benchmarks/competitor_methodology.md`

### 6.2 Kimi cluster

- `docs/COMPETITIVE_ASSESSMENT_KIMI_MANUS_AND_US.md`
- `docs/archive/KIMI_CROSSWALK.md`
- `docs/archive/KIMI_GAPS_AND_FUNCTIONS.md`
- `docs/archive/COMPARE_CRUCIBAI_VS_KIMI_AI.md`
- `docs/archive/HOW_WE_COMPARE_TO_MANUS_KIMI_TOP.md`
- `docs/archive/KIMI_INSPIRED_PLAN.md`
- `docs/archive/KIMI_COMPLIANCE_MATRIX.md`
- `docs/archive/KIMI_QA.md`
- `docs/archive/KIMI_PROOF_OF_IMPLEMENTATION.md`
- `docs/archive/KIMI_BEAT_IMPLEMENTATION_PROOF.md`
- `docs/archive/KIMI_BEAT_10_10_APPROVAL.md`
- `docs/archive/PROOF_KIMI_BEAT_10_10.md`

### 6.3 Manus / architecture

- `docs/CrucibAI_vs_Manus_Architecture_Deep_Dive.md`
- `docs/archive/CRUCIBAI_CAPABILITIES_vs_MANUS.md`
- `docs/archive/CRUCIBAI_MANUS_ARCHITECTURE.md`
- `docs/archive/EXACT_MANUS_IMPLEMENTATION.md`
- `extracted_content/EXACT_MANUS_IMPLEMENTATION.md`
- `docs/archive/REVISED_MANUS_ALIGNED_SPECS.md`
- `docs/archive/OUR_SANDBOX_PREVIEW_AND_MANUS_STYLE.md`
- `docs/archive/DESIGN_SYSTEM_MANUS_INSPIRED.md`

### 6.4 Positioning & Top N

- `docs/archive/RATE_RANK_TOP5_MONDAY_FRIDAY.md`
- `docs/RATE_RANK_CURRENT.md`
- `docs/Top_10_AI_App_Builders_Competitive_Analysis_2026.md`
- `docs/CRUCIBAI_COMPETITIVE_RANKING.md`
- `docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md`
- `docs/AGENTS_STRATEGY_N8N_ZAPIER_SPACE.md`
- `docs/GAPS_AND_INTEGRATIONS_REVIEW.md`

### 6.5 Brand & messaging

- `docs/BRAND_IMPLEMENTATION_PLAN_INEVITABLE_AI.md`
- `docs/BRAND_IMPLEMENTATION_COMPLIANCE_CROSSWALK.md`
- `docs/MESSAGING_AND_BRAND_VOICE.md`
- `docs/CRUCIBAI_BRAND_BOOK_MASTER.md`

### 6.6 Presentations & misc

- `docs/PRESENTATION_CRUCIBAI_VS_COMPETITORS.md`
- `docs/PLAYGROUND_COMPARE.md`
- `COMPETITIVE_ADVANTAGE.md` (repo root)

---

## Part 7 — One-page summary for new hires

- **We are not** a foundation model company; **we are** an **app + control-plane** company: jobs, DAG, proof, preview, optional What-If.  
- **We win** on **transparent orchestrated builds**, **export/deploy**, **automation bridge** (`run_agent`), and **honest** capability surfaces.  
- **We do not win** on **Kimi benchmarks**, **Kimi Office editor**, **Cursor local IDE loop**, **Zapier connector count**, or **Manus marketing rank** — unless we have **our** proof.  
- **Next builds** should close **task↔job binding**, **live trace richness**, **preview data in prod**, and **Manus checklist gaps** where product chooses hard gates.

---

## Appendix A — Top 10 platforms table (full copy)

**Source:** `docs/Top_10_AI_App_Builders_Competitive_Analysis_2026.md`  
**Note:** This is **positioning copy** inside the repo; rank order is **not** independently verified.

| Rank | Platform | Category | Primary LLM Engine | Key Differentiator | Target Audience |
|------|----------|----------|-------------------|-------------------|-----------------|
| 1 | CrucibAI | Enterprise Swarm | Anthropic Haiku + Cerebras (Intelligent Routing) | Deterministic build pipeline, 6-phase learning loop, 70+ role-based agent swarm | Enterprise teams, founders, full-stack developers |
| 2 | Manus AI | Generalist Agent | Claude 3.7 | Linux sandbox execution, context-aware state machines | Researchers, prototypers |
| 3 | Lovable | Vibe Coding | Claude 3.7 / Gemini | Full-stack + bi-directional GitHub + Supabase | Designers, non-technical founders |
| 4 | Cursor | Agentic IDE | Claude / GPT-4o | Codebase context, multi-file edit, Figma MCP | Professional developers |
| 5 | Windsurf (Codeium) | Agentic IDE | Custom / Claude | Agentic IDE, codebase indexing | Enterprise engineering |
| 6 | Replit Agent 4 | Hybrid | Custom | Parallel multi-agent | Indie hackers, prototypers |
| 7 | Bolt.new | Vibe Coding | Claude | WebContainers, instant preview | Frontend developers |
| 8 | Devin | Autonomous SWE | Custom | Long-horizon tasks, SWE-bench, environment management | Engineering teams |
| 9 | v0 (Vercel) | Vibe Coding | Custom / Claude | React/Tailwind/Vercel-tuned UI | Frontend, designers |
| 10 | Base44 | Vibe Coding | Multiple | Code ownership / portability | Startups needing MVP portability |

**Narrative bullets in that doc (for GTM context only):** “70+ Agent Swarm,” speed-tier routing, `.crucib_build_memory.json`, 6-phase learning loop, deterministic repair (`file_language_sanity`, `brain_repair`, verification suites). **Engineering must verify** each claim against live code before external use.

---

## Appendix B — “Monday → Friday” Top 5 scoring table (full copy)

**Source:** `docs/archive/RATE_RANK_TOP5_MONDAY_FRIDAY.md`

**Dimensions:** Mon→Fri delivery, Full-stack sharp, Same AI build+auto, One platform, Export/own. Overall = average of five.

| # | Tool | Mon→Fri | Full-stack | Same AI | One platform | Export/own | Overall |
|---|------|---------|------------|---------|--------------|------------|---------|
| 1 | CrucibAI | 10 | 10 | 10 | 10 | 10 | 10.0 |
| 2 | Manus / Bolt | 8 | 7 | 3 | 6 | 8 | 6.4 |
| 3 | N8N | 5 | 4 | 4 | 5 | 8 | 5.2 |
| 4 | Lovable | 7 | 6 | 3 | 5 | 7 | 5.6 |
| 5 | Zapier | 5 | 3 | 3 | 4 | 5 | 4.0 |

---

## Appendix C — `RATE_RANK_CURRENT` competitor tiers (full Tier 1–3)

**Source:** `docs/RATE_RANK_CURRENT.md` §5 (Feb/Mar 2026 framing).

**Tier 1 — Top 5 (8.5+):** CrucibAI (~9.5), Manus/Bolt (8.2), Cursor (8.0), Kimi AI K2 (7.8), v0 (7.6).

**Tier 2 — Top 10 (7.0–8.4):** GitHub Copilot (7.4), Replit Agent (7.3), Lovable (7.2), Windsurf (7.1), ChatGPT/Claude coding (7.0).

**Tier 3 — Top 20 (6.0–6.9):** Codeium (6.8), Bolt.new (6.6), Cody (6.5), Phind (6.4), Continue.dev (6.3), Amazon CodeWhisperer (6.2), Mutable AI (6.1), Tabnine (6.0), Mistral Codestral (5.9), Pieces (5.6).

**Use:** Internal **discussion** only unless rescored with a published rubric.

---

## Appendix D — Star feature matrix (CrucibAI vs Cursor, Copilot, Replit, v0)

**Source:** `docs/CRUCIBAI_COMPETITIVE_RANKING.md` (Feb 2026). Subjective ⭐ grid.

| Feature | CrucibAI | Cursor | Copilot | Replit | Vercel v0 |
|---------|----------|--------|---------|--------|-----------|
| Code Completion | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Full Projects | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Agent Orchestration | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| Backend Automation | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| Frontend Automation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Deployment | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| IDE Integration | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Real-time Collab | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Enterprise Ready | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Pricing | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Weaknesses called out in same doc:** market presence, native IDE, real-time collab, community, brand vs Cursor/Copilot/Replit.

---

## Appendix E — Kimi vs CrucibAI dimension table (archived compare doc)

**Source:** `docs/archive/COMPARE_CRUCIBAI_VS_KIMI_AI.md`  
**Warning:** That file asserts CrucibAI **10/10 on every dimension** — treat as **sales draft**, not engineering truth. Prefer **Part 2.1** of this handoff for reconciled messaging.

| Dimension | CrucibAI (claimed) | Kimi (claimed) | Notes |
|-----------|-------------------|----------------|-------|
| Full-app output | 10 | 7 | Subjective |
| Orchestration visibility | 10 | 8 | |
| Long context | 10 | 9 | |
| Agent scale / value | 10 | 8 | |
| Quality visibility | 10 | 6 | |
| Pricing flexibility | 10 | 8 | |
| Docs/Slides/Sheets | 10 | 8 | Verify our product scope |
| UX / polish | 10 | 9 | |
| Bring your own model | 10 | 5 | |
| Onboarding | 10 | 8 | |

---

## Appendix F — “50 things you can build” (category index)

**Source:** `docs/archive/CRUCIBAI_CAPABILITIES_vs_MANUS.md`  
**Caveat:** Lists **agent numbers** and competitive claims that may **not** match current `agent_dag.py`. Use as **idea catalog**, not inventory.

1–10: E-commerce, SaaS, real-time chat, project management, analytics dashboards, CMS, LMS, social networks, mobile (RN), PWA.  
11–20: REST, GraphQL, microservices, webhooks, job queues, authN/Z, file upload, search, caching, DB design.  
21–30: Chatbots, image gen, video gen, voice, recommendations, sentiment, document analysis, predictive analytics, computer vision, NLU.  
31–40: Responsive UI, a11y, dark mode, RTL, component libs, animation, form builder, data viz, tables, i18n.  
41–50: Unit test, integration test, E2E, performance test, security test, code review, compliance, monitoring, incident response, deployment/DevOps.

**Manus comparison sections in that file also claim** latency, cost, DB technology, and agent counts — **verify before reuse**.

---

## Appendix G — Control plane “independent findings” (B3) checklist

**Source:** `docs/CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md` Part B3

1. Dual brain: Dashboard `/ai/chat` vs workspace orchestrator.  
2. Assistant channel during build may be **only** `brain_guidance` → quiet chat.  
3. Task↔job binding: sidebar can open without `jobId`.  
4. Multiple workspace surfaces (`UnifiedWorkspace`, `Workspace`, `WorkspaceManus`).  
5. `useTaskStore` localStorage ≠ enterprise DB task history.  
6. Job switch clears chat; rehydration from events not guaranteed as full log.  
7. Preview/proof empty when job DTO lacks URLs/files.

---

## Appendix H — Engineering priority train (verbatim order)

**Source:** Control plane Part E

1. Single run identity in URL + task store (`jobId` after plan).  
2. Activity feed contract (events → chat **or** always-visible activity).  
3. Preview pipeline verification on Railway (log `job` + `dev-preview`).  
4. Workspace file pull on important steps.  
5. Failed-run UX — never lose Failure DTO.  
6. Optional server-side conversation / event read model.

**Commit train label from doc:** WORKSPACE-TRACE → PREVIEW-DATA → TASK-JOB-BINDING → CLEANUP duplicate workspace routes.

---

*Maintainers: when you complete a backlog row, add a sub-bullet under Part 4 with PR link and date.*
