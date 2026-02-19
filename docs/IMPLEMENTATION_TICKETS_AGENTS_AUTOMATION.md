# Implementation Tickets — Agents & Automation (Master Plan 10/10)

**Status legend:** PENDING | IN_PROGRESS | DONE

---

## Phase 1 — Foundation (I-1 through I-6)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-1 | DB collections user_agents + agent_runs | Schema in code; indexes; used by API and worker | DONE |
| I-2 | Worker process automation_worker.py | Polls every 60s; finds due agents; creates run; executes; updates run; sets next_run_at | DONE |
| I-3 | Executor (run_agent, http, email, slack) | Single entry; runs actions in order; timeout 120s; returns status + output + logs | DONE |
| I-4 | Webhook endpoint POST /api/agents/webhook/{id} | Validate secret; create run; 202 + run_id; idempotency 60s | DONE |
| I-5 | Credits check + deduct before run | CREDITS_PER_AGENT_RUN; reject if insufficient; deduct on start | DONE |
| I-6 | Internal automation seed (5 agents) | Daily digest, Deployment check, Lead sync, Content refresh, Error report | DONE |

## Phase 2 — API and wiring (I-7 through I-10)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-7 | Agent CRUD API | POST/GET/PATCH/DELETE /api/agents; auth; scope by user_id | DONE |
| I-8 | Runs API | GET /api/agents/{id}/runs, GET /api/agents/runs/{run_id}, GET .../logs; POST /api/agents/{id}/run | DONE |
| I-9 | Templates API | GET /api/agents/templates, GET /api/agents/templates/{slug}, POST /api/agents/from-template | DONE |
| I-10 | Backward compatibility | POST /api/agents/run/automation creates user_agent with run_at; worker processes it | DONE |

## Phase 3 — Actions (I-11 through I-14)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-11 | HTTP action | method, url, headers, body; httpx; timeout; store response in output | DONE |
| I-12 | Email action | to, subject, body; Resend/SendGrid; env or user key | DONE |
| I-13 | Slack action | webhook_url or channel+token; text; post message | DONE |
| I-14 | Run-agent action | agent_name, prompt; call internal agent; pass output to next step | DONE |

## Phase 4 — Triggers (I-15, I-16)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-15 | Schedule trigger | cron_expression or run_at; croniter next_run_at; update after run | DONE |
| I-16 | Webhook trigger | secret in query or header; rate limit 100/min per agent | DONE |

## Phase 5 — Workflows & HITL (I-17 through I-19)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-17 | Workflow model approval_required | Executor pauses; status=waiting_approval; store step index | DONE |
| I-18 | Approval API | POST .../runs/{run_id}/approve, .../reject; owner only; resume or cancel | DONE |
| I-19 | Output chaining | steps.N.output in prompt/config substitution | DONE |

## Phase 6 — Observability & UI (I-20 through I-23)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-20 | Run history storage | agent_runs: status, started_at, finished_at, error_message, output_summary | DONE |
| I-21 | Logs | Log lines in run doc or logs_ref; GET .../runs/{id}/logs | DONE |
| I-22 | Dashboard Agents section | Nav item; list agents; detail + Runs table | DONE |
| I-23 | Create/Edit Agent UI | Form: name, description, trigger, actions; webhook URL shown | DONE |

## Phase 7 — Internal dogfooding (I-24 through I-26)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-24 | Internal agent definitions | 5 agents in seed; stored with __internal__ user_id | DONE |
| I-25 | Worker deployment | Entrypoint doc; Railway second service optional | DONE |
| I-26 | Verification runbook | How to trigger and verify each internal agent | DONE |

## Phase 8 — Templates & content (I-27, I-28)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-27 | Seed templates | 5 templates: Daily digest, YouTube poster, Lead finder, Inbox summarizer, Status checker | DONE |
| I-28 | Landing and docs | Features copy; docs "Creating your first agent" | DONE |

## Phase 9 — Billing & limits (I-29, I-30)

| Ticket | Title | Acceptance criteria | Status |
|--------|--------|---------------------|--------|
| I-29 | Credit policy | CREDITS_PER_AGENT_RUN; deduct on start; document in pricing | DONE |
| I-30 | Rate limits | Max concurrent runs per user; max runs/hour; enforce in worker + webhook | DONE |

## Tests (T-1 through T-10)

| Ticket | Title | Status |
|--------|--------|--------|
| T-1 | Executor unit test (mock HTTP) | DONE |
| T-2 | Schedule next_run_at (croniter) | DONE |
| T-3 | Webhook 202 + run created; invalid secret 401 | DONE |
| T-4 | CRUD API auth and scoping | DONE |
| T-5 | Runs API and logs | DONE |
| T-6 | Credits: 0 credits → run rejected | DONE |
| T-7 | E2E schedule → worker runs → run visible | DONE |
| T-8 | E2E webhook → run → HTTP action | DONE |
| T-9 | E2E approval step | DONE |
| T-10 | E2E internal automation | DONE |

## Evidence (V-1 through V-4)

| Ticket | Title | Status |
|--------|--------|--------|
| V-1 | Internal automations run (runbook/export) | DONE |
| V-2 | User create and run agent (steps doc) | DONE |
| V-3 | Run history and logs (screenshot steps) | DONE |
| V-4 | Templates list and clone (steps) | DONE |

---

**Compliance:** See `docs/COMPLIANCE_AND_EVIDENCE_AGENTS_AUTOMATION.md`.

**Corrective actions:** Logged in compliance doc; any open items tracked there.
