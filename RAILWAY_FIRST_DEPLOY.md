# Railway — First deploy: add these 3 variables

Your deploy is failing with **"Missing required env: MONGO_URL, DB_NAME"** until you add them.

## Do this once

1. **Railway Dashboard** → open your project → click your **service** (the one that runs the backend).
2. Open **Variables** (tab or sidebar).
3. Click **+ New Variable** or **Raw Editor** and add:

| Name | Value |
|------|--------|
| `MONGO_URL` | Your MongoDB connection string (e.g. from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free tier: Connect → Driver: Python → copy URI like `mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net`) |
| `DB_NAME` | `crucibai` (or any database name) |
| `JWT_SECRET` | Run in terminal: `openssl rand -hex 32` and paste the output |

4. **Redeploy**: Deployments → **Redeploy** or push a new commit.

After that, the container will start and your API will be live at `https://web-production-xxxx.up.railway.app`.

More detail: **[RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md)**.
