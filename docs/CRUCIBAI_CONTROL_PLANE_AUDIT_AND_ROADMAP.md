# CrucibAI: deep comparative audit & control-plane roadmap (revised)

**Status:** This document **supersedes** the short “class matrix only” pass. It is **code-grounded**, ties **your reported symptoms** to **file-level behavior**, and situates CrucibAI against **Codex-class**, **Manus-style**, **Claude Code**, **Goose**, and **Cursor** expectations using the same research lens as `research/` and your Manus/Codex checklists (e.g. `validation_checklist.md`).

**How to use:** Each issue lists **evidence in repo** and **what “best in class” does differently**. This is the baseline to **not** be weak: implementation work should **tick** these findings, not re-argue from zero.

---

## Part A — CrucibAI’s own product vision (from this repo, not marketing)

1. **Proof-driven build-and-operations control plane** (your Codex-level directive) — *not* a chat-only tool: **What-If before**, **trace during**, **proof after**, **deployable** output.
2. **Manus-style validation spine** is encoded in `validation_checklist.md` (intent, DAG, verification, handoff) — the repo **explicitly** uses that as a **north star**, even where implementation is **partial**.
3. **“Truth in three places”** recovery theme from prior research: **DB + disk + UI** must agree; **chat is not** the system of record.
4. **Golden paths and proof memos** under `proof/` and `docs/` — many flows **pass on backend**; **UI wiring** is the common gap.
5. **Wedge** you claim vs plain Codex: **simulation (What-If) + proof bundle + job lifecycle** — all **must** surface from **real** `job_id` data, not narrative.

**Strategic line:** The greatest product here is the one where **invariants** are **enforced** (job row, stream, files, proof, preview URL) — the assistant is a **lens** on that spine, not a replacement for it. This matches the Cursor/Composer “agent truths” research you own.

---

## Part B — Reference products: what “good” means (compressed, for comparison)

| Product / archetype | What users *feel* when it works | Technical spine (typical) |
|---------------------|---------------------------------|---------------------------|
| **OpenAI Codex (2025–26 product class)** | Artifact-centric: live preview, files, **visible** work, **background** runs, extensible automations. | **Durable** run records, **IDE/server** co-located build, **preview** URL or embedded surface. |
| **Cursor (Composer / agent in IDE)** | Tight **read→edit→run** loop, **grounded** in workspace. | **Turn-based** model + **tools**; no magic job DB in the model — **the repo + CI** are truth. |
| **Claude Code** | Long-horizon **repo** work, **terminal** as actuator, “agent” in **one** project tree. | Single workspace, **scriptable** invocations, **one** CWD. |
| **Goose (Block-style)** | **Connectors** + extensibility; “do work” in **user’s** environment. | Plugins, often **local** or **MCP**-style; honesty about what’s “live” vs “coming soon.” |
| **Manus (as in your checklists, not a vendor spec)** | **Clarified intent** → **DAG** → **verify** each step → **handoff** artifact. | **Persistent** run graph, **enforced** gates, **recovery** on failure. |

**Composite “best to beat” (for *your* wedge):** **Codex**-class **live artifacts + preview** + **Manus**-class **job spine + proof** + **Goose**-like **extensibility** without **fake** connectors + **Claude**-like **deep repo truth** + **Cursor**-like **grounded** assistant behavior. **CrucibAI** claims this via **orchestrator + jobs API + What-If** — the audit below checks **code**, not the pitch.

---

## Part C — Your reported issues → what the code actually does

### C1. “Conversational chat / middle pane frozen; not showing what is building; AI doesn’t know itself”

**Code reality (`UnifiedWorkspace.jsx` + `useJobStream.js`):**

- The **center feed** is driven by `userChatMessages` (React state), **not** a server-backed chat table for every line. User messages are appended via `appendUserChat`. Assistant-side **build narration** is **largely** driven by **SSE** events, specifically the hook that maps **`brain_guidance`** events into assistant messages:

  ```622:662:frontend/src/pages/UnifiedWorkspace.jsx
  // Wire brain_guidance SSE events → live chat feed so the brain talks during builds
  // PERSISTENCE FIX: Process ALL brain_guidance events (not just the last) ...
  ```

- **Implication:** If the **orchestrator / runtime does not emit** `brain_guidance` (or emits rarely), the **center pane looks dead** even though `useJobStream` is connected — **this matches “not conversationally showing what is building.”**

- `useJobStream` uses **fetch + ReadableStream** to `/api/jobs/{id}/stream` and falls back to **polling** `GET /api/jobs/{id}`, steps, events, proof. The **“frozen”** feeling also occurred when **stale UI** was not cleared on job switch — the file now has an explicit **job-switch reset** (see C4).

- **“AI doesn’t know itself”** in practice = **no unified system prompt in the product layer** that injects **job id, stage, and last event** into *every* follow-up. The **Dashboard** may still use `/ai/chat` for **advisory** text that is **not** the same as **orchestrator** state. Two **cognitive** channels → user sees **inconsistent** “personality” and **facts**.

**Reference comparison:** **Codex**-style UPs usually tie the **active run** to a **single** run object and **stream** all tool/file events to the same transcript. **Cursor** keeps the **file + terminal** as ground truth. **You** need either **(a)** more **`brain_guidance` / event → chat** mapping for **all** important step types, or **(b)** a **dedicated** “Activity” line that is **not** chat-shaped but is **always** on during `running`.

---

### C2. “No persistent state”

**Code reality:**

- **Tasks** in the sidebar are **`useTaskStore` → `localStorage` (`crucibai_tasks`)** — `frontend/src/stores/useTaskStore.js`. That is **durable** on one browser but **not** a **server** truth for “who am I and what did I run.”
- **Job** truth is on the **server** via `GET /api/jobs/{id}`; **chat lines** in `userChatMessages` are **in-memory** until **(a)** you reload from **events** or **(b)** you implement **server-side** conversation persistence per job.
- **Implication:** “Persistence” is **split-brain** today: **job** can survive refresh if URL has `jobId=`, **ephemeral** chat can **rehydrate partially** from **job events** (see comments on `brain_guidance`) but is **not** a full **Slack-style** log unless the **backend** stores messages.

**Reference comparison:** **Manus**-grade narrative in your checklists assumed **durable** job + transcript; **Cursor** is explicit that **only git** is durable. You want **stronger** than Cursor for **ops** — that means **server** conversation or **event log** is the **product** read model.

---

### C3. “Preview not showing / should be almost live”

**Code reality:**

- `PreviewPanel.jsx` (used from workspace shell) tries **(1)** `previewUrl` prop, **(2)** `GET /api/jobs/{jobId}/dev-preview` for **`dev_server_url`**, **(3)** **Sandpack** from merged files, **(4)** optional **WebSocket** `.../ws/jobs/{id}/preview-watch` to **reload** iframe on file change.

- In `UnifiedWorkspace.jsx`, `previewUrl` is derived from **`job.dev_server_url` / `preview_url` / `published_url` / `deploy_url`** or a **published** path pattern when **completed** — if **`job` never** gets those fields and **files** are empty, the panel correctly falls back to **empty / waiting / trust banner** but **user experience** is “**preview broken**”.

- **Root causes to verify in prod:** (1) **Job record** not populated with preview URLs after build, (2) **`dev-preview`** endpoint error (auth, job not in runnable state), (3) **CORS/iframe** to Railway, (4) **Sandpack** fallback path missing **`App.jsx`** (banner exists).

**Reference comparison:** **Codex**-class **lives** on **one** “you can see it” surface; you have **the right components**; the gap is **data** to `PreviewPanel`, not a missing `iframe` **concept**.

---

### C4. “Code not created in code room / files not showing”

**Code reality:**

- The **“code room”** is the **API-backed workspace** tree + `wsFileCache` — files load when **`/api/jobs/.../workspace/...`** returns bodies; `workspacePullKey` bumps on **DAG node completion** and on **job failure** (to re-pull). **Merge** for Sandpack is `sandpackMergeFiles` = `DEFAULT_FILES` + `files` + **cached** server files.

- If the **orchestrator never writes** to the job workspace, or the **file list** route returns empty, the tree stays **empty** — this is **honest** but feels “broken” if marketing says “code room always full.”

**Reference comparison:** **Claude Code**-style: **one** working tree. **You** have **one** `job_id` — **wiring** must guarantee **file_writer**-equivalent path on the **server** for every build step (your own **ui_safety_proof** / **file writer** docs).

---

### C5. “When build fails, everything disappeared” (legacy; may be fixed)

**Code today:**

- `useJobStream` fetches `latestFailure`, proof, steps; `UnifiedWorkspace` has **Failure** / **proof** / **error** raw handling and **refreshes** file pull on `job.status === 'failed'`. The **orchestrator** can still return **redacted** or **empty** failure UI if **events** are missing — that’s a **server** + **UI** join.

- **Implication:** “Disappearing” was often **(a)** **state reset** bug or **(b)** **no** failure row in `job` DTO. Your codebase **acknowledges** the class of problem in **comments** and **proof** test memos; **treat** any recurrence as a **P0** trace on **`GET /api/jobs/{id}`** and **`events`** for failed runs.

---

### C6. “Can’t toggle from one build to another — have to go through chat”

**Code reality (high-signal):**

- Sidebar **navigates** to `/app/workspace?taskId=...&jobId=...` when `item.jobId` is present — `Sidebar.jsx` around **item.jobId** in query string. If **`task` has no `jobId` yet** (only local task row), the workspace opens with **task** but **no** `jobId` → stream **doesn’t** attach, **orchestrator** may be idle → user **bounces** through **chat/plan** to get a `job_id`.

- **Job switch reset** (`setUserChatMessages([])` on `jobIdFromUrl` change) **wipes the visible transcript** on purpose to avoid **stale** data — that **feels** like “I can’t switch builds fluidly” if **server-side** job-scoped **history** is not reloaded for the new `jobId`.

- **“Effective” `jobId`:** `effectiveJobId = jobIdFromUrl || jobId` so URL wins — good — but any **mismatch** between **sidebar** `task` pointer and **server** job will **hiccup**.

**Reference comparison:** **Codex** runs are **listable**; click run → see **one** run. You need the **task list** to **always** store **`jobId`** after plan creation (your store already has `jobId` on task update path in `UnifiedWorkspace` when bound — verify **all** create paths set it).

---

## Part D — Synthesis: where CrucibAI **wins** on paper vs where it **loses in UX** today

| Dimension | On paper (repo + backend) | In UX (from code + your reports) |
|-----------|----------------------------|------------------------------------|
| **Job spine** | **Strong** — jobs, stream, steps, proof, workspace files, export zip, What-If route | **Fragmented** — Dashboard chat vs **orchestrator** plan/run; user may lack **`jobId`** in URL early |
| **Live trace** | **Strong** — SSE + poll, events → `steps`/`proof` | **Chat feels quiet** if only **`brain_guidance`** is mapped to “assistant” text |
| **Preview** | **Strong** — `dev-preview`, iframe, WS watch, Sandpack | **Data-dependent** — URLs must land on `job` + files |
| **Persistence** | **Split** — server job + local task list | **No** full server chat log **per** job in `UnifiedWorkspace` as read model |
| **Mode / polish** | **Many** components (`ThreePaneWorkspace`, `Workspace`, etc.) | **One** user path must dominate (`UnifiedWorkspace` on `/app/workspace`) to avoid “which workspace am I in?” |

---

## Part E — Engineering priority order (tied to **your** pain, not generic agile)

1. **Single run identity in the URL and task store** — every **runnable** task has **`jobId`** as soon as **plan** returns; **sidebar** and **share links** must preserve it. **Validates** C6.
2. **Activity feed contract** — either **(a)** expand **event → chat** mapping beyond **`brain_guidance`**, or **(b)** add a **non-chat** “Live activity” list bound to `events` always visible during `running`. **Validates** C1.
3. **Preview pipeline verification** — for a **failing** and **succeeding** job on **Railway**, log **`job` JSON** and **`dev-preview` response**; fix **data**, not the iframe. **Validates** C3.
4. **Workspace file pull on every important step** — already partially there; ensure **orchestrator** always writes to job workspace. **Validates** C4.
5. **Failed-run UX** — never clear **Failure** DTO; **E2E** on failed job. **Validates** C5.
6. **Server-side or event-log “conversation”** (optional, larger) for **true** cross-device persistence. **Validates** C2.

**Commit train** (aligned with your earlier directive, now **grounded**): **WORKSPACE-TRACE** → **PREVIEW-DATA** → **TASK-JOB-BINDING** → **CLEANUP** of duplicate workspace routes / dead panels.

---

## Part F — “Weak doc” self-critique: what this revision fixes

- **Names real files and hooks** (`useJobStream`, `UnifiedWorkspace`, `PreviewPanel`, `useTaskStore`, `Sidebar` query params) instead of only “Class 1–8.”
- **Maps** your **concrete** complaints to **line-of-business** code paths.
- **Explicitly** uses **Competitor** only as a **rubric** — the **wedge** is **your** **What-If + proof + job** design, with **gaps** called honestly.
- **Does not** claim line-by-line **every** file — **Part E** is the **punch list**; extend with **tickets** per bullet.

---

## Part G — Appendix: quick file index (working set)

| Concern | Primary files |
|---------|-----------------|
| Job stream, poll, proof | `frontend/src/hooks/useJobStream.js` |
| Workspace UX, chat feed, plan/run | `frontend/src/pages/UnifiedWorkspace.jsx` |
| Preview | `frontend/src/components/AutoRunner/PreviewPanel.jsx` (and imports in `UnifiedWorkspace`) |
| Task list / local persistence | `frontend/src/stores/useTaskStore.js` |
| Sidebar **taskId+jobId** | `frontend/src/components/Sidebar.jsx` |
| Legacy rich workspace | `frontend/src/pages/Workspace.jsx` (still has **EventSource** patterns for some paths) |
| **API** | `backend/routes/jobs.py`, `preview_serve.py`, orchestrator under `backend/routes/orchestrator.py` / `server.py` (per deploy) |
| **Vision / checklist** | `validation_checklist.md`, your Codex directive (chat), `research/*` in parent workspace |

---

*Maintainers: when you close an item in Part C, add the **PR / commit** and a **one-line** “before/after” under that subsection.*
