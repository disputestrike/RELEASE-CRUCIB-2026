# Backend, Database & Login Checklist

Use this to confirm the backend is there, tables exist, admin is wired, and why Google sign-in might loop back to the login page.

---

## 1. Do we have a backend?

**Yes.** The app has a FastAPI backend in `backend/server.py`:

- **Auth:** `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/google`, `/api/auth/google/callback`
- **Health:** `/api/health`
- **Admin:** `/api/admin/dashboard`, `/api/admin/users`, `/api/admin/analytics/*`, etc.
- **Projects, tokens, Stripe, AI, etc.** — all under `/api/*`

On **Railway** (or your host), the backend must be running and reachable at the URL you use for API calls. If the frontend is on a different domain (e.g. Vercel + Railway), that URL must be set in the frontend build (see below).

---

## 2. Database and tables

**Yes.** The backend uses **PostgreSQL** via `backend/db_pg.py` (Motor-like API: `db.users.find_one`, `db.users.insert_one`, etc.). Tables are created on first use (e.g. `users`, `projects`, `token_ledger`, `api_keys`, etc.) with a `doc` JSONB column per collection.

- **Required env:** `DATABASE_URL` (Postgres connection string). If this is missing or wrong, the server will fail to start or all auth/DB calls will 500.
- **Railway:** Attach a Postgres plugin or set `DATABASE_URL` in Variables. The backend does **not** use MongoDB; it uses Postgres only.

So: **we have the tables we need for login.** User records are stored in the `users` table (via the `users` collection in `db_pg`). Google callback creates/finds the user there and then issues a JWT; `/api/auth/me` looks up the user by that JWT.

---

## 3. Admin panels

**Yes.** Admin is wired to the same backend and DB:

- **Frontend routes:** `/app/admin`, `/app/admin/users`, `/app/admin/users/:id`, `/app/admin/billing`, `/app/admin/analytics`, `/app/admin/legal` (see `App.js` → AdminRoute, AdminDashboard, AdminUsers, etc.).
- **Backend:** `GET /api/admin/dashboard`, `GET /api/admin/users`, `GET /api/admin/users/{user_id}`, `POST /api/admin/users/{user_id}/grant-credits`, analytics, etc. All use the same `get_current_user` + `get_current_admin` and same `db` (Postgres).

Admin uses the same JWT and same database as normal login; no separate “admin DB”.

---

## 4. Why does Google sign-in loop back to the login page?

Common causes:

| Cause | What happens | Fix |
|-------|----------------|-----|
| **Frontend and backend on different hosts** | “Sign in with Google” used to go to relative `/api/auth/google`, so the browser hit the **frontend** host (e.g. Vercel). That host doesn’t have the callback, so OAuth never reached the backend. | **Fixed in code:** AuthPage now uses the **backend** URL for OAuth when `REACT_APP_BACKEND_URL` is set. Rebuild the frontend with `REACT_APP_BACKEND_URL=https://your-backend.railway.app` (or your real backend URL). |
| **Backend not reachable** | After Google, backend redirects to `FRONTEND_URL/auth?token=...`. Frontend then calls `GET /api/auth/me` with that token. If that request goes to the wrong host (e.g. localhost) or the backend is down, the call fails and the user stays on the login page. | Ensure the frontend build has the correct API base: **same-origin deploy:** build with `REACT_APP_BACKEND_URL=` (empty). **Split deploy:** set `REACT_APP_BACKEND_URL` to the backend URL and rebuild. |
| **Redirect URI mismatch** | Google returns `redirect_uri_mismatch`; backend then redirects to `/auth?error=google_failed` and the user sees the form again. | In Google Cloud Console → Credentials → your OAuth client → **Authorized redirect URIs**, add the **exact** callback URL: `https://your-backend-domain.com/api/auth/google/callback` (same as `BACKEND_PUBLIC_URL` or what the backend uses). See `docs/GOOGLE_AUTH_SETUP.md`. |
| **Missing or wrong env on backend** | `JWT_SECRET`, `FRONTEND_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `DATABASE_URL` must be set correctly on the server. | Set them in Railway (or your host) Variables. Restart the backend after changing. |
| **DB not connected** | If `DATABASE_URL` is wrong or Postgres is down, `db` is `None` and auth endpoints return 500. | Check Railway Postgres and `DATABASE_URL`; check backend logs for “PostgreSQL pool failed” or “NoneType … users”. |

---

## 5. Quick production checklist

- [ ] **Backend** running and reachable at the URL you expect (e.g. `https://your-app.up.railway.app`).
- [ ] **DATABASE_URL** set and Postgres reachable (no “password authentication failed” or “pool failed” in logs).
- [ ] **JWT_SECRET**, **FRONTEND_URL**, **GOOGLE_CLIENT_ID**, **GOOGLE_CLIENT_SECRET** set on the backend (and **BACKEND_PUBLIC_URL** if you use it for OAuth redirect).
- [ ] **Google Console:** Authorized redirect URI = `https://<your-backend-domain>/api/auth/google/callback`.
- [ ] **Frontend build:**  
  - **Single URL (frontend + backend same origin):** build with `REACT_APP_BACKEND_URL=` so API is relative `/api`.  
  - **Frontend and backend on different origins:** build with `REACT_APP_BACKEND_URL=https://your-backend-domain.com` so OAuth and `/auth/me` hit the backend.

After changing env or rebuilding, try Google sign-in again and, if it still loops, check backend logs for the “Google callback: …” lines to see whether the callback is succeeding or returning an error.

---

## 6. Everything on Railway (single app) — what to set

If your **entire app** (frontend + backend) is one Railway service:

1. **Build:** Use `REACT_APP_BACKEND_URL=` (empty) so the frontend uses relative `/api`. The Dockerfile already does this.
2. **Backend env vars on Railway (Variables):**
   - `DATABASE_URL` — from Railway Postgres (attach the DB to the service).
   - `JWT_SECRET` — a long random string (same every deploy).
   - `FRONTEND_URL` — your public URL, e.g. `https://crucibai-production.up.railway.app` (no trailing slash).
   - `BACKEND_PUBLIC_URL` — **same value** as `FRONTEND_URL` (so the OAuth callback URL is exactly that + `/api/auth/google/callback`).
   - `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` — from Google Cloud Console.
3. **Google Cloud Console → Credentials → your OAuth client → Authorized redirect URIs:** add exactly:
   - `https://crucibai-production.up.railway.app/api/auth/google/callback`  
   (or whatever your Railway URL is — must match `BACKEND_PUBLIC_URL` + `/api/auth/google/callback`).

If the loop continues after this, the backend is likely redirecting with `?error=...` (e.g. `google_failed` from token exchange). Railway logs for that request will show the reason.
