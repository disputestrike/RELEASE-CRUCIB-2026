# Master Prompt: Complete Source of Truth / Engine Room / Data Room

**Purpose:** This prompt, when executed, produces the single top-tier document that contains everything about CrucibAI: every feature, function, how it works, where it is, why it beats competitors, full tech spec, architecture, developer notes, engine room, data room — nothing hidden. Use it to regenerate or extend the full source-of-truth document.

**How to use:** Run this prompt (or feed it to an AI/system that has access to the codebase and all docs). The output must be one comprehensive document. Fix any broken references or gaps found during generation.

---

## The Prompt (copy below)

```
You are producing CrucibAI’s single SOURCE OF TRUTH document for investors, new team, and developers. Hide nothing. Incorporate every existing doc, rating, ranking, and code fact. Output one structured markdown document that includes ALL of the following. If something is missing or broken in the codebase, note it under "What's left / Gaps."

1. WHAT & WHY
   - What CrucibAI is (product, one-liner, positioning).
   - Why we built it (problem, solution, unique advantage).
   - Who it’s for (marketers, agencies, devs, product teams).
   - Why "CrucibAI" and "Inevitable AI"; Monday→Friday messaging.

2. FULL FEATURE LIST (every feature)
   - For each feature: name, what function/API/page implements it, how it works (flow), why and how it beats competitors, where in the app (route, component, backend route).
   - Include: Auth (register, login, MFA, Google OAuth), Projects, Build (plan, phases, DAG, 120 agents), Workspace (editor, Sandpack, tools, chat, voice), AgentMonitor (phases, progress, Build state, retry), Agents (user automations: schedule, webhook, run_agent, executor steps), Import (paste, zip, git), Deploy (ZIP, Vercel, Netlify, GitHub), Tokens & billing (Stripe, bundles, usage), Settings (API keys, env), Share, Templates, Learn, Pricing, Enterprise, Security, Admin (dashboard, users, billing, analytics, legal), Audit log, Blog, Benchmarks, Export, ManusComputer-style widget, command palette, shortcuts, quality score, Try these / API key nudge.

3. FULL TECH SPEC & ARCHITECTURE
   - Stack: backend (FastAPI, Python, Motor, uvicorn), frontend (React, CRACO, Radix, Monaco), DB (MongoDB), payments (Stripe), deploy (Vercel, Netlify), infra (Railway).
   - Directory structure (every important folder and file with one-line purpose).
   - Data flow: frontend → API (REACT_APP_BACKEND_URL, /api/*) → server.py → DB / workers / tools.
   - WebSocket: /ws/projects/{id}/progress; where consumed (BuildProgress, AgentMonitor).

4. EVERY FUNCTION & CONNECTIVITY (by layer)
   - Backend: List every major route in server.py (auth, build, agents, workspace, deploy, tokens, admin, stripe, audit, MFA, referrals, etc.) with method, path, purpose, and which frontend page/hook calls it.
   - Frontend: List every page (route path + component) and what backend endpoints it uses.
   - Admin: Every admin route and corresponding Admin* page.
   - Automation: executor steps (HTTP, email, Slack, run_agent, approval); schedule; webhook; where defined and how triggered.

5. 120 AGENTS (algorithm & real behavior)
   - Source: agent_dag.py, agent_real_behavior.py, real_agent_runner.py.
   - For each agent (or by phase): name, depends_on, real behavior (state write / artifact write / tool run), where output goes (state key or file path or tool).
   - Plan-first flow; quality score; retry; token optimization.
   - run_agent in user automations: same swarm invokable as step; executor.py.

6. INTEGRATIONS & EXPORTS
   - MongoDB, Stripe, Vercel, Netlify, GitHub, ZIP, Resend/SendGrid, Slack, OpenAI/Anthropic, Google OAuth.
   - For each: how it’s used, env var if any, where in code.

7. COMPETITIVE POSITION (why we win)
   - Pull from RATE_RANK_*.md, CRUCIBAI_COMPETITIVE_RANKING.md, UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA.md, HOW_WE_COMPARE_TO_MANUS_KIMI_TOP.md, OUR_SANDBOX_PREVIEW_AND_MANUS_STYLE.md.
   - vs Manus, Cursor, Kimi, Replit, N8N, Zapier, Bolt, v0, etc.: what we have that they don’t; what they have that we don’t; our 10/10 claims and evidence.

8. RATINGS & RANKINGS (the truth)
   - Overall 10/10 evidence (RATE_RANK_COMPARE.md, RATE_RANK_TOP10, TOP20, TOP50).
   - What was left to reach 10/10 and what’s done; compliance matrix; 5-layer validation; proof scripts.

9. WHERE IN THE APP (map)
   - Table: User action / Feature → Frontend route → Component(s) → Backend route(s).
   - Public vs app vs admin routes; Layout, sidebar, ProtectedRoute, AdminRoute.

10. DEVELOPER NOTES & DOCUMENTATION
    - How to run locally (backend, frontend, env).
    - How to verify (pytest, npm test, security_audit, CI).
    - Key files to read: server.py, orchestration.py, agent_dag.py, agent_real_behavior.py, real_agent_runner.py, project_state.py, tool_executor.py, automation/executor.py, Workspace.jsx, AgentMonitor, Dashboard, BACKEND_FRONTEND_CONNECTION.md, CODEBASE_SOURCE_OF_TRUTH.md.
    - Endpoint map (frontend call → backend route); CORS, health check, "Backend unavailable" fix.

11. ENGINE ROOM & DATA ROOM
    - Everything an investor or acquirer would need: scale (lines, files, tests), critical paths (all wired), placeholders (MONGO for deploy test, image slots, template HTTP targets), gaps (Ads: Option A "you run the ads we built the stack"; no native Meta/Google).
    - Security: rate limits, headers, CORS, JWT, MFA, Stripe webhook verification, security_audit.
    - Tests & CI: enterprise-tests.yml (lint, security, frontend, backend, E2E).

12. ROADMAPS & WHAT'S LEFT
    - From CRUCIBAI_10_10_ROADMAP.md, AGENTS_ROADMAP.md, GAPS_AND_INTEGRATIONS_REVIEW.md, PLAN_AND_REQUIREMENTS_10_10.md.
    - What’s implemented vs placeholder vs not built; post-launch options (native ads, outcome guarantee, etc.).

13. MANUS COMPUTER STYLE & UX
    - ManusComputer.jsx: what it shows (step, thinking, tokens); where used (Workspace); wiring to real build if any.
    - AgentMonitor: phases, event timeline, Build state panel, per-agent tokens, quality score, retry, Open in Workspace, View Live.
    - Command palette, shortcuts, model selector, Tools tab.

14. INCORPORATE ALL DOCUMENTS
    - Cite or summarize: CODEBASE_SOURCE_OF_TRUTH, FULL_SCOPE_INVESTOR_ENGINE_ROOM, BACKEND_FRONTEND_CONNECTION, TRUTH_120_AGENTS, RATE_RANK_*, AGENTS_REAL_BEHAVIOR_MATRIX, FULL_PLAN_ALL_120_AGENTS, LAUNCH_SEQUENCE_AUDIT, CRUCIBAI_MASTER_BUILD_PROMPT, docs/UNIQUE_COMPETITIVE_ADVANTAGE_AND_NEW_BIG_IDEA, docs/MESSAGING_AND_BRAND_VOICE, TESTING.md, and any other key .md that defines product or proof.

15. CATCH ALL / FIX BROKEN
    - While generating, note any broken link, missing route, or inconsistency between docs and code. List under "Corrections & Gaps" so the reader knows what to fix or verify.
```

---

## After Running the Prompt

- Save the output as **docs/CRUCIBAI_SOURCE_OF_TRUTH_ENGINE_ROOM.md** (or the single "bible" doc path you use).
- Update "Last updated" and any version/scale numbers from the actual codebase.
- Run a quick check: grep for key routes and pages to ensure the doc matches the code.
