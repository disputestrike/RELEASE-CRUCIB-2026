# Full Plan: All 120 Agents — Integrated, Working, True (No Games)

**Purpose:** Every one of the 120 agents must be a **true agent**: a real, verifiable action (run a tool, write to state, or write an artifact). No "prompt only" or "tag." This is the plan to wire everything so we can present and show it—and be better than Manus.

---

## 1. What a "True Agent" Is (No Games)

A **true agent** does at least one of the following. If it does none, it is not a true agent.

| Type | Meaning | Example |
|------|--------|--------|
| **Tool run** | Executes a real tool (file write, subprocess, API call, browser, DB). | File Tool Agent writes files to workspace. Test Executor runs pytest. |
| **State write** | Writes to structured project state (plan, requirements, stack, decisions) that other agents or the UI read. | Planner writes `state.plan`. Requirements Clarifier writes `state.requirements`. |
| **Artifact write** | Writes a real artifact to the project workspace (code file, config file, doc file) that the system or deploy uses. | Documentation Agent writes `README.md`. SEO Agent writes `public/index.html` meta or `robots.txt`. |

**Not a true agent:** Only returning text that is then stored in a generic "outputs" folder with no structured use. That is a **prompt + persist**, not a true agent.

So the plan is: for **all 120**, assign one of: **tool run**, **state write**, or **artifact write** (and implement it). No exceptions.

---

## 2. Shared Infrastructure (What We Must Build Once)

- **Project state**  
  One store per project: `state.json` or DB with `plan`, `requirements`, `stack`, `decisions`, `artifacts[]`, `test_results`, `deploy_result`, `tool_log[]`. Agents that "decide" something write here; agents that need context read from here.

- **Tool layer**  
  Single entry point: `execute_tool(project_id, tool_name, params)`. Tools: `file` (read/write/list/mkdir in workspace), `run` (allowlisted commands: pytest, npm, npx, vercel, bandit, eslint, etc.), `api` (HTTP with SSRF protection), `browser` (navigate/screenshot with URL rules), `db` (SQLite in workspace only). All paths and commands restricted. Auth required.

- **Workspace**  
  One directory per project: `workspace/<project_id>/`. All file tools and run tools use only this tree. All artifacts (code, docs, configs) live here.

Once we have state + tool layer + workspace, every agent is wired to one of: **read state → call tool** or **read state + previous outputs → write state** or **read state + previous outputs → call tool (artifact write)**.

---

## 3. All 120 Agents: Real Behavior and Wiring

Each row: **Agent** | **Real behavior (what it must do)** | **Wiring (how)**.

| # | Agent | Real behavior | Wiring |
|---|--------|----------------|--------|
| 1 | Planner | Write structured plan (list of tasks) to state | Parse LLM output → `state.plan`; persist to state file. |
| 2 | Requirements Clarifier | Write structured requirements to state | Parse LLM output → `state.requirements`; persist. |
| 3 | Stack Selector | Write chosen stack (frontend, backend, db) to state | Parse LLM output → `state.stack`; persist. |
| 4 | Frontend Generation | Write React/JSX code to workspace file | LLM → code; tool `file` write `src/App.jsx` (or path from stack). |
| 5 | Backend Generation | Write backend code to workspace file | LLM → code; tool `file` write `server.py` or equivalent. |
| 6 | Database Agent | Write schema to workspace file | LLM → SQL/text; tool `file` write `schema.sql`. |
| 7 | Database Tool Agent | Apply schema to SQLite in workspace | Already real: aiosqlite.executescript in workspace. |
| 8 | API Integration | Write API client code to workspace file | LLM → code; tool `file` write e.g. `api/client.js` or inject into app. |
| 9 | Test Generation | Write test code to workspace file | LLM → code; tool `file` write `tests/test_basic.py` or equivalent. |
| 10 | Test Executor | Run tests in workspace | Already real: run `pytest` or `npm test` via tool `run`; write result to state. |
| 11 | Image Generation | Call image API (Together.ai), write URLs to state/workspace | Already real: API call; write URLs to state.images. |
| 12 | Video Generation | Call video API (Pexels), write URLs to state/workspace | Already real: API call; write URLs to state.videos. |
| 13 | Security Checker | Run security scanner (bandit/eslint) in workspace, write report to state | Tool `run` bandit/eslint; parse result → state.security_report. |
| 14 | UX Auditor | Run a11y check or scan JSX for ARIA, write report to state | Tool `run` (e.g. axe) or scan files; write state.ux_report. |
| 15 | Performance Analyzer | Run perf check or count lines, write to state | Tool `run` or file scan; write state.performance_report. |
| 16 | Deployment Agent | Produce deploy config; Deployment Tool Agent runs deploy | Write deploy config to state; deploy step uses it. |
| 17 | Deployment Tool Agent | Run deploy (Vercel/Railway/Netlify) from workspace | Already real: subprocess/API. |
| 18 | Error Recovery | Write runbook/recovery steps to workspace file | LLM → text; tool `file` write `docs/runbook.md`. |
| 19 | Memory Agent | Write project summary to state | LLM → summary; state.memory_summary. |
| 20 | File Tool Agent | Write generated code/files to workspace | Already real: FileAgent. |
| 21 | Browser Tool Agent | Navigate/screenshot when URL in context | Already real: Playwright. |
| 22 | API Tool Agent | HTTP request when URL in context | Already real: httpx. |
| 23 | Documentation Agent | Write README to workspace | LLM → markdown; tool `file` write `README.md`. |
| 24 | PDF Export | Write PDF spec or generate PDF to workspace | LLM → spec; tool `file` write `docs/summary.pdf` (or spec for generator). |
| 25 | Excel Export | Write CSV/Excel spec or file to workspace | LLM → spec or CSV; tool `file` write `docs/tracking.csv` or equivalent. |
| 26 | Markdown Export | Write project summary markdown to workspace | LLM → markdown; tool `file` write `docs/summary.md`. |
| 27 | Design Agent | Write design spec (JSON) to state | LLM → JSON; state.design_spec. |
| 28 | Layout Agent | Write updated frontend with placeholders to workspace | LLM → code; tool `file` write/overwrite frontend file. |
| 29 | SEO Agent | Write meta/robots/sitemap to workspace | LLM → content; tool `file` write `public/robots.txt`, meta in index or config. |
| 30 | Content Agent | Write copy to workspace or state | LLM → copy; tool `file` write `content/copy.json` or state.content. |
| 31 | Brand Agent | Write brand spec (JSON) to state | LLM → JSON; state.brand_spec. |
| 32 | Validation Agent | Write validation rules/schema to workspace | LLM → rules; tool `file` write `validation/schema.json` or in code. |
| 33 | Auth Setup Agent | Write auth config or code snippet to workspace | LLM → code/config; tool `file` write e.g. `auth/config.json` or inject. |
| 34 | Payment Setup Agent | Write payment config or code to workspace | LLM → code; tool `file` write payment snippet or config. |
| 35 | Monitoring Agent | Write monitoring config to workspace | LLM → config; tool `file` write `monitoring/sentry.yaml` or equivalent. |
| 36 | DevOps Agent | Write CI/CD config to workspace | LLM → YAML; tool `file` write `.github/workflows/ci.yml` or Dockerfile. |
| 37 | Webhook Agent | Write webhook handler spec/code to workspace | LLM → code; tool `file` write webhook handler file. |
| 38 | Email Agent | Write email config/template to workspace | LLM → config; tool `file` write `email/config.json` or template. |
| 39 | Legal Compliance Agent | Write compliance checklist to state/workspace | LLM → checklist; tool `file` write `docs/compliance.md`. |
| 40 | Scraping Agent | If URLs suggested, Browser/API tool can visit; write URLs to state | LLM → URLs; state.scrape_urls; optional tool run. |
| 41 | Automation Agent | Write cron/task config to workspace | LLM → config; tool `file` write `cron/tasks.json` or equivalent. |
| 42 | GraphQL Agent | Write GraphQL schema to workspace | LLM → schema; tool `file` write `schema.graphql`. |
| 43 | WebSocket Agent | Write WebSocket code to workspace | LLM → code; tool `file` write ws handler or inject. |
| 44 | i18n Agent | Write locale files or config to workspace | LLM → JSON/strings; tool `file` write `locales/en.json`. |
| 45 | Caching Agent | Write cache config to workspace | LLM → config; tool `file` write `cache/redis.json` or equivalent. |
| 46 | Rate Limit Agent | Write rate-limit config/code to workspace | LLM → code; tool `file` write middleware or config. |
| 47 | Search Agent | Write search config to workspace | LLM → config; tool `file` write `search/config.json`. |
| 48 | Analytics Agent | Write analytics config to workspace | LLM → config; tool `file` write `analytics/events.json`. |
| 49 | API Documentation Agent | Write OpenAPI/Swagger to workspace | LLM → YAML/JSON; tool `file` write `openapi.yaml`. |
| 50 | Mobile Responsive Agent | Write responsive config or CSS vars to workspace | LLM → config; tool `file` write `styles/responsive.json` or inject. |
| 51 | Migration Agent | Write migration scripts to workspace | LLM → SQL/code; tool `file` write `migrations/001_init.sql`. |
| 52 | Backup Agent | Write backup script/config to workspace | LLM → script; tool `file` write `scripts/backup.sh`. |
| 53 | Notification Agent | Write notification config to workspace | LLM → config; tool `file` write `notifications/config.json`. |
| 54 | Code Review Agent | Run linter (e.g. eslint) and write report to state | Tool `run` linter; write state.code_review_report. |
| 55 | Staging Agent | Write staging config to workspace | LLM → config; tool `file` write `staging.env` or equivalent. |
| 56 | A/B Test Agent | Write experiment config to workspace | LLM → config; tool `file` write `experiments/ab.json`. |
| 57 | Feature Flag Agent | Write feature-flag config to workspace | LLM → config; tool `file` write `flags.json`. |
| 58 | Error Boundary Agent | Write error-boundary code to workspace | LLM → code; tool `file` write component or inject. |
| 59 | Logging Agent | Write logging config to workspace | LLM → config; tool `file` write `logging/config.json`. |
| 60 | Metrics Agent | Write metrics config to workspace | LLM → config; tool `file` write `metrics/prometheus.yaml`. |
| 61 | Audit Trail Agent | Write audit config/code to workspace | LLM → code; tool `file` write audit middleware or config. |
| 62 | Session Agent | Write session config to workspace | LLM → config; tool `file` write `session/config.json`. |
| 63 | OAuth Provider Agent | Write OAuth config to workspace | LLM → config; tool `file` write `auth/oauth.json`. |
| 64 | 2FA Agent | Write 2FA config to workspace | LLM → config; tool `file` write `auth/2fa.json`. |
| 65 | Stripe Subscription Agent | Write Stripe config to workspace | LLM → config; tool `file` write `payments/stripe.json`. |
| 66 | Invoice Agent | Write invoice template to workspace | LLM → template; tool `file` write `templates/invoice.html`. |
| 67 | CDN Agent | Write CDN config to workspace | LLM → config; tool `file` write `cdn/config.json`. |
| 68 | SSR Agent | Write SSR config to workspace | LLM → config; tool `file` write `next.config.js` snippet or doc. |
| 69 | Bundle Analyzer Agent | Run bundle analyzer, write report to state | Tool `run` e.g. npx webpack-bundle-analyzer; state.bundle_report. |
| 70 | Lighthouse Agent | Run Lighthouse (if available), write report to state | Tool `run` lighthouse; state.lighthouse_report. |
| 71 | Schema Validation Agent | Write request/response schema to workspace | LLM → schema; tool `file` write `schemas/api.json`. |
| 72 | Mock API Agent | Write mock definitions to workspace | LLM → mocks; tool `file` write `mocks/handlers.js`. |
| 73 | E2E Agent | Write E2E test file to workspace | LLM → code; tool `file` write `e2e/spec.js`. |
| 74 | Load Test Agent | Write load-test script to workspace | LLM → script; tool `file` write `load/k6.js`. |
| 75 | Dependency Audit Agent | Run npm audit / pip audit, write report to state | Tool `run` npm audit; state.dependency_audit. |
| 76 | License Agent | Write license file to workspace | LLM → text; tool `file` write `LICENSE`. |
| 77 | Terms Agent | Write terms draft to workspace | LLM → text; tool `file` write `docs/terms.md`. |
| 78 | Privacy Policy Agent | Write privacy draft to workspace | LLM → text; tool `file` write `docs/privacy.md`. |
| 79 | Cookie Consent Agent | Write cookie banner config to workspace | LLM → config; tool `file` write `consent/cookies.json`. |
| 80 | Multi-tenant Agent | Write tenant schema/config to workspace | LLM → SQL/config; tool `file` write `tenant/schema.sql`. |
| 81 | RBAC Agent | Write roles config to workspace | LLM → config; tool `file` write `auth/roles.json`. |
| 82 | SSO Agent | Write SSO config to workspace | LLM → config; tool `file` write `auth/sso.json`. |
| 83 | Audit Export Agent | Write export script to workspace | LLM → script; tool `file` write `scripts/export_audit.sh`. |
| 84 | Data Residency Agent | Write residency config to workspace | LLM → config; tool `file` write `compliance/residency.json`. |
| 85 | HIPAA Agent | Write HIPAA checklist to workspace | LLM → checklist; tool `file` write `docs/hipaa.md`. |
| 86 | SOC2 Agent | Write SOC2 checklist to workspace | LLM → checklist; tool `file` write `docs/soc2.md`. |
| 87 | Penetration Test Agent | Write pentest checklist to workspace; optional run | LLM → checklist; tool `file` write `security/pentest.md`. |
| 88 | Incident Response Agent | Write runbook to workspace | LLM → runbook; tool `file` write `docs/incident_runbook.md`. |
| 89 | SLA Agent | Write SLA doc to workspace | LLM → doc; tool `file` write `docs/sla.md`. |
| 90 | Cost Optimizer Agent | Write cost checklist to workspace | LLM → checklist; tool `file` write `docs/cost.md`. |
| 91 | Accessibility WCAG Agent | Write WCAG checklist to workspace | LLM → checklist; tool `file` write `docs/wcag.md`. |
| 92 | RTL Agent | Write RTL CSS/config to workspace | LLM → config; tool `file` write `styles/rtl.css` or config. |
| 93 | Dark Mode Agent | Write theme config to workspace | LLM → config; tool `file` write `themes/dark.json`. |
| 94 | Keyboard Nav Agent | Write keyboard nav spec to workspace | LLM → spec; tool `file` write `a11y/keyboard.md`. |
| 95 | Screen Reader Agent | Write screen-reader spec to workspace | LLM → spec; tool `file` write `a11y/screenreader.md`. |
| 96 | Component Library Agent | Write component list/config to workspace | LLM → config; tool `file` write `components/manifest.json`. |
| 97 | Design System Agent | Write design tokens to workspace | LLM → tokens; tool `file` write `design/tokens.json`. |
| 98 | Animation Agent | Write animation config to workspace | LLM → config; tool `file` write `animations/config.json`. |
| 99 | Chart Agent | Write chart config to workspace | LLM → config; tool `file` write `charts/config.json`. |
| 100 | Table Agent | Write table component config to workspace | LLM → config; tool `file` write `components/table.json`. |
| 101 | Form Builder Agent | Write form schema to workspace | LLM → schema; tool `file` write `forms/schema.json`. |
| 102 | Workflow Agent | Write workflow definition to workspace | LLM → definition; tool `file` write `workflows/main.json`. |
| 103 | Queue Agent | Write queue config to workspace | LLM → config; tool `file` write `queue/config.json`. |
| 104 | Vibe Analyzer Agent | Write vibe spec (JSON) to state | LLM → JSON; state.vibe_spec. |
| 105 | Voice Context Agent | Write voice-derived requirements to state | LLM → structured; state.voice_requirements. |
| 106 | Video Tutorial Agent | Write tutorial script to workspace | LLM → script; tool `file` write `docs/tutorial_script.md`. |
| 107 | Aesthetic Reasoner Agent | Write aesthetic report to state | LLM → JSON; state.aesthetic_report. |
| 108 | Collaborative Memory Agent | Write team prefs to state | LLM → JSON; state.team_preferences. |
| 109 | Real-time Feedback Agent | Write feedback log to state | LLM → summary; state.feedback_log. |
| 110 | Mood Detection Agent | Write mood/approach to state | LLM → JSON; state.mood. |
| 111 | Accessibility Vibe Agent | Write a11y vibe report to state | LLM → JSON; state.accessibility_vibe. |
| 112 | Performance Vibe Agent | Write perf vibe report to state | LLM → JSON; state.performance_vibe. |
| 113 | Creativity Catalyst Agent | Write ideas to state | LLM → JSON; state.creative_ideas. |
| 114 | IDE Integration Coordinator Agent | Write IDE config to workspace | LLM → config; tool `file` write `.vscode/settings.json` or equivalent. |
| 115 | Multi-language Code Agent | Write alternate language files to workspace | LLM → code; tool `file` write e.g. `api_go/main.go` or equivalent. |
| 116 | Team Collaboration Agent | Write collaboration config to workspace | LLM → config; tool `file` write `docs/collab.md`. |
| 117 | User Onboarding Agent | Write onboarding flow to workspace | LLM → flow; tool `file` write `onboarding/flow.json`. |
| 118 | Customization Engine Agent | Write customization config to workspace | LLM → config; tool `file` write `customization/config.json`. |
| 119 | Design Iteration Agent | Write iteration log to state | LLM → log; state.design_iterations. |
| 120 | (All 120 DAG agents are listed above.) | — | Every agent: state write, or file-tool artifact write, or run/api/browser/db tool run. No agent is prompt-only. |

**Table covers all 120 agents in the DAG.** Each has exactly one real behavior: state write, artifact write (file tool), or tool run (run/api/browser/db).

---

## 4. Implementation Plan: Phases to Wire All 120

### Phase A: Foundation (state + tool layer)
- Implement project **state** (schema + load/save) in `workspace/<project_id>/state.json`.
- Implement **execute_tool(project_id, tool_name, params)** with: file, run (allowlist), api (SSRF-safe), browser (URL rules), db (SQLite workspace only). Enforce path/command/URL safety. Require auth.
- Ensure **workspace** is the only place file/run tools can touch.

### Phase B: State writers (agents that write to state)
- Wire: Planner, Requirements Clarifier, Stack Selector, Design Agent, Brand Agent, Memory Agent, Vibe Analyzer Agent, Voice Context Agent, Aesthetic Reasoner Agent, Collaborative Memory Agent, Real-time Feedback Agent, Mood Detection Agent, Accessibility Vibe Agent, Performance Vibe Agent, Creativity Catalyst Agent, Design Iteration Agent.
- Each: run LLM (or rule) → parse output → write to state (plan, requirements, stack, design_spec, brand_spec, memory_summary, vibe_spec, etc.). No "only output to a random .md file."

### Phase C: Artifact writers (agents that write files via tool)
- Wire every agent that "produces code, config, or doc" to call **file** tool: Frontend Generation, Backend Generation, Database Agent, API Integration, Test Generation, Documentation Agent, SEO Agent, Content Agent, Validation Agent, Auth Setup Agent, Payment Setup Agent, Monitoring Agent, DevOps Agent, Webhook Agent, Email Agent, Legal Compliance Agent, Automation Agent, GraphQL Agent, WebSocket Agent, i18n Agent, Caching Agent, Rate Limit Agent, Analytics Agent, API Documentation Agent, Mobile Responsive Agent, Migration Agent, Backup Agent, Notification Agent, Staging Agent, A/B Test Agent, Feature Flag Agent, Error Boundary Agent, Logging Agent, Metrics Agent, Audit Trail Agent, Session Agent, OAuth Provider Agent, 2FA Agent, Stripe Subscription Agent, Invoice Agent, CDN Agent, SSR Agent, Schema Validation Agent, Mock API Agent, E2E Agent, Load Test Agent, License Agent, Terms Agent, Privacy Policy Agent, Cookie Consent Agent, Multi-tenant Agent, RBAC Agent, SSO Agent, Audit Export Agent, Data Residency Agent, HIPAA Agent, SOC2 Agent, Penetration Test Agent, Incident Response Agent, SLA Agent, Cost Optimizer Agent, Accessibility WCAG Agent, RTL Agent, Dark Mode Agent, Keyboard Nav Agent, Screen Reader Agent, Component Library Agent, Design System Agent, Animation Agent, Chart Agent, Table Agent, Form Builder Agent, Workflow Agent, Queue Agent, Video Tutorial Agent, IDE Integration Coordinator Agent, Multi-language Code Agent, Team Collaboration Agent, User Onboarding Agent, Customization Engine Agent, Error Recovery, PDF Export, Excel Export, Markdown Export, Layout Agent.
- Each: run LLM (or use previous outputs) → get content → **execute_tool(project_id, "file", {action: "write", path: "...", content: "..."})**. Paths determined by agent (e.g. Documentation → README.md, SEO → public/robots.txt).

### Phase D: Tool runners (agents that run a real tool)
- Already real: File Tool Agent, Database Tool Agent, Browser Tool Agent, API Tool Agent, Deployment Tool Agent, Test Executor.
- Add real run for: Security Checker (run bandit/eslint), UX Auditor (run axe or scan), Performance Analyzer (run or scan), Code Review Agent (run linter), Bundle Analyzer Agent (run bundle analyzer), Lighthouse Agent (run Lighthouse), Dependency Audit Agent (run npm audit).
- Each: **execute_tool(project_id, "run", {command: allowlisted_cmd, args: [...]})** and write result to state (e.g. state.security_report).

### Phase E: Integration and ordering
- Keep DAG order; for each agent, call: (1) load state + previous outputs, (2) if state writer → update state, (3) if artifact writer → call file tool, (4) if tool runner → call run tool and update state. Persist state after each agent.
- Expose state and last N tool results to UI (for "why did this fail?" and demos).

### Phase F: Verification and presentation
- **Verification:** For each of the 120, a test or script that runs the agent and checks: either state was updated, or a file was written, or a tool was run. No agent without a check.
- **Presentation:** One matrix: "120 agents × Real behavior" and a demo flow: start build → show state + workspace filling with real files and real runs. No "we have 120 prompts."

---

## 5. How This Beats Manus and Is 10/10

- **Manus:** Many tools, one or a few "actors" that call tools. We do the same (tool layer) **plus** 120 named agents each with a **defined real behavior**. So we have both: a unified tool layer and 120 specialized roles that each do something concrete.
- **No games:** Every row in the table above is either state write, artifact write, or tool run. No "just a prompt."
- **Presentable:** We can show: (1) list of 120 agents, (2) for each, one line "real behavior," (3) live run where state and workspace are updated and tools run. That is a true company-grade design: everything wired, everything verifiable, nothing that would make someone laugh.

---

## 6. What We Must Do (Summary)

1. **Build once:** State schema + persistence; execute_tool (file, run, api, browser, db) with safety and auth.
2. **Wire all 120:** For each agent, implement the "Real behavior" from the table (state write, or file tool write, or run tool + state write).
3. **Remove "prompt only":** No agent that only returns text to a generic output file with no structured use. Either it writes state, or it writes an artifact, or it runs a tool.
4. **Verify and present:** Tests/checks per agent; one demo that shows the full pipeline with real state and real artifacts and real tool runs.

This is the full plan for all 120 agents, integrated and working, with every one a true agent. No games.
