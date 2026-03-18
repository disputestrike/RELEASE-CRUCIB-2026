# Railway Deploy (Git push) — What You Need

When you push to Git and deploy to Railway, use this checklist so the app works in production.

---

## 1. Backend service (Railway)

- **Build:** Use the repo **Dockerfile** (backend + frontend static in one image, or configure Railway to use the Dockerfile for the backend service).
- **Start:** Railway runs `uvicorn server:app --host 0.0.0.0 --port $PORT`. No extra step.
- **Migrations:** The backend runs **PostgreSQL migrations on startup** (`backend/db_pg.run_migrations()` → `001_full_schema.sql`). No separate migration job needed.

### Required variables (Railway → Backend service → Variables)

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | **Yes** | Postgres connection string. Add **Postgres plugin** in Railway and reference `DATABASE_URL` (Railway sets it automatically), or use an external Postgres URL. |
| `JWT_SECRET` | **Yes** | Long random string (e.g. `openssl rand -hex 32`). |
| `CORS_ORIGINS` | **Yes** (prod) | Your frontend URL, e.g. `https://your-app.up.railway.app` or your custom domain. Comma-separated if multiple. |
| `FRONTEND_URL` | Recommended | Same as frontend origin (for auth redirects, emails). |

Optional: `ANTHROPIC_API_KEY` or `CEREBRAS_API_KEY` for AI builds; `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` for payments.

---

## 2. Frontend (static or separate service)

- If the **same Dockerfile** serves both API and frontend static (current root Dockerfile), the frontend is built with **`REACT_APP_BACKEND_URL=`** (empty), so it uses **same-origin** `/api`. One Railway service = one URL; no extra config.
- If you deploy the **frontend as a separate service** (e.g. Vercel, or Railway static), set at **build time**:
  - **`REACT_APP_BACKEND_URL=https://your-backend.railway.app`** (no trailing slash)  
  so the built app sends API requests to your backend. Otherwise the browser would call `/api` on the frontend origin and get 404.

---

## 3. Summary

| Concern | What we did |
|--------|-------------|
| **Local "Disconnected"** | Backend must run on **port 8000**. Use `docker-compose up -d` or `python run_local.py` in `backend/`. Frontend proxy sends `/api` and `/health` to 8000. See **RUN_LOCAL.md**. |
| **Docker for local** | **docker-compose.yml** runs backend + Postgres. Exposes backend on **8000**. Run frontend on host; proxy connects to 8000. |
| **Railway migrations** | Backend runs **001_full_schema.sql** on startup when `DATABASE_URL` is set. No separate migration step. |
| **Railway env** | Backend needs `DATABASE_URL` (Postgres), `JWT_SECRET`, `CORS_ORIGINS`, `FRONTEND_URL`. |
| **Frontend on Railway** | If same service as backend: no `REACT_APP_BACKEND_URL`. If separate: set `REACT_APP_BACKEND_URL` to backend URL at build time. |

---

## 4. Quick Railway backend checklist

1. Add **Postgres** plugin (or attach external Postgres) → `DATABASE_URL` set.
2. Set **JWT_SECRET**, **CORS_ORIGINS**, **FRONTEND_URL**.
3. Deploy from Git; backend starts and runs migrations automatically.
4. If frontend is separate, build it with **REACT_APP_BACKEND_URL** = your backend’s public URL.
