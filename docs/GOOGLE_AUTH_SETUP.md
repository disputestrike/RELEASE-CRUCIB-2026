# Google OAuth (Sign in with Google) — Setup & Flow

This doc describes **how CrucibAI implements** Google Auth: sign up, sign in, and what you need to configure so it works. Use this as the single source of truth; do not rely on other repos’ Google Auth setup.

---

**Checkpoint (bring forward):** This is **our** flow only. Backend: one token exchange at `oauth2.googleapis.com/token`, verify with `google.oauth2.id_token.verify_oauth2_token`, redirect to `{FRONTEND_URL}/auth?token=...`. Do not import or use another project's Google OAuth. Keep FRONTEND_URL and BACKEND_PUBLIC_URL as the single source for redirect targets.

---

## 1. What we use

- **Backend:** OAuth 2.0 **authorization code** flow (server-side).
- **Google endpoints:**  
  - Authorize: `https://accounts.google.com/o/oauth2/v2/auth`  
  - Token: `https://oauth2.googleapis.com/token`
- **Libraries:**  
  - `httpx` (or similar) for token exchange (POST with `code`).  
  - `google-auth` (Python) to **verify the ID token** with Google’s public keys (no `verify_signature: False`).
- **Our API routes:**  
  - `GET /api/auth/google` — redirects user to Google consent.  
  - `GET /api/auth/google/callback` — receives `code`, exchanges for tokens, verifies ID token, creates/ finds user, issues our JWT, redirects to frontend with `?token=...`.

---

## 2. Google Cloud setup (one-time)

1. **Create or select a project**  
   - Go to [Google Cloud Console](https://console.cloud.google.com/) → select or create a project.

2. **Enable the OAuth APIs**  
   - APIs & Services → Library → search **“Google+ API”** or **“Google Identity”** (or ensure **OAuth consent screen** is configured).  
   - For “Sign in with Google” you need the **OAuth 2.0 Client ID**; the consent screen is required to create it.

3. **Configure OAuth consent screen**  
   - APIs & Services → **OAuth consent screen**.  
   - Choose **External** (or Internal for workspace-only).  
   - Fill App name, User support email, Developer contact.  
   - Scopes: add `openid`, `email`, `profile` (we use `openid email profile` in the authorize URL).  
   - Save.

4. **Create OAuth 2.0 credentials**  
   - APIs & Services → **Credentials** → **Create credentials** → **OAuth client ID**.  
   - Application type: **Web application**.  
   - Name: e.g. “CrucibAI Web”.  
   - **Authorized redirect URIs:** add your callback URL(s). **The value must match exactly** what the app sends.  
     - Local: `http://localhost:8000/api/auth/google/callback`  
     - **Railway:** `https://crucibai-production.up.railway.app/api/auth/google/callback` (if you see `Error 400: redirect_uri_mismatch`, add this exact URI here).  
     - Other production: `https://your-api-domain.com/api/auth/google/callback`  
   - Create → copy **Client ID** and **Client secret**.

5. **Env vars (backend)**  
   Set these where the backend runs (e.g. `.env` or Railway):

   - `GOOGLE_CLIENT_ID` = Client ID from step 4.  
   - `GOOGLE_CLIENT_SECRET` = Client secret from step 4.  
   - `FRONTEND_URL` = where the React app lives (e.g. `http://localhost:3000` or `https://app.crucibai.com`).  
     - Used to redirect after login: `{FRONTEND_URL}/auth?token=...`.  
   - **`BACKEND_PUBLIC_URL`** (recommended for production): The public URL of the backend (e.g. `https://crucibai-production.up.railway.app`).  
     - Ensures the OAuth callback URL sent to Google uses **HTTPS**; without it, the app may send `http://` and cause `redirect_uri_mismatch` or require you to register `http://` in Google (insecure).

---

## 3. Sign-in flow (what actually happens)

1. **User clicks “Sign in with Google”**  
   - Frontend sends the user to:  
     `GET {BACKEND_URL}/api/auth/google?redirect=/dashboard`  
   - Optional `redirect` is where to send the user after login (e.g. `/dashboard`).

2. **Backend → Google**  
   - Backend responds with **302** to:  
     `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=openid+email+profile&access_type=offline&prompt=consent`  
   - `redirect_uri` is **our** callback, e.g. `https://api.example.com/api/auth/google/callback`.

3. **User signs in at Google**  
   - User logs in (if needed) and consents.  
   - Google redirects to our callback with:  
     `?code=...&state=...`  
   - `state` is our own payload (e.g. base64 JSON with `redirect` path) for restoring the post-login redirect.

4. **Backend callback**  
   - Backend receives `code` (and optionally `state`).  
   - **Token exchange:** POST to `https://oauth2.googleapis.com/token` with `code`, `client_id`, `client_secret`, `grant_type=authorization_code`, `redirect_uri` (same as in step 2).  
   - Response contains `id_token` (and often `access_token`).  
   - **Verify ID token:** use `google.oauth2.id_token.verify_oauth2_token(id_token, request, GOOGLE_CLIENT_ID)`.  
     - Do **not** use `jwt.decode(..., verify_signature=False)`; that is insecure.  
   - From verified payload: `email`, `name` (or `given_name`), etc.  
   - **Create or get user:** find by `email`; if missing, create user (and e.g. ledger entry), set `auth_provider: "google"`.  
   - **Our JWT:** issue a CrucibAI JWT (e.g. `create_token(user["id"])`).  
   - **Redirect:**  
     `302` to `{FRONTEND_URL}/auth?token={our_jwt}&redirect=/dashboard`  
     (if `state` contained `redirect=/dashboard`).

5. **Frontend**  
   - Frontend route `/auth` reads `token` from query, stores it (e.g. in memory or localStorage), then redirects to `redirect` or default (e.g. dashboard).  
   - Subsequent API calls send `Authorization: Bearer {token}`.

---

## 4. Sign up vs sign in

- We **do not** have a separate “Google sign up” endpoint.  
- **First time** a Google email is seen: we **create** a user (sign up).  
- **Next times:** we **find** the user by email and log them in (sign in).  
- Distinction is “user exists by email?” → sign in; else create user + sign in.

---

## 5. Why it might not work elsewhere

- **Wrong redirect_uri:** Google only accepts URIs listed in the OAuth client. If the backend URL or path changes, add the new callback URL in the Cloud Console.  
- **ID token not verified:** If another implementation uses `jwt.decode(..., verify_signature=False)`, Google can change token format or you might accept tampered tokens; our flow uses `google-auth` to verify.  
- **Missing env vars:** No `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` → backend returns 503 “Google sign-in is not configured”.  
- **CORS / FRONTEND_URL:** If `FRONTEND_URL` is wrong, the browser is sent to the wrong origin after login; set it to the exact frontend origin (e.g. `https://app.example.com`).  
- **Credentials in a different project:** Client ID and secret must be from the same OAuth client and the same Google Cloud project.

---

## 6. Checklist

- [ ] Google Cloud project created.  
- [ ] OAuth consent screen configured (External/Internal, scopes `openid`, `email`, `profile`).  
- [ ] OAuth 2.0 Web client created; **Authorized redirect URIs** includes `{BACKEND_URL}/api/auth/google/callback`.  
- [ ] `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` set in backend env.  
- [ ] `FRONTEND_URL` set to frontend origin (no trailing slash).  
- [ ] Backend uses **verified** ID token (e.g. `google.oauth2.id_token.verify_oauth2_token`), not unverified decode.  
- [ ] Frontend “Sign in with Google” links to `GET {BACKEND}/api/auth/google?redirect=...`.  
- [ ] Frontend `/auth` page reads `token` (and optional `redirect`) from query and stores token, then redirects.

Using this process and our backend implementation, Google Auth will behave consistently across environments. When you pull from git, keep using **this** flow and **this** setup; do not replace it with another repo’s Google Auth implementation.
