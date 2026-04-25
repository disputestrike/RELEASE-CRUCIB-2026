# CrucibAI control plane: honest state audit and roadmap (2026)

**Purpose:** Single source of truth for *where the product is today* vs *the Codex-level upgrade directive* and vs *the research frames* (job lifecycle, proof, streams, no fake UI). This is a **code-grounded** inventory, not a competitor slide deck. Update this file as wiring lands.

**Scope:** `RELEASE-CRUCIB-2026` (frontend + backend as shipped in repo). **Production URL** and **local** may differ by env/config only.

**How to read status labels**

| Status | Meaning |
|--------|--------|
| **REAL** | Backed by API + persisted or streamed data in normal paths |
| **PARTIAL** | Some paths real; others stub, feature-flag, or client-only |
| **LOCAL** | True in dev / zustand / session only |
| **PLACEHOLDER** | UI or copy implies live system data; implementation is static or hardcoded |
| **UNKNOWN** | Not fully traced in this pass; needs file-level follow-up |

---

## 1. Executive summary (honest)

CrucibAI is **not** an empty shell: the backend exposes **real job**, **stream**, **workspace file**, **preview serve**, **proof** (in tests and routes), and **orchestrator**-adjacent surfaces. The frontend has a **large** `Dashboard` and **`UnifiedWorkspace`** with intent routing, **SSE-style** job consumption patterns, and **task store** integration.

Gaps to close for a **“no fake control plane”** bar are **mostly wiring and honesty**, not a greenfield server:

- **Dashboard → canonical job** — Home flow centers on `/ai/chat`, `/agents/from-description`, **navigation to** `/app/workspace` with handoff state; a strict **`POST /api/jobs` first** product narrative (per directive) may still need **unifying** with existing chat/orchestrator flows so one **job_id** is the spine end-to-end.
- **One workspace** — `App.js` routes **`/app/workspace` → `UnifiedWorkspace`** (plus legacy `Workspace`, `WorkspaceManus`). **Duplicate entry points** remain by design for migration; the roadmap should **converge** on one surface for “live work” *without* breaking bookmarks.
- **Static vs live panels** — Any card showing numbers or “activity” must be **tied to API** or **replaced** with empty/loading/error (directive Class 7).

This audit maps **eight upgrade classes** to evidence and next actions.

---

## 2. Architecture snapshot (as wired in repo)

### 2.1 Frontend entry and routes (from `App.js`)

- **`/app` (index) → `Dashboard`** — main “What do you want to build?” experience.
- **`/app/workspace` → `UnifiedWorkspace`** — primary build/workspace shell.
- **`/app/workspace-classic` → `Workspace`** — legacy.
- **`/app/workspace-manus` → `WorkspaceManus`** — variant.
- **`/app/what-if` → `WhatIfPage`** — What-If (calls **`/runtime/what-if`** from `WhatIfPage.jsx`).
- Large surface area: **agents, skills, knowledge, admin,** etc.

**Implication:** “Single workspace” is a **product** decision: consolidate **navigation and job context** so users do not hit divergent runtimes for the same intent.

### 2.2 Backend integration (from `route_integration.py` and `server.py` patterns)

Routers include **jobs** under `/api`, **projects**, **agents**, **monitoring**, and many modules via **`modules_blueprint` / `router_loader`**. **Jobs** and **orchestrator**-related code exist (`routes/jobs.py`, `routes/orchestrator.py`, `services/job_runtime_service.py`, `routes/preview_serve.py`).

**Implication:** Prefer **extending** existing `job_id` + **stream** + **artifacts** paths before creating parallel “fake” job APIs.

---

## 3. Class-by-class matrix (directive ↔ repo reality)

### Class 1 — Dashboard entry and “real job”

| Requirement (directive) | Status | Notes / pointers |
|-------------------------|--------|------------------|
| Prompt creates **`POST /api/jobs`** | **PARTIAL / UNKNOWN** | `Dashboard.jsx` uses **`/ai/chat`**, **`/agents/from-description`**, **`/projects`**, etc. **Direct** `POST /api/jobs` from the home prompt must be **traced** per submit path. |
| **`job_id` returned, route to workspace** | **PARTIAL** | Navigation to `/app/workspace` with **state / query** and **useTaskStore**; align with **server job id** when build path creates one. |
| Recent jobs from **backend** | **PARTIAL** | Sidebar / history: **local tasks** and **API-backed** project rows — verify each bucket’s source. |
| No fake project cards | **PARTIAL** | `HomeLeftPane` / dashboard cards: audit **“No X yet”** vs **static demo** in **Dashboard**. |
| No duplicate entry | **PARTIAL** | **Multiple** workspace routes; document **which is canonical** for new users. |

**Next steps:** Trace **`submit` / `handleSend` / build branch** in `Dashboard.jsx` and the **`UnifiedWorkspace`** handoff (see `withWorkspaceHandoffNonce`, `sessionStorage` autostart). Map to **`POST /api/jobs`** or document why **`/ai/chat` remains** the source of truth for “chat-first” and how **job rows** are created in DB.

### Class 2 — Live orchestration workspace

| Requirement | Status | Notes |
|-------------|--------|--------|
| Job status, events, stream | **PARTIAL** | `job_runtime_service` stream URLs; **Workspace / UnifiedWorkspace** use hooks and polling — confirm **one** subscription model per `job_id`. |
| Switching job id clears stale | **PARTIAL** | `taskId` in URL; verify **zustand + effects** reset panels. |
| Rehydrate completed | **PARTIAL** | `GET /api/jobs/{id}` patterns in tests; ensure UI uses same. |

**Code cues:** `workspaceLiveUi.js` (“**no fake data**” comment), `Workspace.jsx` (large; event panels).

### Class 3 — Preview, files, artifacts

| Requirement | Status | Notes |
|-------------|--------|--------|
| Artifacts list + preview | **PARTIAL** | `preview_serve.py`: `/api/preview/{job_id}/serve/...`, `/api/jobs/{id}/dev-preview`. **Wire** `UnifiedWorkspace` preview panel to these when job has output. |
| Honest error | **UNKNOWN** | Each panel needs **error boundary** and **empty** when no artifacts. |

### Class 4 — What-If, proof, runtime inspect (wedge)

| Surface | Status | Notes |
|---------|--------|--------|
| What-If | **REAL (path exists)** | `WhatIfPage.jsx` → **`/runtime/what-if`**; fix JSX regression already shipped. |
| Runtime inspect | **PARTIAL** | Internal/admin-style routes; ensure **one** “inspect this job” surface for product tier. |
| Proof bundle | **PARTIAL** | **Golden path** tests hit **`/api/jobs/{id}/proof`**. Expose in UI as **structured** evidence, not a paragraph. |

### Class 5 — Work automation (future)

| Requirement | Status |
|-------------|--------|
| Capability registry, no fake connectors | **PARTIAL** — search **`SkillsPage` / channels** for “coming soon” vs “live” labels. |

### Class 6 — Builder vs developer modes

| Requirement | Status | Notes |
|-------------|--------|--------|
| Same job data, different presentation | **PARTIAL** | `user.workspace_mode` and **`workspace_mode`** in tests reference **developer vs simple**; **`UnifiedWorkspace`** should not fork **state**, only **views**. |

### Class 7 — Remove placeholders and “static lies”

**Method:** Rerun targeted search in **`frontend/src/pages`** and **`components`** (exclude `__tests__`, `setupTests.js`):

```text
mock|MOCK|placeholder|hardcoded|dummy|fake|sample|static
```

**Principle:** **Input** `placeholder` on `<input />` is fine; **“placeholder panel”** without data is not.

**Initial grep note:** Jest and story mocks are **test-only**; production risk is in **pages** that synthesize success without API.

| Area | Action |
|------|--------|
| Trust / activity / metrics cards | Each needs **source** (API) or **empty** copy |
| “Live” / “Active” | Must reflect **stream or poll**, not time-of-mount |

### Class 8 — Tests and proof of completion

| Asset | Status |
|-------|--------|
| `backend/tests/test_golden_path.py` | Exercises **jobs**, **steps**, **workspace file**, **proof** |
| `test_golden_path_local.py` | **POST /api/jobs** acceptance |
| `frontend` `craco build` | **Required** on every release |

**Next:** **Single script** in repo root or `scripts/` that: **backend import**, **pytest subset**, **npm run build** (documented in CI).

---

## 4. Research alignment (shorthand)

| Research theme | CrucibAI expression in product |
|----------------|---------------------------------|
| **Intent → job** | Dashboard + workspace handoff; tighten **one job id** story |
| **Proof > narrative** | Proof API exists — **UI must show** structured evidence |
| **Streams > static dashboards** | **SSE / poll** to panels; no fake “green” |
| **No assistant as system of record** | **DB + job row + artifacts** are truth; chat is not |

---

## 5. Suggested commit train (matches your directive)

1. **DASHBOARD** — Map prompt flow → **job create** (or document dual path) + recent list from **API**  
2. **WORKSPACE** — Single stream/rehydration path per `job_id`  
3. **PREVIEW** — Artifacts + iframe + preview routes  
4. **PROOF** — What-If (done path) + runtime inspect + **proof** panel from API  
5. **MODES** — Builder/ developer presentation only  
6. **CLEANUP** — Remove or hide false panels (Class 7 list)  
7. **VALIDATION** — `scripts/validate.sh` (or `npm run verify`)  

---

## 6. Stability score (subjective, for this pass)

| Dimension | Score /100 | Rationale |
|-----------|------------|-----------|
| Backend surface area | **78** | Jobs, stream, files, proof, preview exist |
| Frontend honesty | **58** | Rich UI; need systematic **anti-fake** pass |
| Single-job spine | **55** | Multiple routes and handoff paths |
| Test/CI story | **65** | Golden paths exist; need **one** local command bundle |

**Overall (rough): 62/100** — strong bones; **wiring + honesty** to reach “control plane” bar.

---

## 7. Immediate UI fix (this session) — sidebar account menu (collapsed)

**Issue:** **`.sidebar`** uses **`overflow: hidden`**. The **account dropdown** in the **collapsed** strip was **position: absolute** inside the rail — **clipped** and **misread** as “stuck in nav.”

**Fix:** **Portal** the collapsed account menu to **`document.body`**, **`position: fixed`**, placed **to the right** of the avatar (with **resize/scroll** listeners). **Outside-click** and **Escape** include the **portaled** node. (Same class of fix as **delete** confirmation **portal**.)

**Files:** `frontend/src/components/Sidebar.jsx`, `Sidebar.css`

---

## 8. Remaining blockers (rolling list)

- [ ] **Trace** `Dashboard` primary submit → **server job id** for build path (vs chat-only)  
- [ ] **Converge** workspace routes or **document** primary URL for marketing + product  
- [ ] **Class 7** file-by-file placeholder audit with **tickets** per panel  
- [ ] **E2E** or smoke: “prompt → job row → workspace stream → proof” on **staging**  

---

*This document is the first pass of the approved “unraveling + roadmap.” Expand sections with file paths and screenshots as you close each class.*
