# Railway — Fix 502 / Get CrucibAI Running

**If you see "Application failed to respond" (502)** on your Railway URL, the backend is exiting at startup because required environment variables are missing.

---

## 1. Add required variables (one-time)

1. Open **Railway Dashboard** → your project → the **backend service**.
2. Go to **Variables** (or **Settings → Variables**).
3. Add these (click **+ New Variable** or **Raw Editor**):

| Variable     | Required | Example / where to get it |
|-------------|----------|---------------------------|
| `MONGO_URL` | **Yes**  | MongoDB connection string. Get a free cluster at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) → Connect → Driver: Python → copy the URI. Use format: `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net` |
| `DB_NAME`   | **Yes**  | Any name, e.g. `crucibai` |
| `JWT_SECRET`| **Yes** (prod) | Long random string (e.g. run `openssl rand -hex 32` and paste) |

4. **Redeploy**: Deployments → trigger a new deploy, or push a commit.

---

## 2. Optional (for full features)

| Variable | Use |
|----------|-----|
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | Required for AI build/chat in the app |
| `FRONTEND_URL` | Your frontend URL (e.g. `https://your-app.vercel.app`) for auth redirects and CORS |
| `CORS_ORIGINS` | Comma-separated allowed origins; default `*` |

---

## 3. Check deploy logs

- Railway → your service → **Deployments** → click the latest deploy → **View Logs**.
- If you see `FATAL: Missing required env: MONGO_URL, DB_NAME`, add those variables and redeploy.
- After a successful start you should see Uvicorn logs like `Uvicorn running on http://0.0.0.0:XXXX`.

---

## 4. Build and start (how Railway runs the app)

- **Build:** Railway uses the repo **Dockerfile**: builds the backend image (Python 3.11, `backend/`).
- **Start:** Runs `uvicorn server:app --host 0.0.0.0 --port $PORT`. Railway sets `PORT` automatically.
- No need to set `PORT` yourself.

Once `MONGO_URL`, `DB_NAME`, and `JWT_SECRET` are set and you redeploy, the 502 should be resolved and your API will respond at the Railway URL.
