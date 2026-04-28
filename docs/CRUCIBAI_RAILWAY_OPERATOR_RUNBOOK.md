# CrucibAI — Railway / production operator runbook (control plane)

Use this after deploy to close the **post-deploy** gates in `CRUCIBAI_CONTROL_PLANE_IMPLEMENTATION.md` §4. All paths assume the API is served at **`https://<host>/api`** (same as the app’s `API_BASE`).

---

## 0. Logs you may see (what they mean)

- **`get_projects: pg query failed: column "doc" does not exist`** — fixed in app by `ALTER TABLE projects ADD COLUMN ... doc` + a corrected jobs fallback. Redeploy backend; the warning should stop after deploy.
- **`GET .../dev-preview` → `202`** — no `index.html` in the job workspace yet (build still writing files, or output path differs). Preview iframe stays empty until this returns `200` with `dev_server_url`. Not a “lost UI” bug by itself.
- **Set `CRUCIBAI_PUBLIC_BASE_URL` or `BACKEND_PUBLIC_BASE_URL`** on Railway to your **this** service’s public origin (e.g. `https://vigilant-youth-production-5aa6.up.railway.app`) so when preview **is** ready, the iframe gets an absolute URL.
- **Tavily 432** — search quota; chat may still work via other tools. Optional: disable or upgrade Tavily in env.

---

## 1. Get `TOKEN` and `JOB_ID`

1. Log in to the app in the browser.
2. Open DevTools → **Application** → **Local storage** → copy `token`, **or** Network → any `GET /api/...` → Request headers → `Authorization: Bearer ...`.
3. Start a build from **Workspace** (`/app/workspace`) and copy `jobId` from the URL query string, **or** use `GET /api/jobs?limit=5` and pick a job `id`.

Set environment variables (bash):

```bash
export API="https://YOUR_RAILWAY_HOST/api"
export TOKEN="paste_jwt_here"
export JOB_ID="paste_job_id_here"
```

PowerShell:

```powershell
$env:API = "https://YOUR_RAILWAY_HOST/api"
$env:TOKEN = "paste_jwt_here"
$env:JOB_ID = "paste_job_id_here"
```

---

## 2. Gate A — Success path: job row + dev-preview

**Intent:** Confirm the job DTO and preview pipeline are populated when a build has produced a servable tree.

```bash
curl -sS -H "Authorization: Bearer $TOKEN" "$API/jobs/$JOB_ID" | head -c 2000
echo
curl -sS -H "Authorization: Bearer $TOKEN" "$API/jobs/$JOB_ID/dev-preview"
echo
```

**Pass when:**

- `GET /api/jobs/{id}` returns **200** and JSON includes useful status (`running`, `completed`, …) and, when the orchestrator has set it, preview-related fields (e.g. `dev_server_url` / `preview_url` / `published_url` — exact keys depend on deploy).
- `GET /api/jobs/{id}/dev-preview` returns **200** with `"status":"ready"` and a non-null `dev_server_url`, **or** **202** with `"status":"pending"` or `"building"` while the workspace still has no `index.html` yet ( honest mid-build state).

**If `dev-preview` is always 202 with no progression:** check Railway logs, workspace disk, and that the job actually writes files under the job workspace.

---

## 3. Gate B — Failed job: API still narrates the failure

**Intent:** Per control plane E5, a failed run must still return enough for the UI (`latestFailure`, `failure_reason`, etc.).

Run after you have a **failed** `JOB_ID` (e.g. force an invalid goal blocked by spec guardian, or a step that fails in your env).

```bash
curl -sS -H "Authorization: Bearer $TOKEN" "$API/jobs/$JOB_ID" | head -c 2500
echo
curl -sS -H "Authorization: Bearer $TOKEN" "$API/jobs/$JOB_ID/events?limit=50" | head -c 2000
echo
```

**Pass when:**

- Job JSON has `status` reflecting failure (e.g. `failed` / `cancelled` as appropriate).
- Prefer **`latest_failure`** non-empty when a checkpoint exists (per `GET /api/jobs/{id}` docstring in `jobs.py`).
- `GET /api/jobs/{id}/events` includes a **`job_failed`** (or other failure-related) event you can correlate.

Then in the **browser**: open `/app/workspace?jobId=...&taskId=...` for that job, **hard refresh** once — the failure callout / activity feed should not be blank (exact UI copy varies).

---

## 4. Optional — E6 transcript (already in main implementation doc)

See `CRUCIBAI_CONTROL_PLANE_IMPLEMENTATION.md` §7 steps 1–3 (`POST /transcript`, `GET /events`, UI refresh).

---

## 5. What you do not need to fix in code

If **Gate A** or **B** fail only on Railway but pass locally, treat it as **hosting** (env, DB, `CRUCIBAI_PUBLIC_BASE_URL` / `BACKEND_PUBLIC_URL` for absolute preview URLs, disk, build timeouts), not the control-plane React wiring.
