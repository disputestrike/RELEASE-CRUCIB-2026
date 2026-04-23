# Merge Plan (Reversed): Local as Base — Bring Remote’s New Features Into Local

**Goal:** Keep **local** as the single codebase (stable, rich, working). Pull **only the new features from remote into local**. Do **not** bring remote’s Google Auth (keep your working local one). Optionally, later, migrate the database from MongoDB to PostgreSQL so local runs on Postgres.

---

## Why This Approach?

- **Local is already working and stable** — full feature set, audit work, indexes, encryption, logApiError, working Google OAuth.
- **Remote has useful additions** — Railway deployment, new IDE-style components, new backend modules — but remote is thinner (fewer endpoints) and its Google Auth doesn’t work for you.
- **Lower risk:** We add to local instead of rebuilding on remote. No big rewrite; incremental improvements.
- **Database:** Stay on MongoDB for now; migrate to PostgreSQL in a **separate, later phase** when you’re ready.

---

## What We Do **Not** Bring From Remote

| Do not bring | Reason |
|--------------|--------|
| **Remote’s Google OAuth** | You said: “we definitely do not want to bring in their Google auth.” Local’s works; keep it. |
| **Remote’s auth router / signup path** | Local keeps `/api/auth/register`, `/api/auth/login`, `/api/auth/google`, `/api/auth/google/callback`, etc. |
| **Removal of `/api` prefix** | Local and frontend use `/api/...`; no change. |
| **Remote’s replacement of server.py with routers** | Optional later refactor; not required to “bring remote in.” We can cherry-pick **logic** from remote’s routers without replacing local’s structure. |
| **Anything that would remove local’s audit work** | Keep db_indexes, env_encryption, logApiError, deletion E2E, CONTRIBUTING, audit docs. |
| **Remote’s PostgreSQL / db.py / db_schema** | For now keep MongoDB. Postgres migration is a separate phase below. |

---

## What We **Do** Bring From Remote Into Local

### 1. Deployment (Railway / Docker) — **No action needed**

**Local already has Railway deployment** and has been deployed successfully in the past. You have:

- **railway.json** — builder DOCKERFILE, startCommand for uvicorn.
- **Dockerfile** — multi-stage (frontend build with `REACT_APP_BACKEND_URL=` for same-origin `/api`, then backend + static).
- **Docs** — `RAILWAY_QUICKSTART.md`, `RAILWAY_FIRST_DEPLOY.md`, `docs/RAILWAY_DEPLOYMENT_GUIDE.md`, `docs/DEPLOY_SUMMARY_RAILWAY.md`.
- **App.js** — already uses empty `REACT_APP_BACKEND_URL` for single-URL deploy on Railway.
- **server.py** — serves frontend from `./static`, FATAL messages reference Railway/Production Variables.

So we **do not** need to bring Railway or Docker config from remote. Skip this step; keep using your existing setup.

---

### 2. New backend modules (integrate with local server.py + MongoDB)

Bring the **code** from remote; wire it into local’s `server.py` or local modules so it uses **MongoDB** (and local’s env, JWT, etc.), not Postgres.

| Module (remote) | What it does | Action on local |
|-----------------|--------------|------------------|
| **ide_features.py** | IDE-style features | Copy file; call from server.py or workspace routes where relevant. Use Motor/db, not asyncpg. |
| **git_integration.py** | Git operations | Same: copy, adapt to use local db/config. |
| **terminal_integration.py** | Terminal/shell integration | Same. |
| **vibe_analysis.py** / **vibe_code_generator.py** | VibeCode analysis/generation | Same. |
| **ecosystem_integration.py** | Ecosystem (e.g. packages, deps) | Same. |
| **monitoring.py** | Monitoring helpers | Same. |
| **agent_cache.py** | Agent response caching | Same; use MongoDB or in-memory, not Postgres. |
| **ai_features.py** | Extra AI feature helpers | Same. |
| **parallel_workers.py**, **phase_optimizer.py**, **incremental_execution.py** | Build/orchestration helpers | Copy if useful; integrate with local build flow. |
| **validate_deployment.py** | Deploy validation | Same. |

**Important:** Each of these may reference `db` or `get_db()` from remote’s Postgres layer. When porting, either (a) replace with local’s `db` (Motor) and existing collections, or (b) add thin wrappers so the module’s interface stays the same but data comes from MongoDB.

---

### 3. New frontend components (from remote)

| Component (remote) | Action on local |
|--------------------|------------------|
| **IDETerminal** | Copy component into local frontend; wire into Workspace or layout if you want terminal in the app. |
| **IDEGit** | Same. |
| **IDEDebugger** | Same. |
| **IDELinter** | Same. |
| **IDEProfiler** | Same. |
| **VibeCodeInterface** | Same. |
| **AIFeaturesPanel** | Same. |
| **EcosystemIntegration** | Same. |
| **MonitoringDashboard** | Same. |
| **UnifiedIDE** | If it’s a wrapper that composes the above, add it and wire to local API. |

**Note:** Remote may have changed **Settings** or **Workspace** in ways that removed logApiError or deletion flows. When bringing components in, **do not** overwrite local’s Settings/Workspace behavior (keep logApiError, workspace mode persistence, etc.). Prefer: add new components as **new** files and import them where needed, or merge only the UI/structure and keep local’s API calls and error handling.

---

### 4. Docs from remote (add, don’t replace)

| Doc (remote) | Action on local |
|--------------|------------------|
| **RAILWAY_DEPLOYMENT_GUIDE.md** | Copy; adjust for local (MongoDB, existing env vars). |
| **DEPLOYMENT_CHECKLIST.md** | Same. |
| **docker-compose.yml** | Add if useful. |
| **COMPREHENSIVE_AUDIT_REPORT.md** | Optional; keep local’s APP_AUDIT_GAPS_AND_PERFORMANCE.md as source of truth. |

Do **not** remove local’s CONTRIBUTING.md, IMPLEMENTATION_PLAN_APPROVED.md, audit docs, or SOURCE_BIBLE updates.

---

### 5. Optional: Modularize backend later (without losing local behavior)

If you want a **modular** backend like remote (routers) but still on local’s behavior:

- Create routers **that mirror local’s routes** (e.g. `routers/auth.py` with register, login, google, google/callback, me; `routers/projects.py` with all project routes; etc.).
- Move logic from `server.py` into these routers **in small steps**, keeping MongoDB and `/api` prefix.
- Do **not** copy remote’s router **implementations** (they’re for Postgres and a subset of routes). Use them only as a structural idea; the **code** stays local’s.

This is a **refactor** step, not required to “bring remote in.” You can do it after deployment and new components are in.

---

## Order of Operations (High Level)

1. **Branch**  
   Work on a branch from current local `main` (e.g. `bring-remote-in`). Keep main stable.

2. **Backend modules**  
   - Copy chosen remote modules (ide_features, git_integration, terminal_integration, vibe_*, ecosystem_integration, monitoring, etc.).  
   - Adapt each to use local `db` (Motor) and config; wire into server.py or existing entry points.

3. **Frontend components**  
   - Copy new IDE/VibeCode/monitoring components from remote into local frontend.  
   - Wire them into Workspace or layout without overwriting local’s logApiError, workspace mode, or deletion flows.

4. **Docs**  
   - Add any remote docs you still want (e.g. deployment checklist); keep all local audit and contribution docs. (Railway docs already exist locally.)

5. **Tests**  
   - Run existing local tests (test_crucibai_api, deletion E2E, etc.); fix anything broken by the new code.

---

## Later Phase: Migrate Local from MongoDB to PostgreSQL

When you’re ready to switch the database:

1. **Add Postgres** alongside Mongo (new `db.py`, `db_schema.py` for Postgres; keep Mongo for a while if needed).  
2. **Dual-write or one-time migration:** Migrate users, projects, token_ledger, workspace_env, etc., to Postgres.  
3. **Switch server to Postgres:** Point local’s `server.py` (and any new modules) at Postgres instead of Motor; remove Mongo dependency.  
4. **Indexes:** Add Postgres indexes (same as in db_indexes for Mongo).  
5. **Env encryption:** Keep; ensure it works with Postgres-backed workspace_env (or equivalent table).

This stays a **separate plan** (e.g. “Phase 2: DB migration”) so the “bring remote in” work stays independent and low-risk.

---

## Summary

| Direction | What we do |
|-----------|------------|
| **Base** | Local (MongoDB, full routes, audit work, **working Google Auth**). |
| **Bring in from remote** | New backend modules (adapted to MongoDB), new frontend components (IDETerminal, IDEGit, VibeCode, etc.). Railway/Docker: not needed — local already has it and has been deployed successfully. |
| **Do not bring** | Remote’s Google OAuth, remote’s auth replacement, API prefix removal, anything that removes local’s security/audit or stability. |
| **Database** | Stay on MongoDB for this phase; migrate to Postgres in a later, separate phase if you want. |

Result: local stays the single source of truth, gets richer with remote’s new features, and you keep your working Google Auth and all current behavior. Once that’s done, you can optionally migrate MongoDB → PostgreSQL on this same codebase.
