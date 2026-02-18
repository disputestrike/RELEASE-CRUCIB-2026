# Railway deploy – what’s in place (so we remember)

One URL serves the full CrucibAI site (frontend + API). Here’s what makes it work.

---

## 1. Single-URL deploy (frontend + backend in one image)

- **Dockerfile** is multi-stage:
  - **Stage 1 (frontend):** Node 20 Alpine. Copies `package.json`, lockfiles, **and `frontend/scripts`** (so postinstall `scripts/patch-ajv-formats.js` runs), then `yarn install` or `npm ci`, then rest of frontend, then `REACT_APP_BACKEND_URL=` and `yarn build` / `npm run build`. Output is in `build/`.
  - **Stage 2 (backend):** Python 3.11 slim. Installs backend deps, copies backend, copies **`/app/build` from stage 1 → `./static`**. Uvicorn runs `server:app`.
- **Backend** (`server.py`) mounts `StaticFiles` at `/` when `Path(__file__).parent / "static"` exists (so in Docker, `/` serves the React app; `html=True` gives SPA fallback for routes like `/features`, `/pricing`). API stays at `/api`, WebSocket at `/ws/...`, etc.
- **Frontend** uses relative `/api` when `REACT_APP_BACKEND_URL` is set to empty (set in Docker build), so the same Railway URL is used for both site and API (`App.js` and `GenerateContent.jsx` handle the empty-backend-url case).

So: **one Railway service → one URL → full website + API.**

---

## 2. Placeholder env for “test deploy” without MongoDB

- If **MONGO_URL** or **DB_NAME** are missing at startup, the app sets safe defaults (`mongodb://localhost:27017`, `crucibai`) and logs a warning so the container can start and you can confirm deploy/health. For real use, set real values in Railway Variables and redeploy.
- **JWT_SECRET** already had a per-process fallback in code; no change.

---

## 3. Railway-specific details

- **Start command:** In `railway.json`, `startCommand` is `sh -c 'uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}'` (no `cd`; Railway runs from the image workdir).
- **Variables (production):** Set `MONGO_URL`, `DB_NAME`, `JWT_SECRET` in Railway Dashboard → service → Variables. See `RAILWAY_QUICKSTART.md` and `RAILWAY_FIRST_DEPLOY.md`.
- **`.dockerignore`:** Excludes `frontend/node_modules`, `frontend/build`, `backend/__pycache__`, etc., so the build context stays small and we don’t reuse local build artifacts.

---

## 4. Critical Dockerfile detail (why `frontend/scripts` is copied early)

- Frontend has a **postinstall** script: `node scripts/patch-ajv-formats.js`. If we only copy `package.json` and lockfiles before `yarn install`, that script fails with “Cannot find module …/scripts/patch-ajv-formats.js”. So we **copy `frontend/scripts` before the install step**; then postinstall runs successfully and the build proceeds.

---

## 5. Quick reference

| What                    | Where / how |
|-------------------------|-------------|
| Frontend build in Docker| Dockerfile stage 1; output in `build/` |
| Frontend served at `/`  | `server.py`: `StaticFiles` on `./static` when it exists |
| API                     | Same host, `/api` (relative when `REACT_APP_BACKEND_URL=""`) |
| Placeholder DB env      | `server.py`: defaults for `MONGO_URL` / `DB_NAME` if unset |
| Postinstall needs scripts | Dockerfile: `COPY frontend/scripts ./scripts` before `yarn install` |

When something breaks on deploy, check: Variables set? Build logs for frontend (install + build)? Deploy logs for backend (Uvicorn + any FATAL/WARNING about env)?

---

## 6. Agents & Automation worker (optional second service)

- **What:** A separate process that runs scheduled agent runs (and legacy `automation_tasks`). It polls `user_agents` every 60s and executes due runs.
- **How to run:** From repo root (with backend on PYTHONPATH): `python -m backend.workers.automation_worker`. Same env as API: `MONGO_URL`, `DB_NAME`. For `run_agent` actions from the worker, set `CRUCIBAI_API_URL` (e.g. your Railway API URL) and `CRUCIBAI_INTERNAL_TOKEN` (random secret); the API must have the same token in `CRUCIBAI_INTERNAL_TOKEN` for `POST /api/agents/run-internal`.
- **Railway:** Add a second service that uses the same Dockerfile and set **Start Command** to `python -m backend.workers.automation_worker` (and same Variables as the API). Internal agents: set `SEED_INTERNAL_AGENTS=1` on the API service to seed 5 dogfooding agents on startup.
