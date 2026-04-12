# Plan & Requirements: 10/10 Best Design

**Goal:** Make CrucibAI the best design—agentic loop, generic tools, structured state, real execution everywhere, and feedback-driven flow. No fake agents; every step either runs a tool or updates shared state that drives the next step.

**Status:** Plan + requirements only. Implementation follows this doc.

---

## 1. Requirements (What “10/10” Means)

### R1. Agentic tool loop (must have)
- **R1.1** One or more LLM “actor” agents that **propose tool calls** (e.g. `{"tool": "file", "action": "write", "path": "src/App.jsx", "content": "..."}`).
- **R1.2** A **tool runner** that executes only a fixed set of safe tools: `file` (read/write/list/mkdir), `run` (subprocess in workspace), `api` (HTTP with SSRF protection), `browser` (navigate/screenshot with URL allowlist), `db` (SQLite in workspace only).
- **R1.3** Tool results (stdout, file contents, HTTP response, etc.) are **fed back** to the LLM so it can propose the next tool call or finish.
- **R1.4** Loop continues until the actor returns “done” or a max step count (e.g. 50).

### R2. Structured project state (must have)
- **R2.1** A **project state** store (e.g. JSON file or DB table per project): `plan`, `requirements`, `stack`, `decisions`, `artifacts` (paths written), `test_results`, `deploy_result`.
- **R2.2** Planner and Requirements Clarifier **write** to this state (structured), not only to a markdown file. Downstream agents **read** from this state.
- **R2.3** All “real” outputs (e.g. chosen stack, approved plan) are in state so the rest of the pipeline and the UI can use them without parsing markdown.

### R3. Real execution for all critical steps (must have)
- **R3.1** **Plan** → stored in state (real write).
- **R3.2** **Requirements** → stored in state (real write).
- **R3.3** **Frontend / Backend / Test code** → produced by the agentic loop using the `file` tool (real write to workspace).
- **R3.4** **Tests** → run via `run` tool (e.g. `pytest tests/` or `npm test`) (real run).
- **R3.5** **Deploy** → run via `run` tool (e.g. `vercel --yes`) or deploy API (real run).
- **R3.6** **Security / Lint** → run via `run` tool (e.g. `bandit`, `eslint`) (real run).
- No step that “only suggests” without either writing to state or running a tool.

### R4. Feedback and recovery (should have)
- **R4.1** If tests fail, the actor can receive the failure output and **propose further tool calls** (e.g. fix file, re-run tests).
- **R4.2** Optional: explicit “retry” or “fix” phase when test/lint step returns non‑zero.
- **R4.3** All tool outputs (and optionally summaries) are stored in project state for audit and UI.

### R5. Safety and security (must have)
- **R5.1** **File tool:** All paths resolved and restricted to project workspace (no traversal).
- **R5.2** **Run tool:** Allowlist of commands (e.g. `pytest`, `npm`, `npx`, `vercel`, `railway`, `netlify`) or restrict to a sandbox; no arbitrary shell.
- **R5.3** **API tool:** SSRF protection (block private IPs, `file:`, allowlist if needed).
- **R5.4** **Browser tool:** URL allowlist or blocklist (e.g. no `localhost` unless allowlisted).
- **R5.5** **DB tool:** Only SQLite in workspace; no arbitrary connection strings from the client.
- **R5.6** All tool endpoints (e.g. `/api/tools/*`) require auth and rate limits.

### R6. UX and observability (should have)
- **R6.1** Real-time progress: which tool is running, which step of the loop (e.g. “Step 3: running pytest).
- **R6.2** Project state and last N tool calls/results available to the UI (e.g. for “why did this fail?”).
- **R6.3** Quality score and deploy URL still available as today (for rate/rank and user value).

---

## 2. High-Level Plan (Phases)

### Phase 1: Structured state + tool contract (foundation)
- **1.1** Define **project state schema** (e.g. `plan: string[]`, `requirements: dict`, `stack: dict`, `artifacts: string[]`, `test_results: dict`, `deploy_result: dict`, `tool_log: list`).
- **1.2** Persist state in `workspace/<project_id>/state.json` (or DB) and load/save from server and runner.
- **1.3** Define **tool-call schema** (e.g. `tool`, `action`, `params`) and **tool result schema** (e.g. `success`, `stdout`, `stderr`, `data`).
- **1.4** Implement **tool runner** (single function) that accepts a tool call and returns a result; internally call existing FileAgent, run subprocess for `run`, APIAgent with SSRF checks, etc. All paths/commands restricted per R5.
- **Deliverable:** State file exists; one “execute_tool(tool_call, project_id)” that runs safely and returns a result.

### Phase 2: Agentic loop (one actor)
- **2.1** Add an **orchestrator** that: (a) loads project state and workspace context, (b) builds a prompt that includes “available tools” and “last N tool results”, (c) calls LLM with a system prompt that says “output a JSON object: either `{\"done\": true, \"summary\": \"...\"}` or `{\"tool_calls\": [{\"tool\": \"...\", ...}]}`”.
- **2.2** Loop: call LLM → parse response → if tool_calls, run each via execute_tool, append results to state and context → call LLM again; if done, exit and save final state.
- **2.3** Integrate with existing build trigger: when user starts build, optionally use “agentic mode” (this loop) instead of the current DAG, or run the loop for a subset (e.g. “code gen + test + fix” only).
- **Deliverable:** One build path that uses the agentic loop; state and tool_log updated each step.

### Phase 3: Planner & Requirements write to state
- **3.1** Planner output is parsed (or prompted) to a **list of tasks**; write to `state.plan`.
- **3.2** Requirements Clarifier output is parsed (or prompted) to **structured requirements**; write to `state.requirements`.
- **3.3** Stack Selector writes to `state.stack`. Downstream prompts include “Current plan: …, Requirements: …, Stack: …” from state.
- **Deliverable:** First three “agents” are real: they update structured state that the rest of the pipeline reads.

### Phase 4: All code and run steps via tools
- **4.1** In the agentic loop, the actor produces frontend/backend/test code by **calling the file tool** (write to `src/App.jsx`, `server.py`, `tests/...`). No “fake” code agent that only appends to a markdown file.
- **4.2** Test run is a **run** tool call (`pytest tests/` or `npm test`). Result goes to state and back to the LLM.
- **4.3** Deploy is a **run** tool call (or dedicated deploy API with tokens). Result (URL, status) in state.
- **4.4** Security/lint steps are **run** tool calls (bandit, eslint, etc.). Results in state.
- **Deliverable:** No step that only “suggests”; code exists on disk and tests/deploy/lint actually ran.

### Phase 5: Feedback and retry
- **5.1** When a tool returns failure (e.g. tests failed), the next LLM turn receives the failure and can issue more tool calls (e.g. edit file, re-run tests).
- **5.2** Optional: max “fix” rounds (e.g. 3) to avoid infinite loops.
- **5.3** Optional: human-in-the-loop (e.g. “Tests failed; show user and ask to continue or abort”).
- **Deliverable:** Build can recover from test/lint failures by further tool use.

### Phase 6: Safety, auth, and observability
- **6.1** Apply R5 to all tools (path restriction, command allowlist, SSRF, URL rules). Audit existing File/API/Browser/DB/Deploy agents and harden.
- **6.2** Require auth (and optionally scope) for all tool execution and state access.
- **6.3** Expose progress (current step, last tool, last result snippet) via WebSocket or polling so the UI shows “Step 5: running pytest” and final state.
- **Deliverable:** Safe, authenticated, observable 10/10 pipeline.

---

## 3. Success Criteria (10/10 Checklist)

- [ ] **Agentic loop:** LLM proposes tool calls; runner executes them; results fed back; loop until done or limit.
- [ ] **Structured state:** Plan, requirements, stack, artifacts, test_results, deploy_result in one place; read/write by pipeline and UI.
- [ ] **Planner & Requirements:** Write to state (real); no “only markdown in outputs/”.
- [ ] **All code and runs real:** Frontend/backend/tests written via file tool; tests run via run tool; deploy run via run/API; security/lint run via run tool.
- [ ] **Feedback:** Test/lint failure can trigger more tool calls (fix and retry).
- [ ] **Safety:** Paths, commands, URLs, DB constrained per R5; tool endpoints behind auth.
- [ ] **Observability:** Progress and last results visible to the UI.

---

## 4. Out of Scope (For This Plan)

- Replacing the entire current DAG with the loop in one shot (can coexist: “classic DAG” vs “agentic build”).
- Adding new LLM providers (use existing).
- Changing frontend UI in detail (only need progress and state hooks).
- Full human-in-the-loop (optional later).

---

## 5. Order of Work (Summary)

1. **State schema + persistence** (Phase 1.1–1.2)  
2. **Tool contract + execute_tool** (Phase 1.3–1.4)  
3. **Agentic loop** (Phase 2)  
4. **Planner/Requirements/Stack → state** (Phase 3)  
5. **Code + test + deploy + lint via tools** (Phase 4)  
6. **Feedback/retry** (Phase 5)  
7. **Safety + auth + observability** (Phase 6)  

This plan and these requirements are the path to a **10/10 design**: agentic, structured, real execution everywhere, with feedback and safety.
