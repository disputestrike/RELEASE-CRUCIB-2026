# How to Run CrucibAI

---

## Your local URLs

| What        | URL |
|------------|-----|
| **App (open this)** | **http://localhost:3000** |
| Backend API        | http://localhost:8000    |
| API health check   | http://localhost:8000/api/health |

Start backend + frontend first (see below), then open **http://localhost:3000** in your browser.

---

## Docker: Postgres + Redis only (local dev)

If you use Docker Desktop, start databases first (backend + frontend still run on your machine):

```powershell
.\run-docker-deps.ps1
```

That runs `docker compose up -d postgres redis`. Postgres is on host **5434** and Redis on **6381** (avoids conflicts with other local Postgres/Redis on 5432/6379). Match **`backend/.env`**:

- `DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai`
- `REDIS_URL=redis://127.0.0.1:6381/0`

Optional: run the API inside Docker too (full image build):

```powershell
docker compose --profile container-api up -d --build
```

Then open the app at **http://localhost:3000** with `npm start` in `frontend` unless the image already serves static files on :8000.

---

## One command (Windows)

From the repo root in PowerShell:

```powershell
.\run-dev.ps1
```

This starts the backend in a new window and the frontend in the current terminal. Open **http://localhost:3000** when the frontend compiles. Start **`run-docker-deps.ps1`** first if your database is in Docker.

To check the local toolchain before starting the app:

```powershell
.\scripts\verify-local.ps1
```

The verifier checks Python, Node, npm, frontend dependencies, backend import in dev mode, and git status. It expects Node 18-22; Node 20 is recommended.

---

## Quick start (two terminals)

1. **Backend (API)** — in a terminal:
   ```powershell
   cd backend
   set CRUCIBAI_DEV=1
   python -m uvicorn server:app --host 127.0.0.1 --port 8000
   ```
   **`CRUCIBAI_DEV=1`** turns off global API rate limiting so local dev does not hit **429** on `/api/auth/me` and other calls. You can also add `CRUCIBAI_DEV=1` to `backend/.env`.  
   In **PowerShell** (same effect): `$env:CRUCIBAI_DEV = "1"` before `python -m uvicorn ...`.  
   Requires: **PostgreSQL** and `DATABASE_URL` in `backend/.env` (unless you only need `/api/health` with `CRUCIBAI_DEV=1`).

2. **Frontend** — in another terminal:
   ```powershell
   cd frontend
   npm start
   ```
   Opens at **http://localhost:3000**.

3. **Open in browser:** http://localhost:3000

---

## If something isn’t working

- **“localhost refused to connect”**  
  - **Open the full URL:** **http://localhost:3000** (frontend) or **http://localhost:8000** (backend). Do not use `http://localhost` alone (nothing runs on port 80).  
  - Make sure you started both the backend and frontend (two terminals), or run **`.\run-dev.ps1`** from the repo root (PowerShell).

- **“Something is already running on port 3000”**  
  - A dev server is probably already running. Open **http://localhost:3000**.  
  - To restart: close the other terminal or stop the process using port 3000, then run `npm start` again in `frontend`.

- **“Port 8000 already in use”**  
  - Backend may already be running. Try **http://localhost:8000/api/health**.  
  - To use another port:  
    `python -m uvicorn server:app --host 127.0.0.1 --port 8001`  
    Then in `frontend/.env` set:  
    `REACT_APP_BACKEND_URL=http://localhost:8001`

- **Frontend fails with `ajv` or ESLint / "defaultMeta" / html-webpack-plugin errors**  
  - Postinstall patches disable the ESLint webpack plugin in `react-scripts`.  
  - If you still see the error: **re-run the patch and clear cache**, then start again:
    ```powershell
    cd frontend
    node scripts/patch-ajv-formats.js
    rmdir /s /q node_modules\.cache 2>nul
    npm start
    ```
  - Recommended: **Node 18 or 20 LTS** (see `frontend/.nvmrc`).

- **"Backend unavailable" in the app footer**  
  - Backend must be running at the URL in `REACT_APP_BACKEND_URL` (default `http://localhost:8000`).  
  - Click **Retry** in the footer to re-check, or restart the backend and refresh.  
  - See **BACKEND_FRONTEND_CONNECTION.md** for full connection analysis and endpoint map.

- **Backend won’t start (e.g. DATABASE_URL)**  
  - Copy `backend/.env.example` to `backend/.env` and set at least:
    - `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/crucibai` (PostgreSQL only)
    - `JWT_SECRET` (any random string in dev; required in production)
