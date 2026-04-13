# Backend–Frontend Connection Analysis

**Purpose:** How the frontend connects to the backend, endpoint map, and how to fix "Backend unavailable".

---

## 1. How the connection works

| Piece | Where | Value |
|-------|--------|--------|
| **Backend URL** | Frontend: `frontend/.env` | `REACT_APP_BACKEND_URL` (default `http://localhost:8000`) |
| **API base** | Frontend: `App.js` | `export const API = \`${BACKEND_URL}/api\`` |
| **All API calls** | Frontend pages | `axios.get(\`${API}/health\`)`, `axios.post(\`${API}/build/plan\`, ...)` etc. |
| **Backend prefix** | Backend: `server.py` | `api_router = APIRouter(prefix="/api")` → all routes under `/api/*` |
| **CORS** | Backend: `server.py` | `allow_origins=os.environ.get('CORS_ORIGINS', '*').split(',')` → default `*` (all origins) |

So: **frontend at http://localhost:3000** calls **http://localhost:8000/api/...**. Both must be running.

---

## 2. Why "Backend unavailable" appears

The **Layout** component (sidebar app shell) does a **health check** on load:

- `GET http://localhost:8000/api/health` (or whatever `REACT_APP_BACKEND_URL` is).
- If it **fails** (network error, timeout, CORS, or backend not running) → footer shows **"Backend unavailable"**.

Common causes:

1. **Backend not running** — Start it: `cd backend && python -m uvicorn server:app --host 127.0.0.1 --port 8000`.
2. **Wrong port** — Backend on 8001 but frontend expects 8000 → set `REACT_APP_BACKEND_URL=http://localhost:8001` in `frontend/.env` and restart `npm start`.
3. **Wrong host** — Backend bound to `127.0.0.1` only; frontend from another machine → use `--host 0.0.0.0` and set `REACT_APP_BACKEND_URL` to that machine’s URL.
4. **CORS** — If you set `CORS_ORIGINS` in `backend/.env`, include the frontend origin (e.g. `http://localhost:3000`). Default `*` allows all.
5. **First load** — Health check runs once; if backend wasn’t up then, click **Retry** in the footer (added below) or refresh the page.

---

## 3. Endpoint map (frontend → backend)

| Frontend call | Backend route | File(s) |
|---------------|--------------|---------|
| `GET ${API}/health` | `GET /api/health` | Layout.jsx, RUN.md |
| `GET ${API}/auth/me` | `GET /api/auth/me` | App.js |
| `POST ${API}/auth/login` | `POST /api/auth/login` | App.js |
| `POST ${API}/auth/register` | `POST /api/auth/register` | App.js |
| `GET ${API}/build/phases` | `GET /api/build/phases` | Workspace.jsx |
| `POST ${API}/build/plan` | `POST /api/build/plan` | Workspace.jsx |
| `GET ${API}/projects` | `GET /api/projects` | Dashboard, AgentMonitor |
| `GET ${API}/projects/:id` | `GET /api/projects/{project_id}` | AgentMonitor, BuildProgress |
| `POST ${API}/projects/:id/retry-phase` | `POST /api/projects/{project_id}/retry-phase` | AgentMonitor.jsx |
| `GET ${API}/agents/status/:id` | `GET /api/agents/status/{project_id}` | AgentMonitor.jsx |
| `GET ${API}/projects/:id/phases` | `GET /api/projects/{project_id}/phases` | AgentMonitor.jsx |
| `GET ${API}/examples` | `GET /api/examples` | LandingPage, ExamplesGallery |
| `POST ${API}/examples/:name/fork` | `POST /api/examples/{name}/fork` | ExamplesGallery.jsx |
| `POST ${API}/voice/transcribe` | `POST /api/voice/transcribe` | Workspace, LandingPage |
| `GET ${API}/workspace/env` | `GET /api/workspace/env` | Settings, EnvPanel |
| `POST ${API}/workspace/env` | `POST /api/workspace/env` | Settings, EnvPanel |
| `GET ${API}/dashboard/stats` | `GET /api/dashboard/stats` | Dashboard.jsx |
| WebSocket progress | `WS /ws/projects/{project_id}/progress` | BuildProgress.jsx (wsUrl from apiBaseUrl) |

All backend routes are under the **api_router** prefix `/api`; the WebSocket is on the **app** at `/ws/projects/...` (no `/api`).

---

## 4. Click-through checklist (manual test)

1. **Backend running** — `curl http://localhost:8000/api/health` → `{"status":"healthy",...}`.
2. **Frontend running** — Open http://localhost:3000.
3. **Layout footer** — Should show "Backend connected". If not, click **Retry** or fix backend/URL.
4. **Landing** — "See What CrucibAI Built" loads examples from `/api/examples` (backend must be up).
5. **Sign in** — Register or login uses `/api/auth/register`, `/api/auth/login`; then `/api/auth/me`.
6. **Dashboard** — Loads `/api/projects` and `/api/dashboard/stats`.
7. **New project** — `POST /api/projects` then redirect to AgentMonitor.
8. **AgentMonitor** — Loads project, agents/status, logs, phases; WebSocket for progress.
9. **Workspace** — Build uses `/api/build/plan`; voice uses `/api/voice/transcribe`; tools use `/api/ai/...`, `/api/export/...`.
10. **Settings** — Load/save env via `/api/workspace/env`.

---

## 5. Quick fix summary

| Problem | Fix |
|--------|-----|
| Backend unavailable (footer) | Start backend on port 8000; or set `REACT_APP_BACKEND_URL` and restart frontend. Click **Retry** in footer. |
| CORS errors in console | Backend: keep `CORS_ORIGINS` unset (default `*`) or set to `http://localhost:3000`. |
| 404 on /api/... | Backend must be running; path must be exactly `/api/...` (backend uses prefix `/api`). |
| WebSocket fails | BuildProgress uses `apiBaseUrl` = API without `/api`; wsUrl = `ws://localhost:8000/ws/projects/:id/progress`. Ensure backend URL and WebSocket path match. |

---

**Last updated:** February 2026
