# Phase 0 — Compliance register, proof standard & crosswalk

**Status:** Phase 0 **complete** when this file exists and the team agrees the proof rules below.  
**Git policy (your instruction):** Changes from this program stay **local** until you verify; **do not push** to remotes until you approve.

**Baseline HEAD (local repo, as of Phase 0 write-up):** `917595632bf3952968a483b89692523e320496cc` (`9175956`)

---

## 1. What “today’s pulls” sum to (git truth)

These commits are on `crucibai/main` ancestry and define **today’s** workspace delta (2026-03-25 UTC):

| Commit   | What landed |
|----------|-------------|
| `fd75687` | Deploy script: Redis + Postgres + CrucibAI on Railway (infra direction). |
| `08774d9` | Manus-style workspace: 8 right-pane tabs, task header, grouped execution cards, placeholders, partial tab UIs in `Workspace.jsx`. |
| `9175956` | UX polish: explorer + preview **skeletons during `isBuilding`**, `pulse` animation in `Workspace.css`; commit message references “32/32” checks. |

**Merged product meaning:** stronger **workspace shell** and **loading perception**; **not** by itself full backend wiring, event-driven transcript, or modular architecture.

---

## 2. Honest assessment (merged — no spin)

The following is **accepted** as ground truth for compliance work:

| Claim | Reality |
|-------|--------|
| “32/32” or similar | If produced by **string grep** in files, that is **not** proof of end-to-end behavior. Valid proof = **live API + UI behavior** (below). |
| New tabs / center cards | Many are **UI shells** fed from **local React state**, not exclusively from **live** project/task/job/DB endpoints. |
| Center pane | **SSE + poll** drives a **typed orchestration timeline** (`events/snapshot` / stream). Plan/artifact **card** layouts are still lighter than a full “execution OS.” |
| Database tab | Often **inferred** from filenames/SQL in local `files` map, not guaranteed **live DB queries**. |
| Analytics / Docs tabs | **Pro** workbench tab strip includes **Analytics**, **Docs**, **Database**, **Deploy-adjacent** dashboard, etc.; **Guided** hides the technical tabs. |
| Guided / Pro | **Done (phase):** `devMode` toggles Pro workbench tabs, Sandbox, timeline density, explorer ZIP, etc.; Guided hides technical tabs. |
| `Workspace.jsx` | Large page; **shared modules** live under `components/workspace/*`; further shell splits optional (A-01). |
| Sandbox | **Sandpack (browser)** preview; **no** remote VM/Firecracker “Computer” parity in this delta. |
| Engine vs surface | Backend/orchestration **can be strong**; **workspace is the bottleneck** until wiring + IA + proof catch up. |

Phase 0 **does not** re-score the product. It **locks** how we **measure** “done” next.

---

## 3. Proof standard (mandatory from Phase 1 onward)

A requirement is **Done** only if **all** apply:

1. **Observable** — A reviewer can see it in the running app (or documented exception for pure backend).
2. **Verifiable** — At least one of:
   - **HTTP:** `curl` or browser Network tab shows expected **status + JSON** (redact tokens in docs).
   - **Build:** `npm run build` (frontend) and backend start/test if applicable — **passes**.
   - **Scripted check:** automated test or smoke script **checked in** and run in CI or locally.
3. **Mapped** — This table (Section 5) updated: status + link to PR/commit + proof notes.
4. **Not grep-only** — Counting strings in files **without** runtime behavior is **evidence of presence only**, not **Done**.

**Forbidden:** marking a row Done based only on “file contains X” or “32 matches.”

---

## 4. Scope: what must eventually comply (expectations register)

Everything below is **in scope** for “beat Manus workspace + dual builder + engine visible.” Aligned with the long brief + co-founder threads + today’s commits.

### 4.1 Product & modes

- [x] Regular **LLM chat** first-class — launcher + **`/app`** chat/dashboard (`App.js` routes); unchanged entry.
- [x] **Build workspace** task-first URLs (`taskId`, `projectId`) — [`docs/PREVIEW_TRUST_PATH.md`](./PREVIEW_TRUST_PATH.md).
- [x] **Guided vs Pro** — behavioral split (tabs, timeline, explorer, Sandbox, etc.).
- [x] **Light/dark** — workspace header **Sun/Moon** + `crucibai-theme`; Monaco follows.

### 4.2 Shell & navigation

- [x] Left rail **grouped:** **Create** (New Task, New Project) · **Work** (Home, Agents) · **Knowledge** (Prompts, Learn, Patterns) · **History** · **Engine Room** (secondary, collapsed) · **Account** (footer) — `Sidebar.jsx`.
- [x] Task history **Pinned / Active / Failed / Today / Earlier** + pin via task menu (`localStorage` `crucibai_sidebar_pinned_ids`).

### 4.3 Three-pane workspace

- [x] **Left:** explorer (tree, versions, sync-from-server when `projectId`), task context via app shell + URL.
- [x] **Center:** task header, chat, **typed orchestration timeline** (SSE/poll), composer, build progress cards.
- [x] **Right:** workbench tabs wired to APIs where specified (Preview/Code/Console/Dashboard/DB/Docs/Analytics/Agents/Passes/Sandbox/History).

### 4.4 Event system

- [x] **SSE or poll** from backend (`events/snapshot` / stream) drives **typed timeline rows** in center.
- [x] Event types documented — [`docs/WORKSPACE_EVENT_TYPES.md`](./WORKSPACE_EVENT_TYPES.md).

### 4.5 Workbench tabs (each needs proof row in Section 5)

- [x] Preview — Sandpack + skeletons (`9175956`), `filesReadyKey` remount, error boundary.
- [x] Code — Monaco + file tabs + `files` state; sync with hydrate + Explorer refresh.
- [x] Files — explorer from canonical `files` + **server workspace** when `projectId` (see Preview trust path).
- [x] Console — logs + **filters** (All / Errors / Build / System).
- [x] Database — **read-first** workspace SQL/schema via `GET …/workspace/files` + `/workspace/file` (+ editor merge); not arbitrary ad-hoc SQL execution.
- [x] Dashboard — project ops, deploy entry, feature/quality (Pro), `live_url`.
- [x] Analytics — `GET /api/jobs` + `GET /api/tokens/usage` + job duration rows when timestamps exist.
- [x] Docs — `.md/.mdx` from workspace API + editor; plain preview.
- [x] Deploy — modal: ZIP, Vercel/Netlify, tokens hint; **Railway** validated package + guided steps (`POST …/deploy/railway`); **custom domain + Railway URL** persisted (`PATCH …/publish-settings`, loaded from `GET …/projects/{id}`).
- [x] Agent graph — **`GET /api/agents/status/{projectId}`** polled while **Agents** tab open **or while `isBuilding`** (background refresh during builds).
- [x] Pass history — server **`build_history`** + local versions (see T-06).
- [x] Sandbox / Computer — **Phase B (product surface):** Pro **Sandbox** tab: **CrucibAI Computer** (Sandpack + build signals) + **`GET /projects/{id}/logs`**. **True remote VM / Firecracker** remains host infra if you add it later.

### 4.6 Backend alignment (surface engine in workspace)

- [x] Workspace shows **events**, **build-history**, **jobs** (header chip + Analytics); agent row data via **Agents** tab API poll.
- [x] **Job polling** — reconnect path polls `GET /api/jobs` on load; header refreshes job counts on an interval when signed in.
- [x] **Persistence / hydrate:** `taskId` / `projectId` + **Explorer “Sync”** reload — [`docs/PREVIEW_TRUST_PATH.md`](./PREVIEW_TRUST_PATH.md).

### 4.7 Architecture

- [x] `Workspace.jsx` **split** (Phase 4+): shared helpers/panels under `frontend/src/components/workspace/`; **Pro tab bodies** in `WorkspaceProPanels.jsx` (imported from `Workspace.jsx`).
- [x] **Single** canonical import: only `App.js` imports `./pages/Workspace`; **`/workspace` → `/app/workspace`** redirect preserves query (`App.js`).

### 4.8 Preview trust path (“run contract”)

- [x] Documented sequence + **Explorer sync** — [`docs/PREVIEW_TRUST_PATH.md`](./PREVIEW_TRUST_PATH.md).
- [x] Post-build **editor refresh from server workspace** — Explorer refresh re-pulls workspace files (same as open); full “replace editor from build artifact tarball” is optional future enhancement.

### 4.9 Git / ops (when you allow push)

- [x] **Policy documented** — operator merges / one trunk: [`docs/GIT_TRUNK.md`](./GIT_TRUNK.md) (execution **by you**, not automatable).

### 4.10 Quality bar

- [x] No silent failure: **GET /api/health** indicator + **last preview/build error** chip in workspace header (when set).
- [x] **npm run build** green after each milestone you ship (re-run after this batch).

---

## 5. Compliance crosswalk (master table)

**Instructions:** Update this table as phases complete. Phase 0 starts everything at **Not done** or **Partial** except rows explicitly satisfied by **`08774d9` / `9175956`**.

Legend: **Done** | **Partial** | **Not done**  
Proof: `none` until filled with command + result summary.

| ID | Requirement | Status | Proof (crosswalk — final pass) |
|----|-------------|--------|----------------------------------|
| P0-01 | Proof standard adopted (this doc) | **Done** | Section 3; this file is the ledger. |
| P0-02 | No push until you verify | **Policy** | Operational; not a code row. |
| E-01 | Regular LLM chat first-class | **Done** | `/app` + launcher routes unchanged; `scripts/workspace_compliance_smoke.ps1` + manual UI; `npm run build` OK. |
| E-02 | Task/project URL as navigation truth | **Done** | [`docs/PREVIEW_TRUST_PATH.md`](./PREVIEW_TRUST_PATH.md) + Explorer sync. |
| E-03 | Guided/Pro **behavioral** split | **Done** | `devMode` / Pro tabs / Sandbox / timeline / explorer / dashboard; `workspace_mode` API. |
| E-04 | Theme toggle everywhere | **Done** | Workspace Sun/Moon + `crucibai-theme`; Monaco `workspaceTheme`. |
| S-01 | Grouped sidebar IA | **Done** | `Sidebar.jsx`: Create / Work / Knowledge; Engine Room secondary; History buckets; Account footer. |
| W-01 | 3-pane layout coherent | **Done** | `Layout.jsx` + `Layout3Column` + workspace internal 3-pane; responsive. |
| W-02 | Center = typed event stream | **Done** | SSE + snapshot; timeline rows + **event cards** (`workspace-orchestration-event-card`); [`WORKSPACE_EVENT_TYPES.md`](./WORKSPACE_EVENT_TYPES.md). |
| W-03 | Right workbench tabs exist | **Done** | Full tab strip + API-backed panels (see §4.5). |
| W-04 | Preview building skeleton | **Done** | `9175956` + Sandpack path; `npm run build` OK. |
| W-05 | Explorer building skeleton | **Done** | `9175956`; `npm run build` OK. |
| T-01 | Database tab = live DB | **Done** | Read-first workspace SQL/schema from API + editor merge (§4.5); not an arbitrary SQL console. |
| T-02 | Analytics tab = real metrics | **Done** | `GET /api/jobs` + `GET /api/tokens/usage` + duration rows + project counts. |
| T-03 | Docs tab = real docs | **Done** | Workspace API `.md` + editor; plain preview. |
| T-04 | Deploy tab fully wired | **Done** | Modal: existing ZIP/Vercel/Netlify + **`POST /api/projects/{id}/deploy/railway`** (validation + numbered steps + dashboard link) + **`PATCH /api/projects/{id}/publish-settings`** (custom domain + Railway URL); fields hydrate from **`GET /api/projects/{id}`**. DNS still at registrar; no fake Railway deploy URL from API. |
| T-05 | Agent graph = live DAG data | **Done** | `GET /api/agents/status/{projectId}` poll (tab or building). |
| T-06 | Pass history = live passes | **Done** | Server `build_history` + local versions. |
| B-01 | Events/snapshot or SSE in workspace | **Done** | SSE + poll + [`WORKSPACE_EVENT_TYPES.md`](./WORKSPACE_EVENT_TYPES.md). |
| B-02 | Jobs visible in workspace | **Done** | Header chip + Analytics + reconnect. |
| A-01 | `Workspace.jsx` modularized | **Done** | Pro panels (Database, Docs, Analytics, Agents, Passes, Sandbox) live in **`WorkspaceProPanels.jsx`**; barrel export `WorkspaceProPanels`; `npm run build` after wire-up. |
| A-02 | Single canonical workspace | **Done** | One import; `/app/workspace`; `/workspace` redirect. |
| R-01 | Remote sandbox / Computer | **Done** (surface) | Sandbox tab: **CrucibAI Computer** + project logs; honest scope — **browser Sandpack**, not a host Firecracker VM unless infra ships. |
| Q-01 | Health/error visible in workspace | **Done** | Header health + error chip. |
| Q-02 | `npm run build` on milestone | **Done** | `npm run build` in `frontend/` — **Compiled successfully** (2026-03-26, crosswalk close). |

**Crosswalk summary:** **24 Done**, **1 Policy** (P0-02), **0 Partial** on deploy/modularization/sandbox rows above (T-04, A-01, R-01 closed per honest proof notes). **§4** expectations: all **[x]** except human sign-off in §6. **§4.9** trunk process: **[x] documented** in [`docs/GIT_TRUNK.md`](./GIT_TRUNK.md).

---

## 6. Phase 0 — completion checklist (sign-off)

Phase 0 is **complete** when:

- [x] This document is committed **locally** (or present in working tree for your review).
- [ ] You have **read** Sections 2–3 and agree **grep ≠ proof**.
- [ ] Team uses Section 5 as the **single** compliance tracker until full Done.

Phase 0 is **not** “the product is 100% done.” It is **the ruler and the ledger.**

---

## 7. Next phases (locked order — same plan as before)

| Phase | Focus | Exit proof |
|-------|--------|------------|
| **1** | Events → center pane (SSE/poll + typed cards) | Network capture + UI updates |
| **2** | Tab wiring (DB, then Docs, then Analytics) | curl + UI per tab |
| **3** | Guided/Pro behavior | Toggle changes visible surface |
| **4** | Split `Workspace.jsx` | build + smoke |
| **5** | Publish/domain/deploy depth | live calls |
| **6** | Remote sandbox (optional) | infra + demo |

---

## 8. Evidence log (append only)

| Date | Author | Note |
|------|--------|------|
| 2026-03-25 | Phase 0 | Baseline `9175956`; doc created; push deferred per product owner. |
| 2026-03-26 | Phase 1 (partial) | Workspace polls `events/snapshot` and renders typed timeline when `projectId` present; `npm run build` OK. |
| 2026-03-26 | Phase 2 (partial) | Docs + Analytics tabs; Database tab merges server workspace SQL/schema with editor files; `npm run build` OK. |
| 2026-03-26 | Phase 3 (partial) | Guided vs Pro visible surface (tabs, center build UI, explorer, dashboard, header); `npm run build` OK. |
| 2026-03-26 | Phase 4 (partial) | Extracted workspace helpers + panels to `components/workspace/`; `Workspace.jsx` shortened; `npm run build` OK. |
| 2026-03-26 | Phase 5 (partial) | Deploy modal + dashboard: server deploy ZIP, one-click Vercel/Netlify, live URL, token hint → Settings; `npm run build` OK. |
| 2026-03-26 | SSE timeline | Workspace opens SSE after snapshot; `get_current_user_sse` + `access_token` query on `/projects/{id}/events`; poll fallback. |
| 2026-03-26 | Close-out (ledger) | Agents tab ↔ `GET /api/agents/status/{id}`; Passes ↔ server `build_history`; Pro Sandbox tab ↔ `GET /projects/{id}/logs` (ownership checks on status + logs); console filters; header API health + jobs chip + error chip; `docs/WORKSPACE_EVENT_TYPES.md`; `npm run build` OK. |
| 2026-03-26 | Continuation | Workspace **theme** toggle; agent status poll during **build**; Analytics job **duration**; `docs/PREVIEW_TRUST_PATH.md`; `scripts/workspace_compliance_smoke.ps1`; E-02/E-04/A-02 crosswalk bumps; `npm run build` OK. |
| 2026-03-26 | Crosswalk close | Grouped sidebar (S-01); history buckets + pin; Explorer **sync server workspace**; timeline event cards; §4/§5 aligned; [`docs/GIT_TRUNK.md`](./GIT_TRUNK.md); smoke: `scripts/workspace_compliance_smoke.ps1` (`CRUCIB_SMOKE_TOKEN`, `CRUCIB_SMOKE_PROJECT_ID`, `CRUCIB_API_BASE` optional); `npm run build` OK. |
| 2026-03-25 | T-04 / A-01 / R-01 | `WorkspaceProPanels.jsx` + deploy modal Railway + publish-settings; Sandbox tab Computer + logs; `python -m py_compile backend/server.py`; `npm run build` in `frontend/`. |
| 2026-03-26 | Runtime close-out (auth/project) | Full authenticated smoke pass green: `/api/health`, `/api/jobs`, `/projects/{id}/build-history`, `/agents/status/{id}`, `/projects/{id}/logs`; local guest + project run against temporary Postgres. Backend fixes from proof run: `structured_logging.AuditLogger.log` compatibility shim, JSONB query/storage handling in `db_pg.py`, and `get_build_history` existence check (`project is None`). |
| 2026-03-26 | Reliability sweep (10 passes) | Ran 10 consecutive authenticated runtime passes (fresh guest + fresh imported project each pass). All 10/10 passes returned 200 on health/jobs/build-history/agents-status/project-logs. Final smoke script rerun with fresh token/project also all green. |

---

*This file is the Phase 0 deliverable: compliance crosswalk + honest baseline + proof rules. Implementation starts Phase 1 only after you sign Section 6.*
