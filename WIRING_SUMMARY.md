# Wiring Summary: One Unit, Everything Connected

All four "match and exceed Manus" items are implemented and wired into the same flow. Nothing is isolated.

---

## 1. SSE event stream (Manus-style timeline)

- **Backend:** `emit_build_event(project_id, type, **kwargs)` is called from orchestration:
  - `build_started`, `phase_started`, `agent_started`, `agent_completed`, `build_completed`.
- **Storage:** In-memory `_build_events[project_id]` (max 500 events).
- **Endpoints:**
  - `GET /api/projects/{id}/events?last_id=0` — SSE stream (real-time).
  - `GET /api/projects/{id}/events/snapshot` — one-shot list for UI.
- **Frontend:** AgentMonitor fetches `events/snapshot` with the rest of the project data and shows an **Event timeline** panel (agent started/completed, phase, build done).

**Wired to:** Same orchestration loop that runs the 120 agents; every phase and agent run emits an event.

---

## 2. ManusComputer wired to real build

- **Workspace** reads `?projectId=` from the URL (from AgentMonitor **Open in Workspace**).
- When `projectId` is present, Workspace opens **WebSocket** `ws/projects/{projectId}/progress` and receives phase, agent, progress, tokens_used.
- **ManusComputer** receives:
  - `currentStep` = phase + 1, `totalSteps` = 12
  - `thinking` = current agent name
  - `tokensUsed` / `tokensTotal` from WebSocket
  - `isActive` = build running or progress in (0, 100).
- When `projectId` is not in the URL, ManusComputer still uses local build state (versions, isBuilding) so the widget works in both contexts.

**Wired to:** Same WebSocket used by BuildProgress on AgentMonitor; same project and orchestration.

---

## 3. Live preview (workspace files in iframe)

- **Backend:**
  - `GET /api/projects/{id}/preview-token` (auth) → returns short-lived JWT and full preview URL.
  - `GET /api/projects/{id}/preview?preview_token=...` (no Bearer) → serves files from `workspace/<project_id>/` (path-safe). Directory → index.html or "Building..." placeholder.
  - `GET /api/projects/{id}/workspace/files` (auth) → list of workspace file paths.
- **Frontend:** AgentMonitor fetches `preview-token`, then shows an **iframe** with `src={url}` so the browser loads the preview with the token. Build state panel can show **Files in workspace** from `workspace/files`.

**Wired to:** Same workspace directory that agents write to; same project and auth.

---

## 4. Sandbox (optional Docker run)

- **Backend:** `tool_executor.execute_tool(..., "run", ...)`.
  - If `RUN_IN_SANDBOX=1`: runs the allowlisted command inside a **Docker** container: `docker run --rm -v workspace:/.app -w /.app <image> <cmd>`. Image = `python:3.11-slim` or `node:20-slim` from command. Falls back to local run if Docker is missing.
  - If not set: same as before (local run in workspace dir).
- **Wired to:** Same `execute_tool` used by agent_real_behavior for Test Executor, Security Checker, Code Review, Bundle Analyzer, Lighthouse, Dependency Audit; same workspace path.

---

## 5. Cross-links (no isolated screens)

- **AgentMonitor** has **Open in Workspace** → `Link to=/app/workspace?projectId={id}`. Opens Workspace with that project so ManusComputer shows real progress.
- **Workspace** with `?projectId=` subscribes to that project’s WebSocket and drives ManusComputer from it.
- **Event timeline** and **Build state** and **Live preview** and **Activity Log** all use the same project id and the same backend (state, events, workspace, progress).

---

## Flow (one unit)

1. User starts a build (dashboard or builder) → orchestration runs in `server.py`.
2. Every phase/agent: we emit `build_events`, update DB (current_phase, agent, progress), and run real behavior (state/artifact/tool).
3. AgentMonitor (and Workspace when opened with projectId) receives:
   - **WebSocket** progress (phase, agent, tokens).
   - **Polled** state, events snapshot, workspace files, preview token.
4. UI shows: **Event timeline**, **Build state**, **Live preview** iframe, **Open in Workspace**, **ManusComputer** (real data when in Workspace with projectId).
5. Optional: set `RUN_IN_SANDBOX=1` so run-tool steps execute in Docker.

Everything uses the same project id, same workspace path, same orchestration, and same APIs. No isolated paths.
