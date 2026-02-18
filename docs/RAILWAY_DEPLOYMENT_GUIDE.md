# Railway Deployment Guide for CrucibAI

## Overview

This guide explains how to deploy CrucibAI to Railway, a modern cloud platform for full-stack applications.

**Recommended: Backend via Dockerfile.** The repo includes a root `Dockerfile` and `railway.json` that build and run the Python backend. In Railway: connect the repo, use the Dockerfile builder, **set required env vars** (see below), and deploy. The backend serves the API on `PORT` (Railway sets this automatically). For the frontend, build separately (e.g. static export) and point it to your backend URL, or serve the frontend from another service.

### 502 Bad Gateway? → **See [RAILWAY_QUICKSTART.md](../RAILWAY_QUICKSTART.md)**

If you see **"Application failed to respond"** (502) on your Railway URL, the app is crashing at startup. **Add these in Railway Dashboard → Your Project → Variables**, then redeploy:

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | **Yes** | MongoDB connection string (e.g. from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free tier) |
| `DB_NAME` | **Yes** | Database name (e.g. `crucibai`) |
| `JWT_SECRET` | **Yes** (production) | Secret for JWT tokens; use a long random string (e.g. `openssl rand -hex 32`) |
| `PORT` | Set by Railway | Do not override unless needed |

Without `MONGO_URL` and `DB_NAME`, the server exits immediately. **Step-by-step:** [RAILWAY_QUICKSTART.md](../RAILWAY_QUICKSTART.md). Check **Deploy logs** in Railway for the exact error.

---

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway
- Environment variables configured

---

## Deployment Configuration Files

### 1. `railway.json`
Main configuration file that tells Railway how to build and deploy the app.

```json
{
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "npm run start:prod",
    "restartPolicyMaxRetries": 5
  },
  "variables": {
    "PORT": "3000",
    "NODE_ENV": "production"
  }
}
```

### 2. `Procfile`
Tells Railway how to start the application.

```
web: npm run start:prod
```

### 3. `.railwayignore`
Excludes unnecessary files from deployment to reduce build time and size.

---

## Environment Variables

Configure these in Railway dashboard:

```env
# Backend
NODE_ENV=production
PORT=3000
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=your-gemini-key-here

# Database
MONGODB_URI=your-mongodb-connection-string
REDIS_URL=your-redis-connection-string

# Frontend
VITE_API_URL=https://your-railway-app.railway.app
VITE_APP_TITLE=CrucibAI

# Security
JWT_SECRET=your-jwt-secret-key
CORS_ORIGIN=https://your-railway-app.railway.app
```

---

## Deployment Steps

### Step 1: Connect GitHub Repository
1. Go to Railway dashboard
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your GitHub account
5. Select `disputestrike/newcrucib` repository

### Step 2: Configure Build Settings
1. Railway auto-detects Node.js from `package.json`
2. Sets build command to `npm install`
3. Sets start command to `npm run start:prod`

### Step 3: Add Environment Variables
1. Go to "Variables" tab
2. Add all environment variables listed above
3. Click "Deploy"

### Step 4: Monitor Deployment
1. Watch the build logs
2. Deployment should complete in 2-5 minutes
3. Your app is live at `https://your-app.railway.app`

---

## Build Process

Railway will:

1. **Install dependencies**
   ```bash
   npm install
   npm install --prefix backend
   npm install --prefix frontend
   ```

2. **Build frontend**
   ```bash
   npm run build --prefix frontend
   ```

3. **Build backend**
   ```bash
   npm run build --prefix backend
   ```

4. **Start application**
   ```bash
   npm run start:prod
   ```

---

## Troubleshooting

### Issue: "Railpack could not determine how to build the app"

**Solution:** Ensure `package.json` exists in root directory with proper scripts.

### Issue: Build fails with "Cannot find module"

**Solution:** Check that `npm install` completes successfully. Add `--legacy-peer-deps` if needed.

### Issue: App crashes after deployment

**Solution:** Check logs in Railway dashboard. Ensure all environment variables are set.

### Issue: Frontend not loading

**Solution:** Ensure `VITE_API_URL` points to correct backend URL.

---

## Performance Optimization

### 1. Enable Caching
Railway caches `node_modules` automatically. No additional configuration needed.

### 2. Reduce Build Size
- `.railwayignore` excludes unnecessary files
- Frontend build is optimized with Vite
- Backend uses production dependencies only

### 3. Database Connection
- Use connection pooling for PostgreSQL
- Redis for caching
- MongoDB for document storage

---

## Monitoring & Logs

### View Logs
1. Go to Railway dashboard
2. Click your project
3. Select "Logs" tab
4. Filter by service (backend/frontend)

### Common Log Patterns

**Successful startup:**
```
Server running on port 3000
Connected to MongoDB
Redis cache initialized
```

**Build successful:**
```
✓ Frontend build complete
✓ Backend build complete
✓ Ready to start
```

---

## Scaling

### Horizontal Scaling
1. Go to "Settings" tab
2. Increase "Replicas" count
3. Railway automatically load balances

### Vertical Scaling
1. Go to "Settings" tab
2. Increase "Memory" allocation
3. Restart application

---

## Custom Domain

### Add Custom Domain
1. Go to "Settings" tab
2. Click "Add Custom Domain"
3. Enter your domain (e.g., crucibai.com)
4. Update DNS records with Railway's nameservers
5. Domain active in 24-48 hours

---

## Continuous Deployment

Railway automatically deploys when you push to GitHub:

1. Push code to `main` branch
2. GitHub webhook triggers Railway
3. Railway builds and deploys
4. New version live in 2-5 minutes

---

## Rollback

If deployment fails:

1. Go to "Deployments" tab
2. Select previous successful deployment
3. Click "Rollback"
4. Previous version restored immediately

---

## Cost Estimation

**Monthly costs (approximate):**
- Compute: $5-20 (depending on traffic)
- Database: $15-50 (MongoDB + Redis)
- Custom domain: $0 (if you own it)
- **Total: $20-70/month**

---

## Support

- Railway Docs: https://docs.railway.app
- Railway Community: https://railway.app/community
- CrucibAI Support: support@crucibai.com

---

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Connect to Railway
3. ✅ Configure environment variables
4. ✅ Deploy
5. ✅ Monitor logs
6. ✅ Add custom domain
7. ✅ Scale as needed

---

**CrucibAI is now deployed and ready for production!** 🚀
