# 🚀 CRUCIBAI FIX ROADMAP

**Status:** SCAFFOLDING → WORKING (Target: 4 hours)

---

## 🔴 CRITICAL BLOCKERS (MUST FIX FIRST)

### 1. **Missing `.env` file** — App cannot start
- **Location:** `backend/.env`
- **Impact:** Backend won't run at all
- **Fix:** Copy `.env.example` → `.env` and set critical vars
- **Time:** 5 min

**Required Variables:**
```env
# Flask/FastAPI
FLASK_ENV=development
SECRET_KEY=<random-secret>
CRUCIBAI_DEV=1

# Database (MySQL on Railway)
MYSQLHOST=localhost
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=<password>
MYSQLDATABASE=crucibai_dev

# LLM API Keys (for testing)
CEREBRAS_API_KEY=<key-or-skip>
ANTHROPIC_API_KEY=<key-or-skip>

# JWT
JWT_SECRET=<random-secret>
JWT_ALGORITHM=HS256
```

---

## 🟠 HIGH PRIORITY (Breaking Features)

### 2. **Status Bar Not Wired** — Frontend reports no build progress
- **Location:** `frontend/src/pages/Workspace.jsx`
- **Problem:** 
  - No `StatusBar` component imported
  - No `buildStatus` state tracking
  - No real-time updates from backend
- **Fix:**
  ```jsx
  // Add to Workspace.jsx
  import StatusBar from '../components/StatusBar';
  const [buildStatus, setBuildStatus] = useState(null);
  
  // In render:
  <StatusBar status={buildStatus} />
  
  // Listen to build progress:
  useEffect(() => {
    const eventSource = new EventSource('/api/builds/stream');
    eventSource.onmessage = (e) => setBuildStatus(JSON.parse(e.data));
  }, []);
  ```
- **Time:** 30 min

### 3. **Missing Backend Endpoints** — Frontend has nowhere to send requests
- **Endpoints Missing:**
  - `POST /api/builds` - Start a build
  - `GET /api/workspace/:id` - Get workspace state
  - `POST /api/quality-gate` - Quality check  
  - `POST /api/build-plan` - Generate build plan
- **Location:** `backend/server.py` (add missing routers)
- **Fix Strategy:**
  1. Check if routes exist in `backend/routers/` subdirectory
  2. If not, add them to `server.py` as stubs
  3. Wire to real implementation
- **Time:** 45 min

**Stub Implementation:**
```python
@app.post("/api/builds")
async def start_build(workspace_id: str, build_request: dict):
    return {"id": uuid.uuid4(), "status": "queued", "workspace_id": workspace_id}

@app.get("/api/workspace/{workspace_id}")
async def get_workspace(workspace_id: str):
    return {"id": workspace_id, "name": "My Project", "status": "ready"}

@app.post("/api/quality-gate")
async def quality_gate(code: str):
    score = 75  # Placeholder
    return {"passed": score >= 60, "score": score, "verdict": "review"}

@app.post("/api/build-plan")
async def build_plan(project_spec: dict):
    return {"plan": "Generated plan", "steps": []}
```

### 4. **Missing Database Tables** — Schema incomplete
- **Location:** `backend/database_init.py`
- **Missing:** `workspaces` and `agents` tables
- **Fix:** Add table definitions
```python
# Add to database_init.py
CREATE TABLE workspaces (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255),
    state JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    name VARCHAR(255),
    type VARCHAR(50),
    config JSON,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
);
```
- **Time:** 20 min

---

## 🟡 MEDIUM PRIORITY (UI Polish)

### 5. **Status Bar Component Missing** — No visual progress indicator
- **Location:** Need to create `frontend/src/components/StatusBar.jsx`
- **What It Should Show:**
  - Build progress %
  - Current agent running
  - Estimated time remaining
  - Quality score
  - Error indicators
- **Time:** 30 min

### 6. **Pre-build Empty States** — No guidance for first-time users
- **Locations:**
  - `frontend/src/pages/Dashboard.jsx`
  - `frontend/src/pages/Builder.jsx`
  - `frontend/src/pages/ProjectBuilder.jsx`
- **What's Missing:**
  - Empty state UI when no projects exist
  - Call-to-action buttons
  - Template suggestions
  - Onboarding hints
- **Time:** 45 min

### 7. **Component Navigation Gaps** — Layout missing navbar wiring
- **Location:** `frontend/src/components/Layout.jsx`
- **Missing:**
  - Navigation bar implementation (or import)
  - Sidebar state management
  - Mobile responsiveness
- **Time:** 30 min

---

## 🔵 LOW PRIORITY (Cleanup)

### 8. **Frontend TODOs/FIXMEs** — 20+ unresolved comments
- **Action:** Audit and resolve/remove
- **Time:** 1 hour

---

## 🎯 EXECUTION ORDER (Fastest Path to Working App)

```
1. Create .env file                          [5 min]
2. Add missing backend endpoints (stubs)      [30 min]
3. Create StatusBar component                 [30 min]
4. Wire StatusBar into Workspace              [15 min]
5. Add missing database tables                [20 min]
6. Test backend health + basic endpoints      [15 min]
7. Test frontend → backend communication      [15 min]
8. Add empty state UIs                        [30 min]
9. Fix Layout/navbar wiring                   [20 min]
10. Full E2E test (build → complete)          [20 min]

TOTAL: ~3.5 hours
```

---

## 🧪 TESTING CHECKLIST

After each step, verify:

```
[ ] Backend starts without errors
    $ cd backend && python -m uvicorn server:app --reload

[ ] Frontend builds
    $ cd frontend && npm run build

[ ] Can POST /api/health and get 200
    $ curl http://localhost:5000/api/health

[ ] StatusBar shows in UI
    - Open Workspace page
    - Should see progress bar/status indicator

[ ] Can start a build
    - Click "Build" button
    - StatusBar updates in real-time

[ ] Pre-build empty state shows when no project
    - Go to Dashboard with 0 projects
    - Should see "Create Project" CTA

[ ] All required endpoints return data
    /api/workspace/{id} → 200 with workspace
    /api/builds → 200 with build list
    /api/quality-gate → 200 with quality score
```

---

## 🚩 KNOWN BLOCKERS TO AVOID

1. **Don't skip the `.env` file** — Backend will fail silently
2. **Don't use `undefined` endpoints** — Frontend will hang
3. **Don't leave database tables incomplete** — Queries will 500
4. **Don't forget async/await in StatusBar updates** — Race conditions
5. **Don't mix old API schema with new**— validation errors

---

## 📝 POST-FIX VALIDATION

Once all fixes applied, run:

```bash
# In root directory
python DIAGNOSTIC_SCAN.py

# Should show:
# 📊 SCAN COMPLETE - 0 critical, 0 high issues found
```

