# Run CrucibAI locally and test everything

## Quick start (two terminals)

### 1. Backend (port 8000)

```bash
cd backend
# Optional: set env if you don't have .env
# set MONGO_URL=mongodb://localhost:27017
# set JWT_SECRET=your-secret
# set DB_NAME=crucibai
python run_local.py
```

Backend will be at **http://localhost:8000**.  
Health: **http://localhost:8000/api/health**

### 2. Frontend (port 3000)

```bash
cd frontend
npm start
```

Frontend will open at **http://localhost:3000**.  
It talks to the API at `http://localhost:8000/api` by default.

---

## URLs to test (local)

| What | URL |
|------|-----|
| **App home** | http://localhost:3000 |
| **Login / Register** | http://localhost:3000/login |
| **Dashboard** | http://localhost:3000/app |
| **IDE (Unified – all 8 tabs)** | http://localhost:3000/app/ide |
| **VibeCode** | http://localhost:3000/app/vibecode |
| **Monitoring** | http://localhost:3000/app/monitoring |
| **Settings** | http://localhost:3000/app/settings |
| **Backend health** | http://localhost:8000/api/health |

---

## IDE tab checklist (http://localhost:3000/app/ide)

1. **Terminal** – Create session (path or project ID), run command, see output.
2. **Git** – Get status, list branches, merge, commit, resolve conflict.
3. **VibeCode** – Analyze text, generate code.
4. **Debug** – Start debug session, add/remove breakpoints.
5. **Lint** – Run lint (project_id / code).
6. **Profiler** – Start/stop profiler.
7. **AI Features** – Generate tests, security scan, optimize, generate docs.
8. **Ecosystem** – VS Code config, get extension code.

---

## Backend API (examples)

- `GET  /api/health`
- `GET  /api/git/status?repo_path=.`
- `GET  /api/git/branches?repo_path=.`
- `POST /api/vibecoding/analyze` — body: `{"text": "Build a todo app"}`
- `POST /api/vibecoding/generate` — body: `{"prompt": "hello component"}`
- `POST /api/terminal/create` — params: `project_path=.`
- `POST /api/ide/debug/start` — params: `project_id=test`
- `POST /api/monitoring/events/track` — body: `{"event_type":"test","user_id":"u1","success":true}`
- `GET  /api/monitoring/events?limit=5`
- `POST /api/ai/docs/generate` — body: `{"project_name":"Test","description":"A test"}`
- `POST /api/deploy/validate` — body: `{"platform":"vercel","files":{}}`
- `POST /api/cache/invalidate`

---

## Smoke tests (backend)

```bash
cd backend
set MONGO_URL=mongodb://localhost:27017
set JWT_SECRET=proof
set DB_NAME=crucibai
python -m pytest tests/test_smoke.py -v
```

All 20 tests should pass.
