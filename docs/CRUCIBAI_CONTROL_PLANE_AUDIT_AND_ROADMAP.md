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

## Part B2 — **Comparative operations & “agent internals” (the five, vs us)**

This is the **per-product** comparison that was **missing** in the first deep pass: for **each** reference, we state **how that class of system typically operates** (from public patterns + your research framing), then **where CrucibAI’s implementation matches, diverges, or is undefined**. This is not marketing copy; it is a **rubric to beat**.

### B2.1 OpenAI **Codex** (product class: computer use + runs + artifacts)

| Typical **operations** (what “good” looks like) | **CrucibAI in this repo** | **Delta (honest)** |
|--------------------------------------------------|-----------------------------|----------------------|
| One **durable** “run” or session object the UI always points at | `job_id` + `GET/POST` under `/api/jobs`, `useJobStream` on **`/api/jobs/{id}/stream`** | **Match** in backend shape; **UX** can still show **no** `jobId` in URL if plan handoff lags. |
| **Transcript of work** = tool + file + step output in **one** feed | `events` in job stream; **center chat** = **user** + **`brain_guidance` → assistant** in `UnifiedWorkspace` | **Weaker** unless **orchestrator** emits rich guidance, or we **map more event types** to the feed. |
| **Preview** is first-class, URL-backed, reloads on change | `PreviewPanel`, `dev-preview`, iframe, **WS** `preview-watch` | **Match in UI**; **weaker** if **`job` lacks URLs** or **files** never land. |
| “Background” and multi-tool automation | `orchestrator/plan`, `orchestrator/run-auto`, long-running job | **Partial** — depends on **host** and **orchestrator** health on Railway. |

**Bottom line vs Codex:** We have the **skeleton** (job, stream, preview component); **Codex** wins when **one run** always **drives** the whole UI. We still split **advisory** `/ai/chat` and **durable** job runs — that **operational** split is a **key** difference from “artifact-centric” UPs.

---

### B2.2 **Cursor** (Composer: IDE agent, tools, repo-grounded)

| Typical **operations** | **CrucibAI** | **Delta** |
|-------------------------|-------------|-----------|
| **Turns** in one workspace; “truth” = **read files + terminal** | Build truth is **server job workspace** + API file routes; not the same as **one local clone in Cursor** | **Different topology** (hosted job workspace vs local repo). Ours is **closer to** a **web control plane** than to Cursor’s local loop. |
| **No** hidden job table in the *model*; CI/git are truth | We **intentionally** have a **server job** table and stream — that’s a **strategic** difference (more “Manus than Cursor” for the run object). | **By design** we are **not** imitating Cursor’s **ephemeral** chat-only truth. **Risk:** if **chat** in Dashboard **sounds** like source of truth, we **violate** both Cursor and our own “job is truth” rule. |
| Fast **edit** loop | Ours is **orchestrated** multi-step, not 50 single-file turns | **Slower** by nature; our wedge is **proof + simulation**, not edit latency. |

**Bottom line vs Cursor:** Cursor’s **strength** is **grounding in one tree**. Ours is **orchestrated** **build**; we must be **candid** in UI that the **file tree** is the **job workspace on the server**, and **rehydrate** that tree **reliably** (no empty “code room” without explanation).

---

### B2.3 **Claude Code** (headless / terminal / single-project depth)

| Typical **operations** | **CrucibAI** | **Delta** |
|-------------------------|-------------|-----------|
| **One** working directory, one process mental model | **One** `job_id` and workspace paths under that job on API | **Match** in concept. **Diverge** if **user** can open **Workspace** + **WorkspaceManus** + **classic** and get **confused** — multiple shells in `App.js`. |
| **Terminal + patch** are the actuators | Our actuators are **orchestrator** + **file_writer**-style **backend** processes | **Stronger** for **SaaS**; **weaker** for “I need raw shell on my machine” unless we expose that honestly. |
| **Long** serial reasoning | `brain_guidance` + `events` | **Weaker** if the **transcript** doesn’t show **all** model-facing steps, only a subset. |

**Bottom line vs Claude Code:** We trade **raw terminal intimacy** for **orchestrated** output and **proof**; the **comparative** risk is **depth of trace** in the **chat** view, not lack of a **job** object.

---

### B2.4 **Goose** (extensibility, connectors, “do work in the user world”)

| Typical **operations** | **CrucibAI** | **Delta** |
|-------------------------|-------------|-----------|
| **Plugins** / MCP / many integrations, clearly labeled | Skills, channels, **many** `App.js` routes; **capability** notices from orchestrator plan | **Match** in ambition; must **not** mark connectors **live** when they’re stubbed (per your directive Class 5). |
| **Local** execution on user machine for some tools | Ours is **server-centric** (Railway) | **Strategic** difference: our **wedge** is **hosted** **build + verify**, not on-device. |

**Bottom line vs Goose:** We win on **unified** **job + proof** in **one** product; we lose if we **imply** external integrations that aren’t **wired**.

---

### B2.5 **Manus** (archetype in *your* checklists — intent, DAG, recovery)

| **Checklist** layer (from `validation_checklist.md` frame) | **CrucibAI in code** | **Delta** |
|---------------------------------------------------------|------------------------|-----------|
| **Intent** as structured object | `orchestrator/plan` with **goal**, **build_target** — **not** the full JSON “IntentSchema” the checklist names | **Partial**; checklist is **aspirational**; **code** is **thinner** than the 160+ checklist. |
| **DAG** visible & enforced | `steps` from API + `dag_node_*` in stream; `events` in `useJobStream` | **Match** in **data**; **UI** must not hide **graph** in favor of only chat. |
| **Clarification gate** for ambiguity | **Not** a hard product gate in `UnifiedWorkspace` in the way the checklist describes | **Weaker**; we often **act** (plan/run) without **clarify-first** **UI**. |
| **Recovery / repair** | `latestFailure`, `repair` endpoints in tests, **AutoRunner** resume/cancel in workspace | **Partial**; must stay **visible** on failure (your “disappearing” history). |
| **Proof** | `GET /api/jobs/{id}/proof` + `Proof` pane patterns | **Strong** in API; must stay **tied to** **UI** and **not** a fake paragraph. |

**Bottom line vs your Manus model:** The **back end** and **stream** are **on the right track**; the **gaps** are **front-end** **honesty** (always show state), **clarify** (optional product choice), and **transcript = events**, not just **`brain_guidance`**.

---

## Part B3 — **Issues the audit found *without* you listing them** (independent findings)

These are **additional** gaps or risks spotted while reading code — they overlap **your** five but are **not** the same list.

1. **Dual “brain” for text:** `Dashboard` → **`/ai/chat`** and workspace → **orchestrator** + **SSE** — the user can get **two** incompatible explanations for “what is happening” unless we **unify** or **label** the channels.
2. **Narrow “assistant” channel during build:** only **`brain_guidance`** (plus manual chat) is clearly wired into **`userChatMessages` → assistant** for live build; **all other** `events` are **in `events` state** but not necessarily **in the main conversational column** — feels “not talking.”
3. **Task↔job binding:** if **`addTask` / history row** has **no** `jobId` until late, `Sidebar` **opens** `?taskId=…` without `jobId=…` — stream **can’t** attach; **comparative** to **Codex** (always has run id) and **Manus** (run is primary key).
4. **Multiple workspace surfaces:** `UnifiedWorkspace` vs `Workspace` vs `WorkspaceManus` in `App.js` — same company, **three** “internal” UIs; **operational** risk for users and for **us** (bugs fixed in one, not the other).
5. **Client-only task persistence:** `useTaskStore` is **not** a **cross-device** or **compliance** store — if we claim “history” in an enterprise sense, we’re **weaker** than any **SaaS** with a real **DB**-backed task list.
6. **Rehydration vs reset:** on **job switch**, chat is **cleared** by design; **rehydration** from **`GET /events`** for that job’s chat-like lines is **not** guaranteed in one shot — can feel like “no memory.”
7. **Preview and proof depend on** **`job` DTO** fields populated by the **orchestrator** on your **hosting**; front-end can be **green** and still **empty** if **backend** never sets `dev_server_url` / file tree.

**Count:** the **user-listed** problems are the **highest pain**; the **independent** list is **why** the product can still “feel” wrong even as **tickets** close one by one.

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

## Part F — Document history (what each revision added)

- **Revision 1 (too thin):** Class-style matrix only — **you** were right: not enough **comparative** depth.
- **Revision 2:** **Part C–E** + your five issues tied to **code**.
- **Revision 3 (this):** **Part B2** — **full five-way** **operational** comparison (Codex, Cursor, Claude Code, Goose, Manus-as-checklist) with **match / delta** tables; **Part B3** — **independent** issues found in review **besides** your five.

**Still not claiming:** access to **private** vendor internals — **Manus** here means **your** checklist archetype, not proprietary server maps.

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
