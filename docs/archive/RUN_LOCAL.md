# Run CrucibAI on Local

Get the app running on your machine with **frontend + backend connected**.

## Why "Disconnected" or "Backend not available"?

The frontend at **http://localhost:3000** sends `/api` and `/health` requests to **http://localhost:8000** (via the dev-server proxy). If nothing is running on port 8000, you get "Disconnected". **Start the backend** using Option A (Docker) or Option B (Python) below.

---

## Option A — Backend with Docker

1. **Start backend + Postgres:** `docker-compose up -d`
2. **Start frontend on host:** `cd frontend && npm install && npm start`
3. Open **http://localhost:3000** — proxy will connect to backend on 8000.

Backend-only (you have your own Postgres): set `DATABASE_URL` in `.env`, then `docker-compose up -d backend`.

---

## Option B — Quick start (2 terminals)

### Terminal 1 — Backend (port 8000)

```powershell
cd backend
# Optional: copy .env.example to .env and set JWT_SECRET + DATABASE_URL for full auth/builds.
# To only get "Connected" and UI working, you can run without .env:
$env:CRUCIBAI_DEV = "1"
python run_local.py
```

- With **no `.env`**: backend starts with dev defaults. `/api/health` works (frontend shows ● Connected). Auth and AI builds will fail until you set `DATABASE_URL` and optionally `JWT_SECRET` in `.env`.
- With **`.env`** (copy from `.env.example`): set `JWT_SECRET` and `DATABASE_URL` (e.g. local Postgres or Docker Postgres). Then auth, guest, and AI builds work.

### Terminal 2 — Frontend (port 3000)

```powershell
cd frontend
npm install
npm start
```

- The frontend **proxies `/api` to http://localhost:8000**, so you don’t set any backend URL. Open **http://localhost:3000**.

## What runs where

| Service   | URL                | Command / note                    |
|----------|--------------------|------------------------------------|
| Frontend | http://localhost:3000 | `npm start` in `frontend/`        |
| Backend  | http://localhost:8000 | `python run_local.py` in `backend/` |

## Full local (auth + builds)

1. **Backend `.env`** (in `backend/`):
   - `JWT_SECRET` — any long random string for dev.
   - `DATABASE_URL` — e.g. `postgresql://user:pass@localhost:5432/crucibai` (or Docker Postgres).
   - Optional: `CEREBRAS_API_KEY` or `ANTHROPIC_API_KEY` for AI builds.

2. **Start backend** (with `.env` in place):
   ```powershell
   cd backend
   python run_local.py
   ```

3. **Start frontend** (same as above):
   ```powershell
   cd frontend
   npm start
   ```

4. Open **http://localhost:3000** — you should see ● Connected and be able to sign in and run builds (if DB and LLM keys are set).

## Troubleshooting

- **"Backend not available" / "Disconnected"**  
  Backend must be running on port 8000 before or while you use the frontend. Start `python run_local.py` in `backend/` first.

- **Backend won’t start: "FATAL: JWT_SECRET not set"**  
  Either set `JWT_SECRET` in `backend/.env`, or run with `$env:CRUCIBAI_DEV = "1"` so the server uses a dev default.

- **Backend won’t start: "FATAL: DATABASE_URL not set"**  
  Either set `DATABASE_URL` in `backend/.env`, or run with `$env:CRUCIBAI_DEV = "1"` so the server starts without a DB (only `/api/health` and UI connection work).

- **Port 8000 or 3000 in use**  
  Stop the other process using that port, or change the backend port in `run_local.py` and the proxy in `frontend/craco.config.js` to match.

- **Docker: backend exits or unhealthy**  
  Run `docker-compose logs backend`. Ensure Postgres is up if using compose DB: `docker-compose ps`. If using an external DB, set `DATABASE_URL` and run only `docker-compose up -d backend`.

- **Docker: backend exits or unhealthy**  
  Run `docker-compose logs backend`. Ensure Postgres is up if using compose DB: `docker-compose ps`. If using an external DB, set `DATABASE_URL` and run only `docker-compose up -d backend`.
