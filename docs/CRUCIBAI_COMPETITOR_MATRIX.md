# CrucibAI: competitor × axis scorecard (code evidence)

**Purpose:** Track where we **match**, **beat**, **are partial**, or **differ by design** versus five reference classes—using **file-level evidence**, not marketing. “Strongest in everything” is a **north star**; this matrix is the **ground truth** for what the repo actually ships and what is **still a workstream**.

**Companion docs:** `CRUCIBAI_CONTROL_PLANE_AUDIT_AND_ROADMAP.md` (narrative B2), `CRUCIBAI_CONTROL_PLANE_IMPLEMENTATION.md` (phased spine).

**Legend**

| Mark | Meaning |
|------|--------|
| **M** | Match / on par for our architecture |
| **+** | Credible differentiator in our favor (when productized) |
| **P** | Partial — spine exists, polish or coverage gap |
| **G** | Gap to close (explicit backlog) |
| **D** | Deliberate non-goal or different topology (document, don’t “fix” silently) |

---

## 1. Axes (what “best” is measured on)

| Axis | What it tests |
|------|----------------|
| **A1** | Durable run identity & UI binding (`job_id`, URL, rehydration) |
| **A2** | Live trace: SSE + event richness + user-visible activity (not only chat) |
| **A3** | **Terminal** (session, policy, who can run, audit) |
| **A4** | Orchestration: plan → DAG steps → `run-auto`, gates (preflight, spec guardian) |
| **A5** | Preview & artifacts: Sandpack / dev preview / `dev_server_url` / export |
| **A6** | Proof & verification: `proof` API, benchmarks, handoff |
| **A7** | Simulation: What-If / risk before run |
| **A8** | Extensibility: connectors, MCP-style tool IDs, skills |
| **A9** | IDE / workspace surfaces: one vs many shells, local vs server truth |
| **A10** | Advisory vs durable brain (Dashboard chat vs job stream) — clarity |

---

## 2. Core backend & orchestration (shared spine)

| Axis | Mark | Evidence | Notes |
|------|------|----------|--------|
| A4 | M | `backend/routes/orchestrator.py` — `POST /orchestrator/plan`, `POST /orchestrator/run-auto`, `build_dag_from_plan`, `create_step` | Job + persisted plan + step rows |
| A4 | M | `backend/db_pg.py` — `jobs`, `job_steps`, `job_events`, `proof_items`, `build_plans` | Relational orchestration model |
| A4 | P | `validation_checklist.md` vs `planner` — “full IntentSchema” thinner than checklist | G: expand structured intent when product asks for it |
| A4 | M | `run-auto` + `build_preflight_report`, `spec_guardian`, `evaluate_goal_against_runner` | Hard gate when `blocks_run` |
| A1 | M | `backend/routes/jobs.py` — `GET/POST` jobs, `GET /{id}/stream`, `POST /{id}/transcript` | Durable run + server chat log (see control plane) |
| A2 | M | `frontend/src/hooks/useJobStream.js` + `WorkspaceActivityFeed.jsx` | Feed beyond `brain_guidance`; **Phase 8** maps preflight, spec, `file_written`, verify, etc. |
| A6 | M | `GET /api/jobs/{id}/proof` in `jobs.py` | API-strong; keep UI tied to payload |
| A5 | M | `UnifiedWorkspace.jsx` — Sandpack merge, `export/full.zip?profile=handoff` | Artifact + handoff path |
| A7 | M | `frontend/src/pages/WhatIfPage.jsx` + `POST /runtime/what-if` | Pre-run simulation surface |
| A8 | P | `backend/services/mcp_client.py` — `mcp.<server>.<tool>` registry | Not full JSON-RPC MCP server; **narrow adapter** by design |
| A8 | P | `GET /api/settings/capabilities` — `connectors_configured` + `mcp.servers`; Settings → Engine room | Honest host-level map; still **G** if marketing implies connectors user doesn’t have |
| A3 | M | `backend/routes/terminal.py` — `POST /terminal/create`, `POST /terminal/{id}/execute`, `GET /terminal/audit` | **Terminal is real in repo** |
| A3 | P | `backend/terminal_integration.py` — policy blocks high-risk patterns | `backend/routes/trust.py` — production posture: interactive host terminal constrained |
| A3 | M | `frontend/src/workspace10/JobTerminalStrip.jsx` | UI wired to terminal API (job workspace context) |
| A9 | P | `frontend/src/App.js` — `/app/workspace` → `UnifiedWorkspace`, also `workspace-manus`, `workspace-classic`, `ide` | **Wayfinding:** Settings → Engine room → “Workspace surfaces”; **G:** consolidate shells when UI freeze lifts |
| A10 | P | `Dashboard` + `/ai/chat` vs `UnifiedWorkspace` + job SSE | C-E5: explicit advisory + `job_id` on Home; build subtitle when job active in `UnifiedWorkspace` |

---

## 3. By reference product (columns)

### 3.1 OpenAI **Codex** (class: durable run, artifacts, preview, background)

| Axis | Mark | Rationale (honest) |
|------|------|---------------------|
| A1 | M | `job_id` in URL + task store after plan (`UnifiedWorkspace` / control plane) |
| A2 | M/P | Activity feed + stream; “one transcript to rule them all” still depends on event emission on host |
| A3 | P | We have **server** terminal + policy; not the same as Codex’s productized computer-use UX |
| A4 | M | Strong: plan, DAG, auto-runner, spec guard |
| A5 | M | Preview panel + Sandpack + export; weaker if `dev_server_url` never populated on env |
| A6 | M | Proof API + proof memo paths in `trust` |
| A7 | + | **What-If** is explicit pre-run lane vs many artifact-only UIs |
| A8 | P | Connectors/MCP-in-spirit; must stay honest vs Goose-class breadth |
| A9 | D | We are a **web control plane**; local clone is user’s, not our default |
| A10 | P | Split advisory chat vs job — **clarity** is the bar |

**Beat vector:** A7 + A4 + A6 **when** preview/files/proof are populated end-to-end on production.

---

### 3.2 **Cursor** (IDE-native loop, local repo as truth, fast tools)

| Axis | Mark | Rationale |
|------|------|-----------|
| A1 | P | We have a **server** job table — *by design* not Cursor’s “no durable run object” model |
| A2 | P | Grounding is **hosted workspace**; not the same as LSP+local terminal intimacy |
| A3 | D | We expose terminal on **our** side; user’s local shell is not replaced |
| A4 | D | We optimize **orchestrated** builds, not 50 sub-second edit turns |
| A5 | P | In-browser preview/Sandpack vs native dev server on laptop |
| A6 | + | **Proof + job** can exceed “chat + diff” for **verifiable** deliverables |
| A7 | + | Systematic What-If vs ad-hoc refactors in IDE |
| A8 | P | Skills/MCP-narrow; Cursor ecosystem scope is different |
| A9 | P | `UnifiedIDEPage` exists but our wedge is **unified build workspace**, not replacing VSCode |
| A10 | G | If UI implies chat is source of truth, we lose to Cursor **and** our own rules — label channels |

**Beat vector:** A6, A4, A7 for **governed** long builds — **not** raw edit latency.

---

### 3.3 **Claude Code** (depth in one tree, terminal as actuator, serial work)

| Axis | Mark | Rationale |
|------|------|-----------|
| A1 | M | One `job_id` + one workspace path mental model for a run |
| A2 | P | `brain_guidance` + events; “full model-facing trace” = emission quality on host |
| A3 | M | **Terminal** stack exists (`terminal.py` + `JobTerminalStrip` + policy) — *claim it* |
| A4 | M | Orchestrated steps vs a single long CLI; different shape, same “serious work” |
| A5 | P | Artifacts in web UI; less “raw repo on disk” than local Claude Code |
| A6 | M | Proof + job events align with “show your work” |
| A7 | M | What-If complements long-horizon planning |
| A8 | P | Scriptability via API/benchmark; not shipping their CLI yet |
| A9 | G | `workspace-classic` / `manus` / `unified` — reduce confusion (product/GTM) |
| A10 | P | Same as above — job stream should read as the **primary** narrative during builds |

**Beat vector:** A4 + A6 + A3 (policy-governed) for **SaaS** where **Claude Code** wins on local intimacy.

---

### 3.4 **Goose** (extensibility, connectors, user-environment execution)

| Axis | Mark | Rationale |
|------|------|-----------|
| A1 | M | Same spine |
| A2 | M | Same |
| A3 | P | We gate terminal; Goose often pushes **to user** env — different trust model |
| A4 | M | DAG + plan |
| A5 | M | Export + preview |
| A6 | M | Proof |
| A7 | M | What-If |
| A8 | P/**G** | **G:** win only with **true** connector surfaces + no fake “live” labels |
| A9 | D | Server-centric; **D** = “on-device is not our default wedge” |
| A10 | P | Honesty bars |

**Beat vector:** A4 + A6 + **honest** A8; lose if we over-claim integration breadth.

---

### 3.5 **Manus** (archetype: intent → DAG → verify → handoff, recovery)

| Axis | Mark | Rationale |
|------|------|-----------|
| A1 | M | Control plane **E1** `jobId` + tasks |
| A2 | M | **E2** activity feed, `workspace_transcript` in events |
| A3 | M | Terminal in product — include in **all** “agent surfaces” checklists going forward |
| A4 | M | DAG in DB and stream; **G:** optional clarify-first **UI** gate (product choice) |
| A5 | M | Handoff export path |
| A6 | M | Proof — strong API |
| A7 | M | What-If = intent/risk pre-check |
| A8 | P | Checklist 160+ items vs code — keep checklist as **aspirational** or shrink claims |
| A9 | P | Multiple workspace routes — **G:** consolidate UX over time (when unfrozen) |
| A10 | M/P | E6 rehydration + failure UX (E5) — still watch “dual brain” |

**Beat vector:** A1 + A2 + A4 + A6 + A5 when the **UI always shows** state and **never** replaces job truth with chat alone.

---

## 4. Terminal — dedicated cross-check (user-critical surface)

| Layer | File / route | Mark |
|-------|----------------|------|
| API | `POST /api/terminal/create`, `POST /api/terminal/{id}/execute`, `DELETE /api/terminal/{id}`, `GET /api/terminal/audit` | M |
| Policy & sandbox note | `backend/terminal_integration.py`, `backend/routes/trust.py` | P (by design: lock down public abuse) |
| Job UI strip | `frontend/src/workspace10/JobTerminalStrip.jsx` | M |
| Other UI | `IDETerminal.jsx`, `TerminalAgent.jsx`, `Workspace.jsx` console, `UnifiedIDEPage` | P — multiple entry points; same policy applies via API |

**Gap to track (G):** “Feels as instant as local terminal” is **not** a pure engineering toggle—depends on **hosting**, **session model**, and **admin vs user** policy (`trust`).

---

## 5. How we keep “unbeaten” **honest**

1. **No row without** either **M/+**, a **G** with an owner, or a **D** with a customer-facing line.
2. Re-run this matrix on each **orchestrator** or **jobs API** change; update **evidence** paths.
3. For releases: smoke **A1** (URL), **A2** (feed + events), **A3** (create + execute + audit), **A4** (plan + run + guard), **A5** (preview + export).

**Last update:** 2026-04-25 — Phase 7 honesty (capabilities API, Settings Engine room, dual-channel copy); terminal row unchanged.
