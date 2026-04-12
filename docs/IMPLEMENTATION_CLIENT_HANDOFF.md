# CrucibAI — implementation handoff (approved architecture slice)

This document is the **client-facing implementation record** for the work landed in this pass and the **ordered backlog** for the full architecture plan you approved (audit → manifests → assembly → profiles → proof bind → ZIP parity).

---

## What shipped in this pass (concrete)

### 1. Agent DAG audit (P0)

| Artifact | Purpose |
|----------|---------|
| `backend/scripts/audit_agent_dag.py` | Regenerates classification from **live imports**: `AGENT_DAG`, `REAL_AGENT_NAMES`, `ARTIFACT_PATHS`, `STATE_WRITERS`, `POST_STEP_AGENTS`, `TOOL_RUNNER_STATE_KEYS`, deploy/automation heuristics. |
| `docs/agent_audit.csv` | Spreadsheet-friendly view. |
| `docs/agent_audit.json` | Machine-readable + `counts_by_group`. |

**Run locally**

```bash
cd backend
set PYTHONPATH=.
python scripts/audit_agent_dag.py
python scripts/audit_agent_dag.py --check
```

**CI** — `.github/workflows/enterprise-tests.yml` job `agent-dag-audit` runs `--check` on every PR/push.

**Tests** — `backend/tests/test_audit_agent_dag.py`.

**Rule for contributors:** any change to `agent_dag.py` or classification inputs must re-run the script (without `--check`) and commit updated `docs/agent_audit.*`, or CI fails on `--check`.

### 2. Workspace seal + manifests (assembly v0)

| Module | Purpose |
|--------|---------|
| `backend/orchestration/workspace_assembly.py` | On **successful** Auto-Runner completion, writes under `<project_workspace>/META/`: `run_manifest.json`, `artifact_manifest.json`, `seal.json`. Emits `workspace_sealed` job event. |

**Hook** — `backend/orchestration/auto_runner.py` immediately before the job is marked `completed`.

**Semantics**

- `artifact_manifest.json` lists **workspace files** (hashes, sizes). `META/` itself is excluded from the manifest body to avoid recursion noise.
- This is **evidence**, not yet the full “merge policy / last writer per path” table from the long-term plan.

### 3. P2 — `WorkspaceAssemblyPipeline` (multi-file assembly, feature-flagged)

| Module / entry | Purpose |
|----------------|---------|
| `backend/orchestration/workspace_assembly_pipeline.py` | **Ingest** outputs from upstream agents in `previous_outputs`, **parse** path-tagged fenced blocks (` ```tsx src/foo.jsx …``` ` and variants), **merge** last-writer-wins per relative path, **materialize** with `executor._safe_write` (same prose/fence stripping as the runner). |
| `CRUCIBAI_ASSEMBLY_V2` | Must be `1`, `true`, `yes`, or `on` to activate. **Default: off** — production behavior unchanged until you set the flag. |
| `real_agent_runner._run_file_tool_agent` | When V2 on, **replaces** the narrow four-file-only writer with `materialize_from_previous_outputs`, then fills missing **Vite preview contract** files via `executor._ensure_preview_contract_files` (merge-only where files already exist). |
| `swarm_agent_runner.run_swarm_agent_step` | When V2 on, after each swarm LLM step, **materialize_swarm_agent_output** writes extra paths from multi-file fences and extends `output_files`. |

**First supported profiles:** V2 path is aligned with the existing **Vite + React + Python sketch** contract (`build_target` stub `vite_react` for the preview overlay). Broader profiles (Next-only, mobile, etc.) still follow the roadmap below.

**Tests** — `backend/tests/test_workspace_assembly_pipeline.py`.

### 4. One full-project ZIP export

| Route | Auth | Behavior |
|-------|------|----------|
| `GET /api/jobs/{job_id}/export/full.zip` | Bearer (same as other job APIs) | Resolves `job → project_id → WORKSPACE_ROOT/<project_id>`, zips tree (skips `node_modules`, `.git`, common caches). Deletes temp zip after response via `BackgroundTask`. |

**Frontend / client:** download with `Authorization: Bearer <token>`. Suggested filename already prefixed `crucibai-job-…-full.zip`.

### 5. P5 — Proof index ↔ artifact manifest (wired)

| Piece | Purpose |
|-------|---------|
| `backend/orchestration/proof_index.py` | Builds `META/proof_index.json` on seal: for each `proof_items` row, extracts path-like strings from `payload_json`, classifies into **resolved in manifest** vs **missing**, and builds **`by_path`** reverse index. |
| `proof_service.fetch_proof_items_raw(job_id)` | DB read for seal-time index build. |
| `proof_service.get_proof` | Adds **`proof_index`** to the JSON returned by `GET /api/jobs/{job_id}/proof` when `workspace/<project_id>/META/proof_index.json` exists (after a successful sealed run). |
| `workspace_assembly.seal_completed_job_workspace` | After `artifact_manifest.json` / `seal.json`, calls `write_meta_proof_index`. |
| `ProofPanel.jsx` + `ProofPanel.css` | **Summary:** `by_path` list (50 paths). **Per row:** `by_proof_item_id[item.id]` shows resolved/missing path chips on each proof item. |
| `proof_bundle_generator.py` | **`workspace_meta/`** in the on-disk proof bundle: copies `META/proof_index.json`, `artifact_manifest.json`, `run_manifest.json`, `seal.json` when `job_state` has `workspace_path` or `project_id`. |
| Path extraction | Embedded paths inside issue strings (e.g. `error in src/foo.tsx`) are picked up via regex in `proof_index.py`. |

**Tests** — `backend/tests/test_proof_index.py`.

### 6. GitHub OAuth (login)

| Route | Purpose |
|-------|---------|
| `GET /api/auth/github` | Redirects to GitHub authorize (or mock when `GITHUB_CLIENT_ID` unset / `mock*` prefix — dev parity with Google mock). |
| `GET /api/auth/github/callback` | Exchanges `code`, loads GitHub user + email, creates/finds Mongo user, redirects to `FRONTEND_URL` or backend-derived origin with `?token=<jwt>`. |

**CSRF** — `/api/auth/github` and `/api/auth/github/callback` added to exempt list (same class as Google).

**Environment (production)**

- `GITHUB_CLIENT_ID` — GitHub OAuth App client ID  
- `GITHUB_CLIENT_SECRET` — client secret  
- `GITHUB_REDIRECT_URI` — optional; if unset, defaults to `{BACKEND_PUBLIC_URL or request}/api/auth/github/callback` (must match GitHub OAuth App “Authorization callback URL”).

**Planner env hints** — `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` included in `_orchestrator_planner_project_state` “configured” hints (same pattern as Google).

---

## What remains (phased — from your approved plan)

| Phase | Deliverable | Notes |
|-------|----------------|-------|
| P1 | `artifact_delta` on **every** step completion (executor → `append_job_event`) | Still optional after P2; telemetry-first is deprioritized per founder note. |
| P2 | `WorkspaceAssemblyPipeline` (v1) | **Shipped** behind `CRUCIBAI_ASSEMBLY_V2`: File Tool + swarm hooks; last-writer merge; path-tagged fences; preview contract overlay. **Still to deepen:** richer parse (JSON file maps), explicit owner table, non-Vite profiles. |
| P3 | Thin legacy shim / remove duplicate writes | Optional cleanup once V2 is default in prod. |
| P4 | `stack_contract` / profile drives `select_agents_for_goal` + directory contract tests | Golden tests per profile. |
| P5 | Proof index ↔ `artifact_manifest` paths | **Shipped (v1):** `META/proof_index.json` on seal + `get_proof.proof_index` + ProofPanel strip. **Deeper:** enrich more verifier payloads with explicit paths; link `proof_bundle_generator` on-disk bundles. |
| P6 | Single canonical export story | Keep `/projects/.../zip` if needed; document which is “ownership” vs deploy. |
| P7 | Orphan DAG agents | Wire artifact/state/tool **or** remove from default selection — use `not_fully_integrated_agent` count in `agent_audit.json` as backlog input. |

---

## IDE / GitHub / deploy (already in repo — do not duplicate blindly)

- **VS Code + Cursor:** `ide-extensions/vscode/` (same VSIX for Cursor). Calls `/api/generate`, `/api/fix`, etc. — **not** the full Auto-Runner DAG unless you add routes.  
- **JetBrains:** `ide-extensions/jetbrains/` — partial plugin surface (verify build before marketplace claims).  
- **Git import / PAT push:** Dashboard GitHub URL import; Settings PAT; `POST /api/git-sync/push` — unchanged, still the path for **repo push** vs **OAuth login**.

---

## Success criteria for “this slice is done”

1. CI **agent-dag-audit** green.  
2. A completed Auto-Runner job leaves `META/*.json` on disk.  
3. `GET /api/jobs/{id}/export/full.zip` returns a zip for that job’s project workspace.  
4. “Continue with GitHub” hits live `/api/auth/github` with configured OAuth app.  
5. With **`CRUCIBAI_ASSEMBLY_V2=1`**, File Tool + swarm runs materialize **multi-file** path-tagged output into the workspace and still pass preview contract fill.

---

## Support / ops checklist

- [ ] Create GitHub OAuth App; set callback to production `/api/auth/github/callback`.  
- [ ] Set `GITHUB_CLIENT_ID` + `GITHUB_CLIENT_SECRET` on Railway (or host).  
- [ ] Confirm `FRONTEND_URL` / `BACKEND_PUBLIC_URL` alignment for redirects.  
- [ ] Optionally add frontend download button calling `/api/jobs/{jobId}/export/full.zip`.

---

*Generated as part of the approved implementation batch. Extend this file as later phases land.*
