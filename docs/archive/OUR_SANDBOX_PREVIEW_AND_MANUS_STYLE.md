# Where’s Our Code? Sandbox? Preview? How We Match Manus (and What’s Missing)

You asked: **Where’s our code? Do we have a sandbox? How does ours work? How do we see preview? How do we do all of that like Manus? We need to be better.**

Here’s the honest map and gap list.

---

## 1. Where’s Our Code? (How Ours Works)

| Piece | Where it lives | What it does |
|-------|----------------|--------------|
| **Project files (generated app)** | `backend/workspace/<project_id>/` | All generated code (e.g. `src/App.jsx`, `server.py`, `README.md`) is written here by the 120 agents via `execute_tool(project_id, "file", ...)` and the File Tool Agent. |
| **Orchestration** | `backend/server.py` (`run_orchestration_v2`, `_run_single_agent_with_context`) | Runs the DAG: phases → agents → LLM or real tool → `run_agent_real_behavior` → persist. |
| **Real tools** | `backend/real_agent_runner.py`, `backend/tool_executor.py` | File/Browser/API/DB/Deploy agents run real tools; `execute_tool` does file/run/api/browser/db with safety. |
| **State** | `backend/workspace/<project_id>/state.json` | Plan, requirements, stack, reports, tool_log. Written by state-writer agents. |
| **Progress UI** | `frontend`: **AgentMonitor** (BuildProgress, phases, Build state panel), **WebSocket** `ws/projects/{id}/progress` | User sees phase, current agent, progress %, tokens. Build state panel shows plan/requirements/stack/tool_log. |
| **“Manus Computer” widget** | `frontend/components/ManusComputer.jsx`, used in **Workspace.jsx** | Step counter, “thinking”, token bar. **Currently not wired to real build** — it uses local `versions.length` and a fixed “Analyzing…” message. |
| **Preview** | **In Workspace:** Sandpack (CodeSandbox in-browser) for the open project’s files. **After deploy:** `project.live_url` (Vercel/Netlify) and “View Live” on AgentMonitor. | You see the app in the browser inside the Workspace; after deploy you get a real URL. |

So: **our “computer” where things run = backend `workspace/<project_id>/`**. Our “things running” view = **AgentMonitor** (phases, agents, logs, Build state). We do **not** have a separate cloud VM “sandbox” per task like Manus.

---

## 2. Do We Have a Sandbox?

**Not like Manus.**

- **Manus:** Isolated **cloud VM per task** (Docker/Linux): full filesystem, terminal, browser, network. You can “view all files in this task” and watch terminal/browser via VNC-style UI.
- **Us:** One **directory per project** on the backend server: `workspace/<project_id>/`. We run allowlisted commands (pytest, npm test, bandit, etc.) in that directory via `execute_tool(project_id, "run", ...)`. No isolated VM, no live terminal view in the UI, no “view all files in this task” in one place (you get files via Workspace editor or deploy ZIP).

So we have a **workspace**, not a **sandbox** in the Manus sense.

---

## 3. How Do We See Preview?

- **Inside the app (Workspace):** **Sandpack** — the code you have open in the Workspace is run in the browser (CodeSandbox). So you get an in-browser preview of the React app while editing.
- **After build (AgentMonitor):** When deploy runs (Vercel/Netlify), we set `project.live_url` and show a **“View Live”** button. That’s the real deployed preview.
- **During build:** We do **not** yet stream a live “preview of the app as agents write files.” You see progress (phases, agents, Build state), not a live-updating app iframe.

---

## 4. How Do We See “Things Running” (Like Manus)?

- **We have:**  
  - **AgentMonitor** page: phases, which agents are running/done, progress %, tokens, Activity Log, Build state (plan, requirements, stack, tool_log, reports).  
  - **WebSocket** `ws/projects/{id}/progress`: phase, current_agent, status, progress, tokens_used.  
  - **ManusComputer** in the Workspace: a small “computer” widget with step/tokens/“thinking” — but it’s **not** wired to the real orchestration; it uses local mock data.
- **Manus has (we don’t yet):**  
  - **SSE stream** of fine-grained events (e.g. “agent is executing X”, “tool Y was called”).  
  - **Live terminal view** (commands and output in the UI).  
  - **Live browser view** (VNC-style headless browser).  
  - **“View all files in this task”** in the UI.

So we have a **high-level “things running” view** (phases + agents + state); we don’t yet have **per-step event stream** or **live terminal/browser** in the UI.

---

## 5. What We Must Add to Be “Just Like Manus” (and Better)

| Gap | What Manus has | What we should add |
|-----|----------------|--------------------|
| **Sandbox** | Isolated cloud VM per task | Optional: run build in a **Docker container** (or VM) per project so execution is isolated and we can show “this task’s files + env.” |
| **Live “computer” in Workspace** | — | **Wire ManusComputer to real build:** when Workspace has a `projectId` and a build is running, subscribe to `ws/projects/{id}/progress` (and optionally `/projects/{id}/state`), pass real `currentStep` (phase index), `totalSteps` (phases.length), `tokensUsed`/`tokensTotal`, and real “thinking” (e.g. current agent name or last state update). So the “manual slide computer” shows real orchestration. |
| **Preview during build** | — | Optional: **live preview during build** — e.g. when Frontend/Backend agents write files, periodically sync `workspace/<project_id>/` to a small dev server or Sandpack template and show an iframe so the user sees the app updating as agents run. |
| **Event stream** | SSE: plan → execute → observe events | Optional: **SSE or WebSocket event stream** (e.g. “Planner finished”, “File Tool Agent writing src/App.jsx”, “Test Executor running pytest”) so the UI can show a timeline like Manus. |
| **“View files in this task”** | UI to see all files created in the task | Optional: **API + UI** to list `workspace/<project_id>/` (and key files) and open them in the Workspace or download as ZIP (we already have deploy ZIP; this would be “all project files”). |

---

## 6. Summary Table

| Question | Answer |
|----------|--------|
| **Where’s our code?** | Backend `workspace/<project_id>/`; orchestration in `server.py`; tools in `real_agent_runner.py` + `tool_executor.py`. |
| **Do we have a sandbox?** | We have a **workspace** (directory per project). We do **not** have an isolated cloud VM/sandbox like Manus; that would be an add-on (e.g. Docker per run). |
| **How does ours work?** | DAG → phases → agents → state/artifact/tool → state persisted; progress via WebSocket; Build state panel on AgentMonitor. |
| **How do we see preview?** | **Sandpack** in Workspace (in-browser); **View Live** after deploy. No live “preview during build” yet. |
| **Where’s the “slide computer” that shows things running?** | **AgentMonitor** = real “things running” (phases, agents, state). **ManusComputer** in Workspace = same idea but **not yet wired** to real build; we should connect it to WebSocket + state. |
| **Do we need to add that stuff to be better?** | Yes. To match and exceed Manus on “see it like Manus”: wire **ManusComputer to real progress**, then optionally add **sandbox (Docker)**, **live preview during build**, **event stream (SSE)**, and **“view all files in this task.”** |

---

## 7. Next Step (Concrete)

**Immediate win:** Wire **ManusComputer** in the Workspace to **real** build progress when the user is in a project that has a build running (or recently ran): use `projectId` from route/context, subscribe to `ws/projects/{projectId}/progress`, and optionally fetch `GET /projects/{projectId}/state` for “thinking” text. Pass real phase index, phase count, tokens, and current agent name into ManusComputer so the “manual slide computer” shows the real subcursive computer (orchestration) running — just like the idea of Manus, with our 120 agents.

I can implement that wiring next (Workspace gets projectId, subscribes to progress WS, feeds ManusComputer with real data).
