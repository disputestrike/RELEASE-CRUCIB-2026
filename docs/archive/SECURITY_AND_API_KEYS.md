# Security, Abuse Prevention, and API Keys – Gaps and Checklist

**Purpose:** Ensure no abuse, code copy, or security concerns are missed. List all env/API keys and what is missing.

---

## 1. Environment variables and API keys (full list)

### 1.1 Backend (server.py) – required or optional

| Variable | Required? | Used for | If missing |
|----------|-----------|----------|------------|
| **MONGO_URL** | **Yes** | MongoDB connection | App fails at import (KeyError). |
| **DB_NAME** | **Yes** | MongoDB database name | App fails at import. |
| **OPENAI_API_KEY** | No (or user keys in Settings) | Chat, analyze, voice, image-to-code, validate-and-fix, many AI routes | AI endpoints return 503/500; message: "Add OPENAI_API_KEY in Settings or .env". |
| **LLM_API_KEY** | No | Fallback for OpenAI / Gemini | Same as OPENAI_API_KEY when used. |
| **ANTHROPIC_API_KEY** | No | Claude models | Claude fails; chain tries OpenAI then Gemini. |
| **GEMINI_API_KEY** or **GOOGLE_API_KEY** | No | Gemini models | Gemini fails; chain uses OpenAI/Anthropic. |
| **JWT_SECRET** | No (default set) | Signing JWTs | Default: `crucibai-secret-key-2024` – **must change in production**. |
| **CORS_ORIGINS** | No | Allowed origins | Default `*` – **tighten in production** (e.g. `https://yourapp.com`). |
| **FRONTEND_URL** | No | Stripe redirects, Google OAuth redirect | Default `http://localhost:3000`. |
| **STRIPE_SECRET_KEY** | No | Token checkout | Checkout returns 503 "Stripe not configured". |
| **STRIPE_WEBHOOK_SECRET** | No | Stripe webhook signature verification | Webhook returns 503. |
| **GOOGLE_CLIENT_ID** | No | Google OAuth login | Google sign-in returns 503. |
| **GOOGLE_CLIENT_SECRET** | No | Google OAuth token exchange | Callback fails. |

### 1.2 Frontend (App.js)

| Variable | Required? | Used for | If missing |
|----------|-----------|----------|------------|
| **REACT_APP_BACKEND_URL** | No | API base URL | Default `http://localhost:8000`. |

### 1.3 Summary: what is “missing” for full functionality

| Feature | Keys / config needed |
|---------|----------------------|
| **App runs** | MONGO_URL, DB_NAME only. |
| **Auth (email/password)** | None (JWT_SECRET has default). |
| **Google login** | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, FRONTEND_URL. |
| **AI chat / build / plan / analyze** | At least one: OPENAI_API_KEY or ANTHROPIC_API_KEY (or user keys in Settings). Gemini: GEMINI_API_KEY or GOOGLE_API_KEY. |
| **Voice transcribe** | OPENAI_API_KEY (or user workspace env). |
| **Image-to-code** | OPENAI_API_KEY (or user env). |
| **Stripe (buy tokens)** | STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, FRONTEND_URL. |
| **Production security** | JWT_SECRET (unique), CORS_ORIGINS (your domain), no default secrets. |

---

## 2. Security and abuse – what is in place vs missing

### 2.1 In place

| Item | Status |
|------|--------|
| **.env gitignored** | Yes (`*.env`, `*.env.*` in .gitignore). |
| **Secrets not in frontend** | Backend keys stay in server; only JWT (opaque token) and REACT_APP_BACKEND_URL in frontend. |
| **User API keys (Settings)** | Stored in DB (`workspace_env`); returned only to same user via GET /workspace/env (auth required). |
| **Auth on protected routes** | get_current_user → 401 if no/invalid token. |
| **Stripe webhook** | Signature verified with STRIPE_WEBHOOK_SECRET. |
| **Passwords** | Hashed (bcrypt) before store; not logged. |
| **CORS** | Configurable; default `*` (development). |

### 2.2 Missing or weak (to add next)

| Gap | Risk | Recommendation |
|-----|------|-----------------|
| **No rate limiting** | Brute force on login/register; abuse of /ai/chat, /build/plan (token/cost exhaustion). | Add per-IP (or per-user) rate limits on `/auth/login`, `/auth/register`, and optionally on `/ai/chat`, `/build/plan`. |
| **JWT_SECRET default** | If unchanged in prod, tokens can be forged. | Require explicit JWT_SECRET in production (fail startup if default). |
| **CORS `*`** | Any site can call your API from browser. | In production set CORS_ORIGINS to your frontend origin only. |
| **No request size limit** | Large body on upload/chat could DoS. | Enforce max body size (e.g. 10–50 MB) in FastAPI/uvicorn. |
| **No CSP / X-Frame-Options** | Frontend not hardened against XSS/clickjacking (backend is API-only). | Optional: add security headers on backend for any HTML it serves; frontend build can set CSP. |
| **User keys in DB** | Stored in plaintext in `workspace_env`. | Consider encrypting at rest (e.g. with a server-side key) for higher assurance. |
| **Logging** | Logger may log request data. | Ensure no logging of Authorization header, body with keys, or full env. |

### 2.3 Code copy / IP protection

| Item | Status |
|------|--------|
| **Generated code** | Owned by user; stored in DB per project. Not exposed to other users except via share link (read-only). |
| **Your app code** | In repo; .env not committed. No obfuscation – standard for many apps. |
| **Abuse** | No rate limit or per-IP cap → someone could scrape or hammer endpoints. | Add rate limiting and monitor abuse. |

---

## 3. Checklist before production

- [ ] Set **JWT_SECRET** to a strong random value; do not use default in production.
- [ ] Set **CORS_ORIGINS** to your frontend origin (e.g. `https://yourapp.com`).
- [ ] Add **rate limiting** on auth and heavy AI/build endpoints.
- [ ] Ensure **MONGO_URL** and **DB_NAME** point to production DB; credentials not in repo.
- [ ] If using Stripe: set **STRIPE_SECRET_KEY**, **STRIPE_WEBHOOK_SECRET**; verify webhook URL and signature.
- [ ] If using Google login: set **GOOGLE_CLIENT_ID**, **GOOGLE_CLIENT_SECRET**; set **FRONTEND_URL** to production URL.
- [ ] For AI: set at least one of **OPENAI_API_KEY**, **ANTHROPIC_API_KEY** (and optionally **GEMINI_API_KEY**) or rely on user keys in Settings.
- [ ] Confirm **.env** (and any `.env.*` with secrets) are never committed; `.gitignore` already has `*.env`.
- [ ] Optional: encrypt user API keys in DB; add max body size; add security headers (CSP, X-Frame-Options).

---

## 4. Quick reference – “list all missing API or API keys”

**Required for server to start:**  
`MONGO_URL`, `DB_NAME`

**Optional (feature-specific):**

- **OpenAI (chat, voice, image, many AI routes):** `OPENAI_API_KEY` or `LLM_API_KEY`
- **Anthropic (Claude):** `ANTHROPIC_API_KEY`
- **Google Gemini:** `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- **Auth (production):** `JWT_SECRET` (change from default)
- **CORS (production):** `CORS_ORIGINS`
- **Stripe:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- **Google OAuth:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- **Redirects:** `FRONTEND_URL`

**Frontend:**  
`REACT_APP_BACKEND_URL` (optional; default `http://localhost:8000`)

**User-level keys (stored in DB via Settings):**  
Users can set OPENAI_API_KEY and ANTHROPIC_API_KEY in workspace env; these are used when present and override server env for that user’s requests.
