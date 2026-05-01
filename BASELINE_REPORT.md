# Baseline report — first visible preview (`/api/preview/{jobId}/serve`)

Freeze date (UTC): **2026-04-30** (repository freeze).

## Scope

This documents the **best-effort on-disk snapshot** tied to the most recently touched workspace under `workspaces/` that contained runtime evidence for a preview-capable job, plus the **git tree** exactly as committed on branch `freeze/first-visible-preview-baseline`.

**Important:** The canonical “first visible preview” may have been produced on a **running backend** with a different `job_id` than the snapshot below. This report records what was **present in this checkout** at freeze time.

## Job and URLs

| Field | Value |
|--------|--------|
| **Job ID** (runtime task id) | `tsk_27e3fcf0d496` |
| **Project / workspace UUID** | `9d6766e2-1bf5-4f27-ab36-fe6621ebaad7` |
| **Preview URL (path-only)** | `/api/preview/tsk_27e3fcf0d496/serve` |
| **Task JSON** | `workspaces/9d6766e2-1bf5-4f27-ab36-fe6621ebaad7/runtime_tasks/tsk_27e3fcf0d496.json` |

## Original user prompt (from exported task)

> Build a one-page local test app with a hero title and contact section.

(Source: `metadata.goal` in `runtime_tasks/tsk_27e3fcf0d496.json`.)

## Generated plan

No separate `plan_created` / structured plan artifact was found in the copied `runtime_state` event tail at freeze time. The event stream begins with `task_created` and a long series of `step_created` entries, then `preflight_report` and `spec_guardian`. If a plan exists elsewhere (DB, chat, or later events), it was **not** present in the exported JSON slice on disk.

## Generated application files (repo workspace)

| Check | Result at freeze |
|--------|-------------------|
| **`workspaces/projects/9d6766e2-1bf5-4f27-ab36-fe6621ebaad7/`** | Directory existed but was **empty** (no `package.json`, no `src/`, no `dist/`). |
| **`workspaces/9d6766e2-1bf5-4f27-ab36-fe6621ebaad7/`** (legacy layout) | Contained only `runtime_state/` and `runtime_tasks/` — **no app source tree**. |
| **`package.json` in project workspace** | **Not found** under the resolved project path above. |
| **`dist/` or `build/` with `index.html`** | **Not found** under that project path (preview serve root would be unresolved for a static tree at this path). |

**Conclusion for this snapshot:** the freeze **preserves orchestration / runtime JSON**, not a generated Vite/React tree, for this UUID on this machine.

Exported copy: `artifacts/preview-baseline-first-visible-output/export/` (recursive copy of `runtime_state` and `runtime_tasks` for that workspace).

## Build logs

No separate build log files were collected under the workspace root. Relevant diagnostic content appears inside **`events.json`** as structured JSON (e.g. `preflight_report` payload). Full copy: `artifacts/preview-baseline-first-visible-output/export/runtime_state/tsk_27e3fcf0d496/events.json`.

### Preflight excerpt (from `events.json`)

- **Playwright Chromium:** not available (`playwright_chromium` check failed; suggested `python -m playwright install chromium`).
- **Python / npm / git / docker:** reported OK per embedded preflight payload (see export).

## Runtime / agent events

- **Location:** `artifacts/preview-baseline-first-visible-output/export/runtime_state/tsk_27e3fcf0d496/events.json`
- **Types observed (non-exhaustive):** `task_created`, `step_created`, `preflight_report`, `spec_guardian`
- **DAG steps:** numerous `agents.*` and `verification.*` / `deploy.*` steps created (see `steps.json` in the same folder).

## Model / provider

**Not present** in `runtime_tasks/tsk_27e3fcf0d496.json` or the sampled `events.json` payloads at freeze time. If the orchestrator records model/provider in DB or other events, that was **not** in the exported files.

## Timestamps

- Task `created_at` / `updated_at` (epoch seconds in JSON): **1777516215.646108** (see task file).
- Workspace directory `LastWriteTime` (local NTFS): **2026-04-29** (approx. 22:30 per directory listing during freeze).

## Preview semantics (code reference — not modified in freeze)

From `backend/routes/preview_serve.py`, static preview serving expects a workspace with **`dist/index.html`**, **`build/index.html`**, or root **`index.html`**. If none exist, the route cannot serve a complete built app from that tree.

## CSS / React / Vite / assets (for this disk snapshot)

| Question | Answer |
|----------|--------|
| **CSS loaded?** | **Unknown / N/A** — no built `index.html` bundle in the exported workspace tree. |
| **React/Vite mounted?** | **Unknown / N/A** — no `package.json` or app sources in the exported project path. |
| **Assets built?** | **No evidence** in `workspaces/projects/{uuid}` at freeze. |

## Backend: raw files vs running app

For **`GET /api/preview/{job_id}/serve`**, the implementation serves **files from disk** (static `FileResponse` style) from the resolved serve root — not an in-process React runtime. A “running app” in the browser is still **client-side** JS from those files.

## Exact commands run (freeze automation)

PowerShell (export copy):

```powershell
$base = "…\RELEASE-CRUCIB-2026"
$art = Join-Path $base "artifacts\preview-baseline-first-visible-output\export"
$src = Join-Path $base "workspaces\9d6766e2-1bf5-4f27-ab36-fe6621ebaad7"
New-Item -ItemType Directory -Force -Path $art | Out-Null
Copy-Item -Recurse -Force (Join-Path $src "runtime_state") (Join-Path $art "runtime_state")
Copy-Item -Recurse -Force (Join-Path $src "runtime_tasks") (Join-Path $art "runtime_tasks")
```

Git (from `RELEASE-CRUCIB-2026`):

```text
git checkout -b freeze/first-visible-preview-baseline
git add -A
git commit -m "baseline: freeze first visible preview output before repair"
git tag -a preview-baseline-first-visible-output -m "First visible preview baseline freeze"
```

## Screenshots

Directory: `docs/proof/preview-baseline-first-visible-output/`

See `README_SCREENSHOTS.md` there. **No image files** were produced in automation.

## What works (product / infra — qualitative)

- **Preview route exists in codebase:** `/api/preview/{job_id}/serve` and related resolver logic (`preview_serve.py`, `workspace_resolver.py`).
- **Runtime persistence on disk:** `runtime_state` + `runtime_tasks` JSON for job `tsk_27e3fcf0d496` under workspace UUID `9d6766e2-1bf5-4f27-ab36-fe6621ebaad7`.

## What is broken / incomplete (this snapshot)

- **No generated app tree** under `workspaces/projects/9d6766e2-1bf5-4f27-ab36-fe6621ebaad7` at freeze.
- **Preflight:** Playwright Chromium missing (see `preflight_report` in `events.json`).
- **Task status** in JSON: still `"running"` in `tsk_27e3fcf0d496.json` at freeze (may be stale vs live orchestrator).

## Git commit SHA

After checking out this branch, resolve the frozen commit with:

`git rev-parse HEAD`

The annotated tag `preview-baseline-first-visible-output` is created on that same commit (no drift).
