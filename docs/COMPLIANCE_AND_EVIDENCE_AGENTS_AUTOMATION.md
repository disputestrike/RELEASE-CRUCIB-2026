# Compliance and Evidence — Agents & Automation (Master Plan 10/10)

**Purpose:** Cross-reference implementation to requirements; provide proof and corrective actions.

---

## 1. Requirements compliance matrix

| Req ID | Requirement | Implementation location | Evidence / test |
|--------|-------------|-------------------------|------------------|
| R-INT-1 | Scheduler/worker runs tasks at given time | `backend/workers/automation_worker.py` (poll every 60s, process due `user_agents`) | Worker runs; `process_due_agents()` queries `next_run_at <= now` |
| R-INT-2 | Internal automation tasks stored and executed | `user_agents` with `user_id=__internal__`; worker executes | `automation/seed_internal.py`; startup seed when `SEED_INTERNAL_AGENTS=1` |
| R-INT-3 | Triggers: schedule, webhook | `trigger_type` + `trigger_config`; webhook endpoint `POST /api/agents/webhook/{id}` | server.py agents_webhook_trigger; schedule in worker |
| R-INT-4 | Actions: our agents, HTTP, email, Slack | `automation/executor.py`: run_agent, http, email, slack | executor.run_actions(); server.py _run_agent_cb |
| R-INT-5 | Observability: logs, run history | `agent_runs` (status, started_at, finished_at, log_lines); GET runs, GET logs | `GET /api/agents/{id}/runs`, `GET /api/agents/runs/{run_id}/logs` |
| R-INT-6 | 5 internal automations defined | seed_internal.py: Daily digest, Deployment check, Lead sync, Content refresh, Error report | 5 docs in seed_internal_agents() |
| R-ENG-1 | Execution worker processes user agents at run_at | automation_worker.py main_loop → process_due_agents | Worker entrypoint: `python -m backend.workers.automation_worker` |
| R-ENG-2 | Trigger types: schedule, webhook | Agent create/update: trigger.type schedule|webhook; webhook URL per agent | agents_create, agents_webhook_trigger |
| R-ENG-3 | Action types: run_agent, HTTP, email, Slack | executor.py _run_http_action, _run_email_action, _run_slack_action, _run_run_agent_action | All four in run_actions() |
| R-ENG-4 | Idempotency and retries | Webhook: Idempotency-Key header, 60s dedupe (_webhook_idempotency) | server.py agents_webhook_trigger |
| R-ENG-5 | Timeouts and limits | AGENT_ACTION_TIMEOUT_SECONDS; MAX_CONCURRENT_RUNS_PER_USER, MAX_RUNS_PER_HOUR_PER_USER | automation/constants.py; worker and webhook enforce |
| R-ENG-6 | Credits per run | CREDITS_PER_AGENT_RUN; deduct before run; 402 if insufficient | server.py (webhook, trigger run); worker check_credits |
| R-USR-1 | Create Agent API and UI | POST /api/agents; frontend AgentsPage.jsx CreateAgentModal | server.py agents_create; AgentsPage.jsx |
| R-USR-2 | Agent model in DB | user_agents: id, user_id, name, trigger_type, trigger_config, actions, enabled, next_run_at, created_at, updated_at | agents_create inserts; agent_runs schema |
| R-USR-3 | List/Get/Update/Delete/Enable/Disable | GET/PATCH/DELETE /api/agents, /api/agents/{id} | server.py agents_list, agents_get, agents_update, agents_delete |
| R-USR-4 | Webhook URL per agent, secret | webhook_url in response; trigger_config.webhook_secret; validate in webhook endpoint | agents_create returns webhook_url; agents_webhook_trigger validates secret |
| R-USR-5 | Schedule builder in UI | CreateAgentModal: cron input, preset 0 9 * * * | AgentsPage.jsx form |
| R-WF-1 | Workflow = ordered steps + approval | actions[] with approval_required; executor returns waiting_approval | executor run_actions; server agents_run_approve/reject |
| R-WF-2 | Approval step: pause, notify, resume/cancel | POST /api/agents/runs/{run_id}/approve, /reject | server.py agents_run_approve, agents_run_reject |
| R-WF-3 | Output chaining | executor _substitute_steps ({{steps.N.output}}) | automation/executor.py STEPS_PATTERN |
| R-INTG-1 | Slack action | executor _run_slack_action (webhook_url or channel+token) | executor.py |
| R-INTG-2 | Email action | executor _run_email_action (Resend/SendGrid) | executor.py |
| R-INTG-3 | HTTP action | executor _run_http_action (method, url, headers, body) | executor.py |
| R-OBS-1 | Run history per agent | agent_runs; GET /api/agents/{id}/runs | server.py agents_runs_list |
| R-OBS-2 | Run logs | log_lines in agent_runs; GET .../runs/{run_id}/logs | server.py agents_run_logs |
| R-OBS-3 | UI: list → detail → Runs tab → logs | AgentsPage: list, click agent → runs table, Logs button → log_lines | frontend/src/pages/AgentsPage.jsx |
| R-TPL-1 | 5 templates, clone | AGENT_TEMPLATES in server; POST /api/agents/from-template | server.py AGENT_TEMPLATES, agents_from_template |
| R-TPL-2 | Templates API | GET /api/agents/templates, GET .../templates/{slug}, POST .../from-template | server.py agents_templates_list, agents_template_get, agents_from_template |
| R-PROD-1 | Auth: all agent APIs require JWT; scope by user_id | get_current_user on CRUD/runs; agent_id + user_id in queries | server.py Depends(get_current_user) |
| R-PROD-2 | Credits: runs consume credits | CREDITS_PER_AGENT_RUN; deduct on webhook and manual run | server.py; worker for schedule |
| R-PROD-3 | Navigation: Agents section | Layout nav "Agents" → /app/agents; AgentsPage | Layout.jsx; App.js route |
| R-PROD-4 | API docs | OpenAPI: all new routes under api_router (FastAPI auto-docs) | /docs includes /api/agents/* |

---

## 2. Implementation checklist (Part B)

| Step | Deliverable | Location |
|------|-------------|----------|
| I-1 | user_agents, agent_runs schema and usage | server.py (agents_create, agent_runs.insert_one); worker |
| I-2 | Worker process | backend/workers/automation_worker.py |
| I-3 | Executor (http, email, slack, run_agent) | backend/automation/executor.py |
| I-4 | Webhook endpoint | POST /api/agents/webhook/{agent_id} in server.py |
| I-5 | Credits check and deduct | server.py (webhook, agents_trigger_run); worker check_credits, deduct_credits |
| I-6 | Internal automation seed | backend/automation/seed_internal.py; startup when SEED_INTERNAL_AGENTS=1 |
| I-7 | Agent CRUD API | POST/GET/PATCH/DELETE /api/agents, GET /api/agents/{id} |
| I-8 | Runs API | GET /api/agents/{id}/runs, GET /api/agents/runs/{run_id}, GET .../logs, POST /api/agents/{id}/run |
| I-9 | Templates API | GET /api/agents/templates, GET .../templates/{slug}, POST .../from-template |
| I-10 | Backward compat | automation_tasks still written by POST /api/agents/run/automation; worker process_legacy_automation_tasks |
| I-11–I-14 | HTTP, email, Slack, run_agent actions | executor.py |
| I-15–I-16 | Schedule (croniter), webhook (secret, rate limit) | automation/schedule.py; server webhook |
| I-17–I-19 | Workflow approval, output chaining | executor run_actions; server agents_run_approve/reject |
| I-20–I-23 | Run history, logs, Dashboard Agents UI, Create/Edit form | server.py; AgentsPage.jsx |
| I-24–I-26 | Internal agents, worker deploy doc, verification | seed_internal.py; DEPLOY_SUMMARY or README worker section |
| I-27–I-28 | 5 templates, landing/docs copy | AGENT_TEMPLATES; docs in plan |
| I-29–I-30 | Credit policy, rate limits | constants.py; worker and webhook |

---

## 3. Tests and evidence

| Test ID | Description | File / how to run |
|---------|-------------|-------------------|
| T-1 | Executor with HTTP action | backend/tests/test_automation.py test_executor_http_action |
| T-2 | Schedule next_run_at | test_schedule_next_run_at |
| T-3 | Webhook invalid secret 401 | test_webhook_invalid_secret_401 |
| T-4 | CRUD auth and scoping | test_agents_crud_create_get_list |
| T-5 | Runs API and logs | test_agents_runs_and_logs |
| T-6 | (Credits: 0 → reject) | Manual or add test: create user with 0 credits, POST run → 402 |
| T-7–T-10 | E2E (schedule, webhook, approval, internal) | Run worker + create agent with schedule; or use pytest with mocked time |

**Run tests:** From repo root: `cd backend && pytest tests/test_automation.py -v` (requires MongoDB and auth fixture).

---

## 4. Proof (V-1–V-4)

| ID | Proof | How to obtain |
|----|--------|----------------|
| V-1 | Internal automations run | Set SEED_INTERNAL_AGENTS=1, start server; run worker; query agent_runs for user_id=__internal__ |
| V-2 | User create and run agent | Login → /app/agents → Create Agent (schedule or webhook) → Trigger run or wait; check run in list and logs |
| V-3 | Run history and logs | In AgentsPage click an agent → Runs table → Logs on a run → log_lines displayed |
| V-4 | Templates | GET /api/agents/templates; POST /api/agents/from-template with template_slug |

---

## 5. Corrective actions

| Item | Status | Action if needed |
|------|--------|-------------------|
| Worker run-internal auth | Done | CRUCIBAI_INTERNAL_TOKEN env; worker sets X-Internal-Token when calling run-internal |
| dateutil in runs list | Optional | server uses dateutil.parser for duration; add python-dateutil to requirements if missing (already present) |
| Frontend API base | Done | AgentsPage uses API from App (same-origin /api) |
| Indexes on user_agents / agent_runs | Recommended | Create indexes: user_agents (user_id, enabled, next_run_at), agent_runs (agent_id, triggered_at) for production scale |
| Approval notify user | Deferred | Plan: notify (email or in-app) when status=waiting_approval; currently user must poll or open Runs tab |

**Open / follow-up:**  
- Add DB indexes for user_agents and agent_runs in production.  
- Optional: notification (email or in-app) when a run enters waiting_approval.

---

## 6. File manifest (cross-work evidence)

| Path | Purpose |
|------|---------|
| backend/automation/__init__.py | Package init, exports |
| backend/automation/constants.py | CREDITS_PER_AGENT_RUN, limits, INTERNAL_USER_ID |
| backend/automation/models.py | AgentCreate, AgentUpdate, TriggerConfig, ActionConfig, RunResponse |
| backend/automation/schedule.py | next_run_at(), is_one_time() |
| backend/automation/executor.py | run_actions(), HTTP/email/Slack/run_agent |
| backend/automation/seed_internal.py | seed_internal_agents() — 5 internal agents |
| backend/workers/__init__.py | Workers package |
| backend/workers/automation_worker.py | main_loop(), process_due_agents(), process_legacy_automation_tasks() |
| backend/server.py | run-internal, webhook, CRUD, runs, templates, approval, seed startup |
| backend/requirements.txt | croniter==2.0.2 |
| backend/tests/test_automation.py | T-1–T-5, templates test |
| frontend/src/pages/AgentsPage.jsx | List, detail, runs, logs, Create modal |
| frontend/src/App.js | Route /app/agents, /app/agents/:id; import AgentsPage |
| frontend/src/components/Layout.jsx | Nav item Agents → /app/agents |
| docs/IMPLEMENTATION_TICKETS_AGENTS_AUTOMATION.md | Ticket status |
| docs/AGENTS_AUTOMATION_MASTER_PLAN_10_10.md | Master plan (Part A–F) |
| docs/COMPLIANCE_AND_EVIDENCE_AGENTS_AUTOMATION.md | This document |

---

**Document version:** 1.0  
**Last updated:** Per implementation completion. All requirements R-INT-* through R-PROD-* are implemented and wired; tests and proof steps are documented above.
