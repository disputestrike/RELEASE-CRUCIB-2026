# Railway Variables — Complete Reference

Use this as your single checklist. **Keep your existing secret values**; only add or fix the ones below.  
In Railway → your service → **Variables**, set these (add any that are missing).

---

## Core (you have these — keep as-is)

```
API_TIMEOUT=120
BUILD_CACHE_ENABLED=true
BUILD_MAX_RETRIES=3
BUILD_TIMEOUT_SECONDS=3600
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
DATABASE_URL=<your existing postgresql://... value>
DB_POOL_MAX_SIZE=20
DB_POOL_MIN_SIZE=5
DB_POOL_TIMEOUT=30
DEPLOYMENT_AUTO_SCALING=true
DEPLOYMENT_CPU_LIMIT=2000m
DEPLOYMENT_CPU_REQUEST=500m
DEPLOYMENT_MAX_REPLICAS=10
DEPLOYMENT_MEMORY_LIMIT=2Gi
DEPLOYMENT_MEMORY_REQUEST=512Mi
DEPLOYMENT_MIN_REPLICAS=2
DEPLOYMENT_REPLICAS=2
ENCRYPTION_KEY=<your existing value>
ENVIRONMENT=production
FEATURE_ADVANCED_MONITORING=true
FEATURE_AGENT_CACHING=true
FEATURE_INCREMENTAL_EXECUTION=true
FEATURE_PARALLEL_WORKERS=true
FEATURE_PHASE_OPTIMIZATION=true
HEALTH_CHECK_INTERVAL=30
INCREMENTAL_CACHE_ENABLED=true
INCREMENTAL_EXECUTION_ENABLED=true
JWT_SECRET=<your existing value>
LOG_BACKUP_COUNT=10
LOG_FILE=/app/logs/crucibai.log
LOG_FORMAT=json
LOG_LEVEL=INFO
LOG_MAX_SIZE_MB=100
MAX_CONCURRENT_AGENTS=50
MAX_RETRIES=3
MEMORY_CACHE_ENABLED=true
MEMORY_CACHE_SIZE_MB=512
METRICS_ENABLED=true
METRICS_PORT=9090
NODE_ENV=production
PARALLEL_WORKERS=4
PHASE_OPTIMIZATION_ENABLED=true
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
RATE_LIMIT_ENABLED=true
RETRY_BACKOFF=1.5
TARGET_PHASE_COUNT=6
WORKERS=4
```

---

## CORS & frontend (one fix)

The app reads **RATE_LIMIT_PER_MINUTE** (not RATE_LIMIT_REQUESTS_PER_MINUTE).  
And for production, **CORS_ORIGINS** should be your real frontend origin so the browser allows requests.

**Add or edit:**

```
CORS_ORIGINS=https://crucibai-production.up.railway.app
RATE_LIMIT_PER_MINUTE=100
FRONTEND_URL=https://crucibai-production.up.railway.app
```

If your frontend is on a **different** URL (e.g. Vercel or another domain), set both to that URL, e.g.:

```
CORS_ORIGINS=https://your-frontend-domain.com
FRONTEND_URL=https://your-frontend-domain.com
```

---

## Google Auth (you have these — keep as-is)

```
GOOGLE_CLIENT_ID=<your existing value>
GOOGLE_CLIENT_SECRET=<your existing value>
GOOGLE_REDIRECT_URI=https://crucibai-production.up.railway.app/api/auth/google/callback
```

In **Google Cloud Console** → APIs & Services → Credentials → your OAuth 2.0 Client → **Authorized redirect URIs** must include exactly:

```
https://crucibai-production.up.railway.app/api/auth/google/callback
```

(If your backend URL is different, use that base + `/api/auth/google/callback`.)

---

## Add these (required for AI builds)

The backend needs **at least one** LLM key so builds can run. Add one or both:

```
ANTHROPIC_API_KEY=<get from console.anthropic.com>
CEREBRAS_API_KEY=<get from cerebras.ai — optional if you use Anthropic>
```

Without at least one of these, creating a project and running a build will fail when the app calls the LLM.

---

## Add these (optional but recommended for production)

**Backend public URL** (for preview links, webhooks, OAuth callbacks that need the real host):

```
API_BASE_URL=https://crucibai-production.up.railway.app
BACKEND_PUBLIC_URL=https://crucibai-production.up.railway.app
```

**Stripe (only if you want paid credits):**

```
STRIPE_SECRET_KEY=<from Stripe Dashboard>
STRIPE_WEBHOOK_SECRET=<from Stripe webhook endpoint>
```

Then in Stripe Dashboard create a webhook pointing to:

```
https://crucibai-production.up.railway.app/api/stripe/webhook
```

---

## Optional (only if you use the feature)

- **Session timeout:** `SESSION_TIMEOUT_MINUTES=60` (default)
- **HTTPS redirect:** `HTTPS_REDIRECT=true` if you want the app to redirect HTTP → HTTPS
- **Admin users:** `ADMIN_USER_IDS=user-id-1,user-id-2` (comma-separated user IDs)
- **Enterprise contact email:** `ENTERPRISE_CONTACT_EMAIL=you@example.com`
- **Tavily (web search):** `TAVILY_API_KEY=...`
- **Images (Together):** `TOGETHER_API_KEY=...`, `TOGETHER_IMAGE_MODEL=...`
- **Videos (Pexels):** `PEXELS_API_KEY=...`
- **Deploy (Vercel/Netlify):** `VERCEL_TOKEN=...`, `NETLIFY_TOKEN=...`

---

## Summary: what to add in Railway

1. **RATE_LIMIT_PER_MINUTE** = `100` (app reads this name).
2. **CORS_ORIGINS** = your frontend URL (e.g. `https://crucibai-production.up.railway.app` if same as backend), not `*`.
3. **ANTHROPIC_API_KEY** or **CEREBRAS_API_KEY** (at least one) for builds.
4. **API_BASE_URL** and **BACKEND_PUBLIC_URL** = `https://crucibai-production.up.railway.app` (or your real backend URL).
5. **STRIPE_SECRET_KEY** and **STRIPE_WEBHOOK_SECRET** if you want payments.

Keep all your existing variables as they are; only add or adjust the ones above so Google Auth and builds work correctly.
