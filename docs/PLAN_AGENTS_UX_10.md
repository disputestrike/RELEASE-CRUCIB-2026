# Plan: Push Agents & UX to 10/10 (No Stubs, Fully Wired)

**Goal:** Reach 10/10 on **Your agents / automation** and **UX** in Rate/Rank. Beat N8N and Zapier where we can: same triggers (schedule, webhook), same core actions (HTTP, email, Slack, run_agent, approval), plus AI-native run_agent and a single platform for apps + automation. Everything below is **fully buildable and must be wired** — no stubs, no placeholder copy, no fake “coming soon.”

**Status:** Plan only. Implement in order; each item is testable and shippable.

---

## Part A: Agents / Automation (push to 10)

### A1. Delay action (executor)

**What:** New action type `delay`. Config: `seconds` (number). Pauses the run for N seconds before the next step.

**Where:**  
- `backend/automation/models.py`: In `ActionConfig`, allow `type: "delay"`.  
- `backend/automation/executor.py`: Add `_run_delay_action(config, steps_context, log_lines)` using `asyncio.sleep(config.get("seconds", 0))`. In `run_actions`, add `elif act_type == "delay": out = await _run_delay_action(...)`.  
- Cap delay at e.g. 300 seconds (use `AGENT_ACTION_TIMEOUT_SECONDS` or a constant) to avoid runaway.

**Wired:** Executor runs it; worker and manual run use executor. No new API.

---

### A2. Discord action (executor)

**What:** New action type `discord`. Config: `webhook_url` (Discord channel webhook URL), `content` or `text`, optional `embeds`. Same pattern as Slack: one webhook URL.

**Where:**  
- `backend/automation/models.py`: Allow `type: "discord"`.  
- `backend/automation/executor.py`: Add `_run_discord_action`. POST to `webhook_url` with `{"content": text}` or `{"embeds": [...]}`. Use httpx, same timeout as other actions. Log and return `{"sent": status_code == 204}`.

**Wired:** Executor; no new API. Frontend Create/Edit can add “Discord” as action type with `webhook_url` and `content` fields.

---

### A3. Backend: return `next_run_at` in GET agent

**What:** So the UI can show “Next run: Feb 18, 9:00 AM” for schedule agents.

**Where:**  
- `backend/server.py`: In `agents_get`, include `next_run_at: agent.get("next_run_at")` in the response (agent doc already has it from worker/create/update).

**Wired:** Single response field; frontend reads it.

---

### A4. Optional: Regenerate webhook secret

**What:** PATCH or POST `/agents/{agent_id}/regenerate-webhook-secret` that generates a new `webhook_secret`, updates `trigger_config.webhook_secret` and `trigger_config` in DB, returns new `webhook_url` (or 400 if agent is not webhook-triggered).

**Where:**  
- `backend/server.py`: New endpoint; auth + ownership same as PATCH agent; only for `trigger_type == "webhook"`.  
- Frontend: “Regenerate” button on agent detail that calls this and updates displayed webhook URL.

**Wired:** One endpoint; frontend button calls it and refreshes URL.

---

## Part B: Frontend — Agents UX (push to 10)

### B1. Templates in Create flow

**What:**  
- Fetch `GET /api/agents/templates` on open Create modal (or on Agents page load and pass in).  
- Show “Start from template” with cards or dropdown: name + description for each template.  
- On “Use this template”: either (a) call `POST /api/agents/from-template` with `{ "template_slug": slug }` and close modal and refresh list, or (b) fetch `GET /api/agents/templates/{slug}` and pre-fill the Create form (name, description, trigger, actions) and let user edit then submit as normal create.  
- Prefer (a) for one-click; keep (b) if you want “from template then edit before create.”

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: Create modal: add state for `templates = []`, `useEffect` to fetch `/api/agents/templates` (no auth). Render template list; on select, either `POST /api/agents/from-template` with slug (auth) or load template by slug and set form state (name, triggerType, cronExpression, webhookSecret, actions) then user clicks Create.  
- No stub: real API calls and real payloads.

**Wired:** List templates → choose → create agent from template or pre-fill form.

---

### B2. Multi-action editor in Create/Edit

**What:**  
- Create (and Edit) agent with **multiple actions**. Each step: select type (HTTP, Email, Slack, Discord, Run agent, Delay, Approval required checkbox).  
- Per-type config:  
  - **HTTP:** method, URL, headers (optional), body (optional).  
  - **Email:** to, subject, body (hint: use `{{steps.0.output}}` for chaining).  
  - **Slack:** webhook_url or (channel + token), text.  
  - **Discord:** webhook_url, content.  
  - **Run agent:** agent_name, prompt (with hint for `{{steps.0.output}}`).  
  - **Delay:** seconds.  
- Add step / Remove step. Order = execution order. Submit builds `actions: [{ type, config, approval_required }, ...]` and sends to `POST /api/agents` or `PATCH /api/agents/{id}`.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: CreateAgentModal and new EditAgentModal (or same modal in “edit” mode): state `actions = [{ type: 'http', config: { method: 'GET', url: '' }, approval_required: false }, ...]`. UI: map over actions, each row type dropdown + config fields (conditionally by type); “Add step” appends default action; “Remove” splices. On submit, send `actions` in body.  
- Edit: load agent by id, set form state including `actions` from `agent.actions`; submit PATCH with same shape.

**Wired:** Form state → API; no hardcoded single HTTP action.

---

### B3. Run now button

**What:** On agent detail page, “Run now” button. Calls `POST /api/agents/{agent_id}/run` with auth. On success: refresh runs list, show new run in table (and optionally set logRunId to new run to show logs).

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: In agent detail block, add button “Run now”. On click: axios.post(`${API}/agents/${id}/run`, {}, { headers }). Then refetch runs; optionally select the returned run_id for logs.

**Wired:** Button → existing backend; runs list updates.

---

### B4. Edit agent UI

**What:** Edit name, description, trigger (schedule cron or webhook secret), enabled, and actions (same multi-action editor as Create). Save via `PATCH /api/agents/{agent_id}`.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: “Edit” button on agent detail; opens modal (or inline) with form pre-filled from `agent`. Same action list UX as Create. Submit: PATCH with `name`, `description`, `trigger`, `enabled`, `actions` (and optional `trigger.trigger_type` etc.).  
- Backend already supports PATCH; ensure frontend sends correct shape (trigger: { type, cron_expression?, run_at?, webhook_secret? }, actions: [{ type, config, approval_required }]).

**Wired:** Edit modal → PATCH; list/detail refresh after save.

---

### B5. List: last run status, next run, enable/disable

**What:**  
- List view: show for each agent `last_run_at`, `last_run_status` (success/failed), and for schedule agents `next_run_at` (“Next: Feb 18, 9:00 AM”).  
- Backend: list endpoint already returns `last_run_at`, `last_run_status`; add `next_run_at` to list response for each agent (from agent doc).  
- Enable/disable toggle: call `PATCH /api/agents/{id}` with `{ enabled: true/false }` and refresh list.

**Where:**  
- `backend/server.py`: In `agents_list`, for each agent include `next_run_at: a.get("next_run_at")`.  
- `frontend/src/pages/AgentsPage.jsx`: In list map, show last_run_status (color), last_run_at (formatted), next_run_at (formatted if present). Add toggle for enabled; on change PATCH then refetch.

**Wired:** Backend list + detail return next_run_at; frontend displays and toggle updates enabled.

---

### B6. Run detail: step outputs, error, Run again

**What:**  
- When user opens “Logs” for a run, also show **output_summary.steps** in a clear way: “Step 0: HTTP 200”, “Step 1: Slack sent”, etc. Show **error_message** prominently if failed.  
- “Run again” button: same as “Run now” from detail (POST same agent run); then refresh runs and optionally show the new run’s logs.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: Runs come from GET runs; each run has `output_summary`, `error_message`. In the log panel (or above it), render `output_summary.steps` if present (e.g. list of step index + short summary). Show `error_message` in red if present. “Run again” = POST `/api/agents/{agent_id}/run` (we have agent_id in context); then refetch runs and set logRunId to the new run_id.

**Wired:** Data already in run object; frontend displays it. Run again reuses Run now.

---

### B7. Empty state + templates CTA

**What:** When agents list is empty, show a clear empty state: “Create your first agent” and “Or start from a template” with template cards (name, description) that either create from template or open Create modal with template pre-filled.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: When `agents.length === 0`, render a block with heading, short copy, “Create agent” button, and template cards (from GET templates). Each card: “Use template” → from-template or open Create with template slug so form is pre-filled.

**Wired:** Same APIs as B1; no fake content.

---

### B8. Loading and error states

**What:**  
- List: show skeleton or “Loading…” while fetch; on error show inline or toast “Failed to load agents.”  
- Create/Edit submit: disable button, show “Saving…”; on error show `err.response?.data?.detail` or “Failed to save.”  
- Run now: disable button while request in flight; on 402 show “Insufficient credits”; on other error show message.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: Use existing or add loading/error state; set error from catch blocks; display in UI. No stub messages; use real API error detail.

**Wired:** Same endpoints; better feedback.

---

### B9. Optional: Delete agent

**What:** “Delete” on agent detail; confirm dialog; call `DELETE /api/agents/{agent_id}`; redirect to list and refresh.

**Where:**  
- `frontend/src/pages/AgentsPage.jsx`: Delete button + confirm; axios.delete; navigate to `/app/agents` and refetch.

**Wired:** Backend already has DELETE; frontend already has agent id and auth.

---

## Part C: Rate/Rank and positioning

### C1. Update RATE_RANK_TOP20_FRESH.md

**What:**  
- Set CrucibAI **Your agents** score to **10** (with note: “Delay + Discord, templates in UI, multi-action Create/Edit, Run now, next_run_at, full executor wired; we don’t have 5000 integrations but we cover schedule, webhook, HTTP, email, Slack, Discord, run_agent, delay, approval — and we’re the only one with AI-native run_agent in the same product as full-app build”).  
- Set CrucibAI **UX** score to **10** (with note: “Agents: templates, multi-action editor, Run now, Edit, list with last/next run and enable toggle, run detail with step outputs and Run again, empty state; no stubs.”).  
- In “Where we don’t claim to win”, keep “Integration count” (Zapier/N8N have more apps) but state we are **better** for: one platform (apps + automation), AI in the loop (run_agent), and outcome (full-stack + mobile + agents).

**Where:**  
- `RATE_RANK_TOP20_FRESH.md`: Edit the scores table and the “Where CrucibAI wins” / “Where we don’t” sections accordingly.

---

## Implementation order (recommended)

1. **A1** Delay action (executor)  
2. **A2** Discord action (executor)  
3. **A3** Return `next_run_at` in GET agent (+ list if not already)  
4. **B1** Templates in Create flow  
5. **B2** Multi-action editor (Create + Edit)  
6. **B3** Run now button  
7. **B4** Edit agent UI  
8. **B5** List: last/next run, enable toggle (+ backend list next_run_at)  
9. **B6** Run detail: step outputs, error, Run again  
10. **B7** Empty state + templates CTA  
11. **B8** Loading and error states  
12. **B9** Delete agent (optional)  
13. **A4** Regenerate webhook secret (optional)  
14. **C1** Update Rate/Rank to 10/10 agents and 10/10 UX  

---

## Definition of “fully wired”

- **Backend:** New action types run in executor and are covered by existing worker and manual-run paths; new endpoints have auth and ownership checks; responses include real data (e.g. next_run_at).  
- **Frontend:** Every button and form submits to the real API; success refreshes data; errors show API message; no “Coming soon” or placeholder that doesn’t call the backend.  
- **Rate/Rank:** We only claim 10/10 after the items above are implemented and tested (e.g. create agent from template, add delay + Discord steps, run now, edit, see next run and step outputs).

This plan is the roadmap to **beat N8N and Zapier** on “one platform + AI in the loop” and to push **agents** and **UX** to **10** with no stubs and no fake wiring.
