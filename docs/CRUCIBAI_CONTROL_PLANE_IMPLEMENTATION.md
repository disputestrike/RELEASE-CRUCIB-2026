# CrucibAI control plane — engineering implementation program

**Authority:** Derives scope from `docs/CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md` (Parts B2, B3, C–E).  
**Constraint:** No broad rewrites of **landing**, **dashboard**, or **workspace layout** — only **spine** integrations (job, stream, tasks, preview data path, activity feed).

---

## 1. Wave / phase map (Part E → delivery)

| Phase | Code name | Part E item | Intent | Status |
|------|------------|-------------|--------|--------|
| **0** | `BASELINE` | — | Audit + this document; frozen-surface rule | **Done** |
| **1** | `TASK-JOB-SPINE` | E1 | Single run identity: `jobId` in URL + task store as soon as plan returns; new runs without `taskId` get a task row + `?taskId=` | **Done** (this train) |
| **2** | `ACTIVITY-FEED` | E2 | Event surface beyond `brain_guidance`: activity feed visible during **run**, mapped event types, live strip | **Done** (this train) |
| **3** | `PREVIEW-DATA` | E3 | Ensure `PreviewPanel` receives `jobId` / `token` / `apiBase` so `dev-preview` + preview WS can run | **Done** (this train) |
| **4** | `WORKSPACE-PULL` | E4 | `workspacePullKey` on `dag_node_completed` (existing) **+** `step_started` / `file_write*` / `workspace_files_updated` (shipped) | **Done** (frontend) **+** verify orchestrator writes on host |
| **5** | `FAILURE-UX` | E5 | `useJobStream`: immediate `GET /jobs/:id` on SSE **`job_failed`**; workspace failure callout + one refresh; pane refresh (existing) | **Done** (frontend) **+** operator E2E |
| **6** | `SERVER-CHAT-LOG` | E6 | `POST /api/jobs/{id}/transcript` persists user lines as `workspace_transcript` events; workspace rehydrates from `GET /events` before `brain_guidance` mapping | **Done** |
| **7** | `HONESTY-DUAL-CHANNEL` | B3 / scorecard A8–A10 | `GET /api/settings/capabilities` exposes `connectors_configured` + in-process `mcp` list; Home chat copy + `UnifiedWorkspace` build subtitle label channels; **Engine room** shows integration + workspace routes | **Done** |
| **8** | `TRACE-AND-TASK-SIGNALS` | B3 #2, #3 / C1, C6 | Activity feed `formatEvent` covers preflight, spec guardian, `file_written`, verify/retry, richer `job_failed`; sidebar **no run** hint when local task has no `jobId` | **Done** |

---

## 2. Compliance tracker (audit finding → control)

| ID | Finding (B3 / C) | Control implemented | Evidence |
|----|------------------|---------------------|----------|
| C-E1 | Task without `jobId` → no stream | Plan path: `updateTask` / `addTask` + URL | `UnifiedWorkspace.jsx` `runNewPlanAndAuto` |
| C-E2 | Only `brain_guidance` in chat | Activity feed + `formatEvent` (incl. preflight, spec, files, verify, **Phase 8**) | `WorkspaceActivityFeed.jsx` |
| C-E3 | Activity hidden during run | Feed was `stage === 'input'` only | Condition `stage === 'input' \|\| effectiveJobId` |
| C-E4 | Preview URL not loading | `dev-preview` never called without `jobId` on panel | `PreviewPanel` props from `UnifiedWorkspace` |
| C-E5 | Dual brain (Dashboard `/ai/chat` vs job) | **Advisory** note (explicit: not system of record) + `job_id` nudge; **build** line in Workspace when a job is active | `Dashboard.jsx` + `Dashboard.css`; `UnifiedWorkspace.jsx` + `unified-workspace-tokens.css` |
| C-E6 | No server chat log per job | User + **steer coach** → `workspace_transcript`; rehydrate user+transcript assistant from `GET /events`; build brain from `brain_guidance` (existing) | `jobs.py` `POST .../transcript`, `UnifiedWorkspace.jsx`, `WorkspaceActivityFeed.jsx` |

---

## 3. Crosswalk — reference rubric (B2) vs our implementation

| Reference | Rubric row | CrucibAI response (this program) |
|-----------|------------|----------------------------------|
| **Codex** | One run drives UI | `jobId` + `taskId` in URL after plan; sidebar `openTask` preserves `jobId` (existing) |
| **Codex** | Transcript of work | Center: `brain_guidance` → chat (existing); **Plus** activity: step + DAG + brain line in feed + live strip |
| **Cursor** | Grounded file tree | Unchanged topology; **Sync** + file pull unchanged |
| **Claude Code** | One CWD mental model | Single `effectiveJobId`; job switch reset preserved |
| **Goose** | Honest connectors | Capabilities + Engine room (Phase 7) |
| **Manus (checklist)** | DAG + recovery visible | Activity feed + timeline details; failure panes unchanged |
| **Manus / Codex** | Durable run transcript | User turns durable via job events; assistant from orchestrator events |

---

## 4. Checklist (release gate)

**Repo / local (complete in source tree)**

- [x] Plan returns `job_id` → URL contains `jobId` (existing; preserved).
- [x] Task store row has `jobId` after plan when user had `taskId` or new task created when no `taskId`.
- [x] `WorkspaceActivityFeed` renders when `effectiveJobId` (not only idle input).
- [x] `formatEvent` covers `dag_node_*`, `brain_guidance` (short), steering, job lifecycle.
- [x] Live strip shows for non-terminal jobs when events exist.
- [x] `PreviewPanel` receives `jobId`, `token`, `apiBase`.
- [x] E6: user workspace lines POST to `/api/jobs/{id}/transcript` and rehydrate from `/events` when present.
- [x] Automated pytest: `scripts/verify_control_plane_local.ps1` (Windows) or `scripts/verify_control_plane_local.sh` (Unix) — runs transcript + capabilities tests.

**Post-deploy on Railway (operator — you)**

- [ ] **Gate A (success):** `GET /api/jobs/{id}` and `GET /api/jobs/{id}/dev-preview` behave as documented in `CRUCIBAI_RAILWAY_OPERATOR_RUNBOOK.md` §2.
- [ ] **Gate B (failure):** For a **failed** job id, `GET /api/jobs/{id}` + `/events` still expose failure narrative; UI refresh on `/app/workspace?jobId=...` shows failure UX — `CRUCIBAI_RAILWAY_OPERATOR_RUNBOOK.md` §3.

---

## 5. Corrective actions log (file touch list, this train)

| File | Change |
|------|--------|
| `frontend/src/pages/UnifiedWorkspace.jsx` | Task/job URL sync after plan; show activity feed for active job; pass preview auth props |
| `frontend/src/components/AutoRunner/WorkspaceActivityFeed.jsx` | Richer `formatEvent` (incl. `workspace_transcript`); live strip; larger event buffer |
| `frontend/src/components/AutoRunner/WorkspaceActivityFeed.css` | Styles for live strip |
| `frontend/src/hooks/useJobStream.js` | `job_failed` → same job row fetch as completed (latestFailure) |
| `frontend/src/pages/AutoRunnerPage.css` | Failure callout in composer |
| `frontend/src/pages/Dashboard.jsx` + `Dashboard.css` | Advisory channel hint (C-E5) |
| `backend/routes/jobs.py` | `POST /{job_id}/transcript` → `workspace_transcript` job event |
| `frontend/src/pages/UnifiedWorkspace.jsx` (E6) | `persistTranscriptLine(user|assistant)`, `jobTranscriptLinesFromEvents`, rehydration; steer coach → transcript |
| `backend/tests/test_control_plane_transcript.py` | Pytest: `workspace_transcript` user+assistant on job events |
| `backend/routes/projects.py` | `get_capabilities` — `connectors_configured`, `mcp` payload |
| `backend/tests/test_projects_capabilities_endpoint.py` | ASGI: capabilities JSON shape |
| `frontend/src/pages/Settings.jsx` (Engine room) | Fetch `/api/settings/capabilities`; integration + workspace surface cards |
| `frontend/src/pages/UnifiedWorkspace.jsx` + `unified-workspace-tokens.css` | Job-active subtitle: authoritative channel |
| `frontend/src/pages/Dashboard.jsx` + `Dashboard.css` | Stronger dual-channel (C-E5) copy |
| `frontend/src/components/AutoRunner/WorkspaceActivityFeed.jsx` | Phase 8: more `formatEvent` types from orchestrator |
| `frontend/src/components/Sidebar.jsx` + `Sidebar.css` | Phase 8: `no run` hint when task lacks `jobId` |

---

## 6. Proof

- **Build:** `cd frontend && npm run build` must pass.
- **Manual:** Start build from `/app/workspace` without prior `taskId` → URL gains `taskId` + `jobId`; sidebar entry links back with both.
- **Manual:** During `running`, “Behind the scenes” shows live strip with step/DAG lines without opening “Timeline & steps”.
- **Manual (E6):** Send a user message with a job active → refresh page → user line returns from events; steer once → refresh → user + coach reply lines (orchestrator `brain_guidance` still appears as before).

---

**Program status:** Phases **0–8** implemented; **local/repo verification** is complete (§4, scripts). **Post-deploy** checks are only the two gates in §4 (operator runbook).

---

## 7. Local verification (engineer, before you push)

**One command (from repo root `RELEASE-CRUCIB-2026/`):**

- Windows: `.\scripts\verify_control_plane_local.ps1`
- macOS/Linux: `bash scripts/verify_control_plane_local.sh`

This runs: `test_control_plane_transcript.py` + `test_projects_capabilities_endpoint.py` (same as CI-friendly subset for the control plane).

**Frontend:** `cd frontend && npm run build` must pass (§6).

---

## 8. Post-deploy verification (E6 transcript + optional UI)

After deploy, smoke the API with a real JWT and `JOB_ID` (browser devtools → `token` or Network `Authorization` header).

1. **Append transcript (user):** `POST /api/jobs/{JOB_ID}/transcript` with body `{"role":"user","body":"test line"}` and `Authorization: Bearer <token>`.
2. **Read back:** `GET /api/jobs/{JOB_ID}/events` — at least one event has `event_type` `workspace_transcript` and payload with `text`.
3. **UI:** open `/app/workspace?jobId=...` after step 1 — after refresh, the user line appears in the center column (rehydration).

**Full Railway gates (preview + failure):** use **`docs/CRUCIBAI_RAILWAY_OPERATOR_RUNBOOK.md`** copy-paste flows so you can close §4 without guessing URLs or fields.
