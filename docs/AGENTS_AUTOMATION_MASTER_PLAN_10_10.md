# CrucibAI Agents & Automation — Master Plan (10/10)
## End-to-end plan to be #1 in agent creation and automation (internal + user-facing)

**Goal:** CrucibAI uses full automation and agentic workflows **internally** (dogfooding), and **users** can create, run, and observe their own agents/automations. We lead the space vs N8N, Zapier, Make. No gaps: requirements, implementation, wiring, testing, verification, proof, and integration with current product and strategy.

---

# PART A — REQUIREMENTS (WHAT WE BUILD)

## A1. Internal use (CrucibAI runs agents on itself)

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-INT-1 | CrucibAI has a **scheduler/worker** that runs tasks at a given time (cron or run_at). | At least one internal job runs on schedule (e.g. daily health report). |
| R-INT-2 | Internal **automation tasks** are stored and executed (not just stored). | DB collection for internal ops tasks; worker executes them. |
| R-INT-3 | **Triggers** we use ourselves: schedule (cron), webhook. | Internal flows can be triggered by time or by incoming webhook. |
| R-INT-4 | **Actions** we use: call our own agents (scrape, content, export), call HTTP API, send notification (email/Slack). | At least 3 internal automations that use these actions. |
| R-INT-5 | **Observability**: logs, run history, success/failure for internal runs. | We can see when each internal agent ran and whether it succeeded. |
| R-INT-6 | **Concrete internal automations** (dogfooding): e.g. daily digest, deployment health check, lead/contact sync, content refresh, error report. | At least 5 internal automations defined, running, and verified. |

## A2. User-facing: execution engine

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-ENG-1 | **Execution worker** processes user `automation_tasks` (or `user_agents`) at `run_at` or on trigger. | User-created scheduled task runs once at the specified time. |
| R-ENG-2 | **Trigger types**: (1) Schedule (cron or one-time run_at), (2) Webhook (HTTP POST to unique URL). | User can create agent with “every day 9am” or “when webhook is called.” |
| R-ENG-3 | **Action types**: (1) Run one of our agents (by name/prompt), (2) HTTP request (URL, method, body), (3) Send email, (4) Post to Slack (and later YouTube, Sheets, etc.). | At least these four action types implemented and callable from a user agent. |
| R-ENG-4 | **Idempotency and retries**: failed runs can retry with backoff; duplicate webhook calls within a window are deduplicated. | Retry policy configurable; at least one retry on 5xx; idempotency key or window for webhooks. |
| R-ENG-5 | **Timeouts and limits**: max run duration per execution, max concurrent runs per user (or per plan). | No run exceeds N seconds; concurrency limit enforced. |
| R-ENG-6 | **Credits/billing**: each agent run consumes credits (or separate “agent run” quota). | Runs deduct credits; over-limit runs are rejected or queued. |

## A3. User-facing: create and manage agents

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-USR-1 | **Create Agent** API and UI: name, description, trigger (schedule or webhook), one or more actions. | User can create an agent via API and from dashboard. |
| R-USR-2 | **Agent model**: id, user_id, name, description, trigger_config (type, cron_expression or webhook_secret), actions (ordered list of action configs), enabled, created_at, updated_at. | Stored in DB; API to CRUD. |
| R-USR-3 | **List / Get / Update / Delete / Enable / Disable** agents. | Full CRUD + enable/disable; list shows run counts or last run. |
| R-USR-4 | **Webhook URL** per agent: unique, secret (or signed), so only the owner can invoke. | Each agent gets a URL like /api/agents/webhook/{agent_id}?secret=... or signed. |
| R-USR-5 | **Schedule builder** in UI: preset (daily 9am, weekly Monday, etc.) or custom cron. | User can pick preset or enter cron without knowing syntax (optional advanced cron). |

## A4. User-facing: multi-agent workflows and human-in-the-loop

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-WF-1 | **Workflow** = ordered list of steps; each step is an action (agent run, HTTP, email, Slack) or a **wait for approval**. | One workflow can have multiple steps; at least one “approval” step type. |
| R-WF-2 | **Approval step**: execution pauses; user is notified; user approves/rejects in UI or via link; execution resumes or cancels. | At least one workflow with approval step runs end-to-end. |
| R-WF-3 | **Chaining**: output of step N can be passed as input to step N+1 (e.g. scrape URL → content agent → Slack). | Documented and tested for at least two steps. |
| R-WF-4 | **Conditional branching** (optional): if condition on step output, run branch A else B. | Optional for 10/10; can be Phase 2. |

## A5. Integrations (actions and triggers)

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-INTG-1 | **Slack**: action “Post message to Slack” (channel or DM, text + optional blocks). | User can add Slack action with webhook URL or bot token; message posts. |
| R-INTG-2 | **Email**: action “Send email” (to, subject, body; use Resend/SendGrid API). | User provides API key or we use workspace email key; email sends. |
| R-INTG-3 | **HTTP**: action “Make HTTP request” (URL, method, headers, body). | Generic HTTP action works for any API. |
| R-INTG-4 | **YouTube** (optional for v1): action “Upload video” or “Schedule post” (via YouTube API). | Documented and tested or clearly scoped for next phase. |
| R-INTG-5 | **Google Sheets** (optional for v1): action “Add row” or “Update cell.” | Same as above. |
| R-INTG-6 | **Trigger: Inbound email** (optional): e.g. send to agent@crucibai.com → run agent. | Can be Phase 2. |

## A6. Observability and UX

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-OBS-1 | **Run history** per agent: run_id, agent_id, triggered_at, triggered_by (schedule/webhook), status (success/failed/cancelled), duration, error_message (if failed), output summary. | Stored in DB; API to list runs for an agent. |
| R-OBS-2 | **Run logs**: store stdout/stderr or structured log lines per run (configurable retention). | At least last 1K lines or 7 days per run retrievable. |
| R-OBS-3 | **UI**: Agent list → Agent detail → Runs tab (table with status, time, duration, link to logs). | User can see runs and open logs from dashboard. |
| R-OBS-4 | **Alerts** (optional): notify user on N consecutive failures (email or Slack). | Configurable per agent or account. |

## A7. Agent templates and marketplace (positioning)

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-TPL-1 | **Templates**: pre-built agent definitions (e.g. “Daily digest”, “YouTube poster”, “Lead finder”) that user can clone and configure. | At least 5 templates; clone creates a copy user can edit. |
| R-TPL-2 | **Templates API**: list templates, get template, create agent from template (with overrides). | Used by UI and by power users. |
| R-TPL-3 | **Landing/marketing**: page or section “Automations & agents” with use cases and templates. | Content and CTAs exist; linked from main nav or pricing. |

## A8. Integration with current CrucibAI product

| ID | Requirement | Success criterion |
|----|-------------|-------------------|
| R-PROD-1 | **Auth**: all agent APIs require auth (JWT); agent and runs scoped by user_id (or team_id if we add teams). | No access to other users’ agents or runs. |
| R-PROD-2 | **Credits**: agent runs consume credits (or dedicated “automation run” quota); free tier gets a small run limit per month. | Billing/usage docs updated; enforcement in worker. |
| R-PROD-3 | **Navigation**: Dashboard has “Agents” or “Automations” section; Create Agent CTA. | Visible in main app nav/sidebar. |
| R-PROD-4 | **API docs**: OpenAPI/Swagger (or docs site) includes all agent/automation endpoints. | All new endpoints documented with examples. |
| R-PROD-5 | **Projects link** (optional): agent can be “attached” to a project (e.g. “deploy this project when I run this agent”). | Optional for v1. |

---

# PART B — IMPLEMENTATION (STEP-BY-STEP)

## B1. Foundation: data model and execution worker

| Step | Task | Details |
|------|------|---------|
| I-1 | **DB collections** | Add or extend: `user_agents` (id, user_id, name, description, trigger_type, trigger_config, actions[], enabled, created_at, updated_at). Add `agent_runs` (id, agent_id, user_id, triggered_at, triggered_by, status, started_at, finished_at, error_message, output_summary, logs_ref). Optionally keep `automation_tasks` for backward compatibility and migrate to `user_agents` or map 1:1. |
| I-2 | **Worker process** | New runnable: `worker/automation_worker.py` (or `backend/workers/automation_worker.py`). Loop: every 60s (or configurable) query `user_agents` where enabled and trigger_type=schedule and next_run_at <= now (or cron match); for each, create an `agent_runs` row (status=running), invoke executor, update run (status=success/failed), set next_run_at for schedule. Use asyncio or separate process; same MongoDB as main app. |
| I-3 | **Executor** | Single function: given agent doc, resolve actions in order; for each action (type: run_agent | http | email | slack), call internal API or HTTP/email/Slack. For run_agent: call existing `/api/agents/run/{agent_name}` or equivalent with prompt from action config. Pass through output to next step if workflow supports it. Timeout per action (e.g. 120s). |
| I-4 | **Webhook endpoint** | `POST /api/agents/webhook/<agent_id>` (or signed token in query). Validate secret or signature; find agent by id, check enabled; create run, enqueue or run synchronously (or async), return 202 with run_id. Idempotency: optional idempotency_key header; dedupe within 60s. |
| I-5 | **Credits** | Before executing a run: check user credits (or agent run quota); deduct on start or on success (policy TBD). Reject with 402 or queue if insufficient. |
| I-6 | **Internal automation** | Bootstrap: insert into DB (or use same `user_agents` with internal user_id) 5 internal “agents”: e.g. Daily health digest (schedule 9am), Deployment check (schedule every 6h), Lead sync (webhook), Content refresh (schedule daily), Error report (schedule daily). Worker runs them; store runs in same `agent_runs`. |

**Deliverables:** Worker runs in CI/staging; at least one internal and one user schedule run successfully; webhook triggers one run.

## B2. API and backend wiring

| Step | Task | Details |
|------|------|---------|
| I-7 | **Agent CRUD API** | `POST /api/agents` (create), `GET /api/agents` (list), `GET /api/agents/{id}` (get), `PATCH /api/agents/{id}` (update), `DELETE /api/agents/{id}`. Request/response models for trigger_config (schedule: cron_expression, run_at; webhook: secret), actions (type, config). All require auth; scope by user_id. |
| I-8 | **Runs API** | `GET /api/agents/{id}/runs` (paginated), `GET /api/agents/runs/{run_id}` (single run + logs). Optional: `POST /api/agents/{id}/run` (trigger run now, for testing). |
| I-9 | **Templates API** | `GET /api/agents/templates` (list), `GET /api/agents/templates/{slug}` (get), `POST /api/agents/from-template` (body: template_slug, overrides). Templates stored in code or DB (read-only table). |
| I-10 | **Backward compatibility** | Keep `POST /api/agents/run/automation` and `GET /api/agents/run/automation-list`; either (a) migrate to create a `user_agent` with one-time run_at and same payload, or (b) let them write to `automation_tasks` and have worker also process that collection (legacy path) until deprecated. |

**Deliverables:** All endpoints implemented, auth and scoping verified, OpenAPI updated.

## B3. Actions: HTTP, email, Slack, run_agent

| Step | Task | Details |
|------|------|---------|
| I-11 | **HTTP action** | Executor step: method, url, headers (dict), body (optional). Use httpx async; timeout from agent config or default. Store response status and body (truncated) in run output. |
| I-12 | **Email action** | Config: to, subject, body (or template_id). Use Resend or SendGrid from env (or user’s connected account). Executor calls send API. |
| I-13 | **Slack action** | Config: webhook_url or channel + token; text; optional blocks. Post to Slack Incoming Webhook or chat.postMessage. |
| I-14 | **Run-agent action** | Config: agent_name (e.g. Scraping Agent, Content Agent), prompt (or prompt_template with placeholders from previous step output). Executor calls internal `_run_agent(agent_name, prompt, user)` (reuse existing server-side logic); capture response and pass to next step. |

**Deliverables:** Each action type tested with a real run; run history shows success/failure and output.

## B4. Triggers: schedule and webhook

| Step | Task | Details |
|------|------|---------|
| I-15 | **Schedule** | trigger_config: cron_expression (e.g. "0 9 * * *") or run_at (one-time ISO). Worker computes next_run_at from cron (use croniter or similar). On run, set next_run_at for next occurrence. |
| I-16 | **Webhook** | trigger_config: secret (random string). URL: `/api/agents/webhook/{agent_id}?secret=...` or header X-Webhook-Secret. Validate; create run; return 202. Rate limit per agent (e.g. 100/min). |

**Deliverables:** Schedule triggers at correct time; webhook triggers run; both appear in run history.

## B5. Multi-step workflows and approval (human-in-the-loop)

| Step | Task | Details |
|------|------|---------|
| I-17 | **Workflow model** | actions[] in agent doc: each item has type, config, and optional approval_required: true. Executor: when approval_required, create run with status=waiting_approval; store run_id and step index; notify user (email or in-app). |
| I-18 | **Approval API** | `POST /api/agents/runs/{run_id}/approve` and `POST /api/agents/runs/{run_id}/reject` (body optional: comment). Only run owner. Update run: resume from step or set status=cancelled. Worker or a “resume” endpoint continues execution. |
| I-19 | **Output chaining** | Each step’s result (e.g. JSON or text) stored in run context; next step’s prompt or config can reference {{steps.0.output}} or similar. Simple placeholder substitution in executor. |

**Deliverables:** One workflow with 2 steps + 1 approval step runs end-to-end; user approves from UI; run completes.

## B6. Observability and UI

| Step | Task | Details |
|------|------|---------|
| I-20 | **Run history storage** | Every run: insert into `agent_runs` with status, started_at, finished_at, error_message, output_summary. Optionally store logs in separate collection or object store (logs_ref). |
| I-21 | **Logs** | During execution, append lines to in-memory buffer or stream to DB; after run, save logs_ref (e.g. S3 key or list of log lines). `GET /api/agents/runs/{run_id}/logs` returns log content. |
| I-22 | **Dashboard UI** | New section “Agents” (or “Automations”): list of user’s agents (name, trigger, last run, status). Click → detail: edit agent, Runs table (triggered_at, status, duration, link to logs). Button “Create Agent.” |
| I-23 | **Create/Edit Agent UI** | Form: name, description, trigger type (schedule / webhook), schedule builder (presets + cron), actions (add step: type dropdown, then config fields). Save calls POST/PATCH /api/agents. Show webhook URL and secret after create. |

**Deliverables:** User can create an agent from UI, see it run, and see run history and logs.

## B7. Internal dogfooding (CrucibAI runs its own agents)

| Step | Task | Details |
|------|------|---------|
| I-24 | **Internal agent definitions** | Define 5 internal agents (e.g. in seed script or config): Daily digest (Content Agent + Email), Deployment health (HTTP to our health endpoint + Slack if down), Lead sync (webhook → our CRM or sheet), Content refresh (Scraping Agent or Content Agent + store), Error report (aggregate errors from DB + email). Store with internal system user_id or service account. |
| I-25 | **Worker deployment** | Run worker alongside API (same host or separate container). In Railway: optional second service “worker” that runs `python -m backend.workers.automation_worker` (or similar). Ensure worker has same env (MONGO_URL, API keys for Slack/Resend). |
| I-26 | **Verification** | For each internal agent: trigger once (schedule or webhook), confirm run in agent_runs, confirm side effect (email sent, Slack message, etc.). Document in runbook. |

**Deliverables:** All 5 internal automations running in production or staging; verified and documented.

## B8. Templates and content

| Step | Task | Details |
|------|------|---------|
| I-27 | **Seed templates** | Create 5 template definitions: Daily digest, YouTube poster (placeholder or with YouTube action), Lead finder (scrape + filter + notify), Inbox summarizer (webhook + content agent + email), Status page checker (schedule + HTTP + Slack). Store in DB or JSON files; load in templates API. |
| I-28 | **Landing and docs** | Add “Automations & agents” to Features or Pricing; short copy: “Create agents that run on your schedule or on trigger. Post, scrape, notify, integrate.” Link to dashboard and templates. Update main docs with “Creating your first agent” and “Triggers and actions.” |

**Deliverables:** 5 templates available; landing and docs updated.

## B9. Billing and limits

| Step | Task | Details |
|------|------|---------|
| I-29 | **Credit policy** | Define: X credits per agent run (e.g. 1 run = 5 credits for run_agent, 1 for HTTP). Or separate “automation runs” quota per plan (e.g. 100 runs/month free, 1000 Builder, etc.). Implement deduction in worker before execute; reject if insufficient. |
| I-30 | **Rate limits** | Per user: max N concurrent runs; max M runs per hour (to prevent runaway). Enforce in worker and in webhook endpoint. |

**Deliverables:** Credits or quota enforced; rate limits applied; documented in pricing.

---

# PART C — TESTING (VERIFICATION)

## C1. Unit and integration tests

| ID | Test | Scope |
|----|------|--------|
| T-1 | **Executor** | Mock agent doc; run executor with one action (HTTP to mock server); assert run status and output. |
| T-2 | **Schedule next_run_at** | Given cron "0 9 * * *", assert next_run_at is next 9am. |
| T-3 | **Webhook** | POST to webhook URL with valid secret; assert 202 and one new run created; invalid secret returns 401. |
| T-4 | **CRUD API** | Create agent, get, list, update, delete; assert 401 without auth; assert cannot access other user’s agent. |
| T-5 | **Runs API** | Create run (by trigger), get run, get runs list; assert logs endpoint returns content. |
| T-6 | **Credits** | User with 0 credits; trigger run; assert run rejected or queued with clear error. |

## C2. End-to-end tests

| ID | Test | Scope |
|----|------|--------|
| T-7 | **E2E: Create agent (schedule) → worker runs it → run visible** | Create agent with schedule “every minute” (for test); wait 2 min; assert run in history and status success (or failed with known reason). |
| T-8 | **E2E: Webhook → run → action (HTTP)** | Create agent with webhook trigger and HTTP action (e.g. to webhook.site). Call webhook URL; assert run created and HTTP request received. |
| T-9 | **E2E: Approval step** | Create workflow with one approval step; trigger; assert run in waiting_approval; call approve; assert run completes. |
| T-10 | **E2E: Internal automation** | Trigger one internal agent (e.g. webhook); assert run in DB and side effect (e.g. Slack message in test channel). |

## C3. Manual verification and proof

| ID | Proof | Evidence |
|----|--------|----------|
| V-1 | **Internal automations run** | Screenshot or export of agent_runs for internal agents over 7 days; or runbook showing “last run” for each. |
| V-2 | **User can create and run agent** | Screen recording: create agent (schedule + Slack action), save, wait for run or trigger webhook, show run success and Slack message. |
| V-3 | **Run history and logs** | Screenshot of Runs table and log viewer for one run. |
| V-4 | **Templates** | Screenshot of template list and “Create from template” flow. |

---

# PART D — INTEGRATION WITH CURRENT PRODUCT AND STRATEGY

## D1. Codebase integration

| Area | Integration |
|------|-------------|
| **Auth** | Reuse existing JWT and get_current_user; all /api/agents/* require auth; agent_id and runs scoped by user_id. |
| **Credits** | Reuse existing credits collection and deduction helpers; add “agent_run” or “automation_run” as a usage type; show in Token Center or Usage page. |
| **Dashboard** | Add “Agents” or “Automations” in sidebar/nav; route to Agents list and Agent detail (create/edit, runs, logs). |
| **API** | All new routes under api_router (e.g. /api/agents, /api/agents/{id}, /api/agents/{id}/runs, /api/agents/webhook/{id}, /api/agents/templates). |
| **Worker** | New entrypoint (e.g. `backend/workers/automation_worker.py`); same repo; deploy as second process or second Railway service. |

## D2. Content and positioning

| Item | Content |
|------|---------|
| **Tagline** | “Build apps agentically. Run agents on your schedule and triggers.” (or similar) |
| **Features page** | Section “Automations & agents”: triggers (schedule, webhook), actions (Slack, email, HTTP, our agents), workflows, templates, observability. |
| **Pricing** | “X agent runs/month” or “Included in Builder/Pro” with run limits; or “Runs use your credits.” |
| **Landing** | One hero or use-case strip: “Create a YouTube poster agent,” “Find leads automatically,” “Daily digest in your inbox.” |
| **Docs** | “Creating your first agent,” “Triggers and actions,” “Templates,” “Run history and logs,” “Webhook security.” |

## D3. Roadmap visibility

| Item | Action |
|------|--------|
| **Public roadmap** | If you have one, add “Agent creation and automation” as shipped or in progress. |
| **Changelog** | Release note: “Agents & automations: create agents that run on schedule or webhook; Slack, email, HTTP, and our AI agents; run history and logs; templates.” |

---

# PART E — PHASED ROLLOUT (ORDER OF EXECUTION)

## Phase 1 — Execution and internal use (Weeks 1–3)

1. Data model: `user_agents`, `agent_runs` (I-1).  
2. Worker + executor (I-2, I-3).  
3. Webhook endpoint (I-4).  
4. Credits and limits (I-5, I-29, I-30).  
5. Internal automations (I-6, I-24, I-25, I-26).  
6. Tests T-1–T-4, T-7, T-8, V-1.

**Exit criteria:** Worker runs in staging/prod; at least 5 internal automations running and verified; one user schedule and one webhook run verified.

## Phase 2 — User-facing API and UI (Weeks 4–5)

1. Agent CRUD and Runs API (I-7, I-8).  
2. Backward compatibility (I-10).  
3. Dashboard: Agents section, list, detail, Create/Edit form (I-22, I-23).  
4. Schedule and webhook triggers (I-15, I-16).  
5. Tests T-5, T-7, T-8; proof V-2, V-3.

**Exit criteria:** User can create an agent from UI, set schedule or webhook, see runs and logs.

## Phase 3 — Actions and integrations (Weeks 6–7)

1. HTTP, email, Slack, run_agent actions (I-11–I-14).  
2. Templates API and seed templates (I-27, I-9).  
3. Templates in UI and landing (I-28).  
4. Tests T-7, T-8 with Slack/email; proof V-4.

**Exit criteria:** User can add HTTP, email, Slack, and “Run our agent” steps; 5 templates available and cloneable.

## Phase 4 — Workflows and human-in-the-loop (Weeks 8–9)

1. Workflow model and output chaining (I-17, I-19).  
2. Approval step and API (I-18).  
3. UI: add step type “Approval,” show waiting runs and Approve/Reject.  
4. Test T-9; proof for approval flow.

**Exit criteria:** Multi-step workflow with approval runs end-to-end; user can approve from UI.

## Phase 5 — Polish and #1 positioning (Weeks 10–12)

1. Observability: logs retention, alerts (R-OBS-2, R-OBS-4).  
2. Rate limits and billing docs (I-30, D2 Pricing).  
3. Landing, Features, Pricing, Docs (D2).  
4. Optional: YouTube/Sheets actions (R-INTG-4, R-INTG-5).  
5. Full regression and proof (V-1–V-4); security review (auth, webhook secret, scoping).

**Exit criteria:** All requirements R-INT-* through R-PROD-* satisfied or explicitly deferred; documentation and proof complete; “#1 in agent creation and automation” messaging live.

---

# PART F — CHECKLIST (NOTHING FORGOTTEN)

## Requirements

- [ ] R-INT-1 to R-INT-6 (internal use)  
- [ ] R-ENG-1 to R-ENG-6 (execution engine)  
- [ ] R-USR-1 to R-USR-5 (create and manage agents)  
- [ ] R-WF-1 to R-WF-4 (workflows, approval)  
- [ ] R-INTG-1 to R-INTG-6 (integrations)  
- [ ] R-OBS-1 to R-OBS-4 (observability)  
- [ ] R-TPL-1 to R-TPL-3 (templates, marketplace)  
- [ ] R-PROD-1 to R-PROD-5 (product integration)

## Implementation

- [ ] I-1 to I-30 (all steps in B1–B9)

## Testing

- [ ] T-1 to T-10 (unit, integration, E2E)  
- [ ] V-1 to V-4 (manual verification and proof)

## Integration and strategy

- [ ] D1 (codebase integration)  
- [ ] D2 (content and positioning)  
- [ ] D3 (roadmap visibility)

## Process

- [ ] Phases 1–5 executed in order  
- [ ] Exit criteria signed off per phase  
- [ ] Security and billing review before Phase 5 close

---

**Document version:** 1.0  
**Scope:** End-to-end plan for CrucibAI to be #1 in agent creation and automation (internal + user-facing), with full implementation, wiring, testing, verification, and integration. No requirements, implementation steps, or verification items omitted.
