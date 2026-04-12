# 🚀 GAUNTLET DEPLOYMENT GUIDE

**Status:** ✅ Ready for Production Integration

**Objective:** Wire GauntletExecutor into CrucibAI and deploy to production

---

## STEP 1: DATABASE SETUP

### Create Gauntlet Tracking Table

```sql
-- PostgreSQL
CREATE TABLE gauntlet_runs (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    spec_file VARCHAR(255) DEFAULT 'proof/GAUNTLET_SPEC.md',
    phase_1_complete BOOLEAN DEFAULT FALSE,
    phase_2_complete BOOLEAN DEFAULT FALSE,
    phase_3_complete BOOLEAN DEFAULT FALSE,
    phase_4_complete BOOLEAN DEFAULT FALSE,
    elite_verified BOOLEAN DEFAULT FALSE,
    proof_files JSONB DEFAULT '{}',
    test_results JSONB DEFAULT '{}',
    error_message TEXT,
    user_id VARCHAR(36)
);

CREATE INDEX idx_gauntlet_runs_user_id ON gauntlet_runs(user_id);
CREATE INDEX idx_gauntlet_runs_status ON gauntlet_runs(status);
```

---

## STEP 2: UPDATE agent_dag.py

### Add Gauntlet Agents to AGENT_DAG

**File:** `backend/agent_dag.py`

Add these lines after the existing agents:

```python
# GAUNTLET AGENTS (Phases 1-4)
"Gauntlet Executor": {
    "depends_on": ["Planner"],
    "system_prompt": """You are the Gauntlet Executor for CrucibAI..."""
},
"Gauntlet Backend Builder": {
    "depends_on": ["Gauntlet Executor", "Backend Generation"],
    "system_prompt": """You are the Gauntlet Backend Builder..."""
},
"Gauntlet Test Builder": {
    "depends_on": ["Gauntlet Executor", "Test Generation"],
    "system_prompt": """You are the Gauntlet Test Builder..."""
},
"Gauntlet Proof Builder": {
    "depends_on": ["Gauntlet Backend Builder", "Gauntlet Test Builder"],
    "system_prompt": """You are the Gauntlet Proof Builder..."""
},
"Gauntlet Verifier": {
    "depends_on": ["Gauntlet Backend Builder", "Gauntlet Test Builder"],
    "system_prompt": """You are the Gauntlet Verifier..."""
},
```

Or use the Python import:

```python
from gauntlet_integration import get_gauntlet_agents_for_dag

# In agent_dag.py
AGENT_DAG.update(get_gauntlet_agents_for_dag())
```

---

## STEP 3: UPDATE server.py

### 3.1 Add Imports

```python
from gauntlet_integration import (
    GauntletRun,
    GauntletStartRequest,
    GauntletStartResponse,
    GauntletStatusResponse,
    setup_gauntlet_integration,
    start_gauntlet_execution,
    get_gauntlet_status,
)
```

### 3.2 Add Database Model

In your database initialization (around line ~200):

```python
# Add GauntletRun to Base models
from gauntlet_integration import Base as GauntletBase

# When creating tables:
GauntletBase.metadata.create_all(bind=engine)
```

### 3.3 Add Routes

Add these endpoints to server.py (before `if __name__ == "__main__"`):

```python
@app.post("/api/gauntlet/execute", response_model=GauntletStartResponse)
async def gauntlet_execute(
    request: GauntletStartRequest,
    user: dict = Depends(get_optional_user)
):
    """Start Gauntlet execution for autonomous SaaS building."""
    try:
        # Get database session (you may need to adjust this based on your DB setup)
        db = SessionLocal()
        result = await start_gauntlet_execution(request, db)
        db.close()
        return GauntletStartResponse(
            status=result["status"],
            executor_id=result["executor_id"],
            phases=result["phases"],
            track_at=result["track_at"]
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500


@app.get("/api/gauntlet/status/{executor_id}")
async def gauntlet_status(
    executor_id: str,
    user: dict = Depends(get_optional_user)
):
    """Check status of a Gauntlet execution."""
    try:
        db = SessionLocal()
        result = await get_gauntlet_status(executor_id, db)
        db.close()
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500


@app.get("/api/gauntlet/spec")
async def gauntlet_get_spec():
    """Get the Gauntlet specification."""
    try:
        with open("proof/GAUNTLET_SPEC.md", "r") as f:
            return {"spec": f.read(), "status": "ready"}
    except FileNotFoundError:
        return {"error": "GAUNTLET_SPEC.md not found"}, 404
```

### 3.4 Wire Startup

Add to startup event:

```python
@app.on_event("startup")
async def startup_gauntlet():
    await setup_gauntlet_integration(app)
    print("✅ Gauntlet ready")
```

---

## STEP 4: UPDATE server.py Agents List

**Find:** `_ORCHESTRATION_AGENTS = [...]` (around line ~400)

**Add** Gauntlet agents:

```python
_ORCHESTRATION_AGENTS = [
    # ... existing agents ...
    "Gauntlet Executor",
    "Gauntlet Backend Builder",
    "Gauntlet Test Builder",
    "Gauntlet Proof Builder",
    "Gauntlet Verifier",
]
```

---

## STEP 5: DEPLOYMENT

### Local Testing

```bash
# 1. Start server
cd /home/claude/CrucibAI
python backend/server.py

# 2. Test endpoint
curl http://localhost:8000/api/gauntlet/spec | jq .

# 3. Start Gauntlet execution
curl -X POST http://localhost:8000/api/gauntlet/execute \
  -H "Content-Type: application/json" \
  -d '{"spec_file": "proof/GAUNTLET_SPEC.md"}'

# 4. Check status (replace with returned executor_id)
curl http://localhost:8000/api/gauntlet/status/{executor_id}
```

### Production Deployment

**Railway Deployment:**

```bash
# 1. Commit changes
git add -A
git commit -m "🎯 GAUNTLET DEPLOYED: Full integration wired to server.py"

# 2. Push to Railway
git push origin gauntlet-elite-run

# 3. Railway auto-deploys from git
# Check logs at: https://railway.app/project/{project_id}

# 4. Test production endpoint
curl https://crucibai-production.up.railway.app/api/gauntlet/execute \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"spec_file": "proof/GAUNTLET_SPEC.md"}'
```

---

## STEP 6: VERIFICATION

### Verify Installation

```bash
# Check that Gauntlet agents are registered
curl http://localhost:8000/api/agents | jq . | grep -i gauntlet

# Check database table exists
psql $DATABASE_URL -c "SELECT COUNT(*) FROM gauntlet_runs;"

# Check spec file is present
ls -la proof/GAUNTLET_SPEC.md

# Check integration module exists
python -c "from backend.gauntlet_integration import GAUNTLET_AGENTS; print(len(GAUNTLET_AGENTS))"
```

### Test Full Flow

```bash
# 1. Start execution
EXECUTOR_ID=$(curl -X POST http://localhost:8000/api/gauntlet/execute \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.executor_id')

echo "Executor ID: $EXECUTOR_ID"

# 2. Monitor status
while true; do
  curl http://localhost:8000/api/gauntlet/status/$EXECUTOR_ID | jq .
  echo "Waiting 10 seconds..."
  sleep 10
done

# 3. When complete, check results
curl http://localhost:8000/api/gauntlet/status/$EXECUTOR_ID | jq '.elite_verified'
# Should output: true
```

---

## EXECUTION FLOW

### When You POST /api/gauntlet/execute

```
1. Create GauntletRun record in DB (status = "phase_1")
2. Return executor_id for tracking

3. Agents dispatch sequentially:
   Phase 1 (1 hr):
     - Gauntlet Executor verifies spec files
     - Status: phase_1_complete = true
   
   Phase 2 (5 hrs):
     - Gauntlet Backend Builder → backend/titan_forge_main.py
     - Gauntlet Test Builder → tests/test_foundation.py
     - Gauntlet Proof Builder → proof/*.md (3 files)
     - Run tests, verify pass rate
     - Status: phase_2_complete = true
   
   Phase 3 (7 hrs):
     - Gauntlet Backend Builder → CRM models, routes, services
     - Gauntlet Test Builder → tests/test_business_logic.py
     - Gauntlet Proof Builder → proof/*.md (4 files)
     - Run tests, verify pass rate
     - Status: phase_3_complete = true
   
   Phase 4 (3 hrs):
     - Gauntlet Test Builder → migration, adversarial, concurrency tests
     - Gauntlet Proof Builder → final proof documents
     - Gauntlet Verifier → scripts/phase4_verify.sh
     - Run verification, check exit code
     - Status: phase_4_complete = true, elite_verified = (exit code == 0)

4. Database record updated continuously via status checks
```

---

## MONITORING

### View Status at Any Time

```bash
curl http://localhost:8000/api/gauntlet/status/{executor_id} | jq .
```

### Expected Status Progression

```
Initial:
  phases_complete: 0
  current_phase: null
  status: "phase_1"

After Phase 1 (1 hour):
  phases_complete: 1
  current_phase: "phase_2"
  status: "in_progress"

After Phase 2 (6 hours):
  phases_complete: 2
  current_phase: "phase_3"
  status: "in_progress"

After Phase 3 (13 hours):
  phases_complete: 3
  current_phase: "phase_4"
  status: "in_progress"

After Phase 4 (16 hours):
  phases_complete: 4
  current_phase: null
  status: "complete"
  elite_verified: true
  proof_files_generated: [12 files]
```

---

## TROUBLESHOOTING

### Gauntlet Endpoint Not Found

**Problem:** `POST /api/gauntlet/execute` returns 404

**Solution:**
1. Check that routes are added to server.py
2. Check that server is restarted
3. Verify endpoint definition: `@app.post("/api/gauntlet/execute")`

### Database Table Not Created

**Problem:** `GauntletRun` table doesn't exist

**Solution:**
```python
from gauntlet_integration import GauntletRun, Base
Base.metadata.create_all(bind=engine)
```

### Agents Not Dispatching

**Problem:** Gauntlet agents not found in orchestrator

**Solution:**
1. Verify agents added to `_ORCHESTRATION_AGENTS` list
2. Verify `agent_dag.py` updated with GAUNTLET_AGENTS
3. Restart server

### Tests Not Passing

**Problem:** Gauntlet execution reports test failures

**Solution:**
1. Check test output in status response
2. Run tests locally: `pytest tests/test_foundation.py -v`
3. Check logs for error messages

---

## PERFORMANCE CONSIDERATIONS

### Resource Usage

- **Phase 2-4:** Parallel agent execution (multiple agents at once)
- **Database:** GauntletRun records are lightweight JSON
- **Storage:** ~50MB for generated code + tests + proofs
- **Memory:** ~500MB during peak execution

### Optimization

```python
# Limit concurrent agents to prevent resource exhaustion
MAX_CONCURRENT_AGENTS = 3

# Add to orchestrator
async def execute_phase_with_limit(tasks, max_concurrent=MAX_CONCURRENT_AGENTS):
    semaphore = asyncio.Semaphore(max_concurrent)
    async def bounded_task(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*[bounded_task(t) for t in tasks])
```

---

## ROLLBACK PLAN

If you need to disable Gauntlet:

```bash
# 1. Remove routes from server.py
# 2. Remove agents from agent_dag.py
# 3. Remove gauntlet_integration imports
# 4. Restart server
# 5. Keep database table for historical records (optional)

# No data loss - existing GauntletRun records are preserved
```

---

## SUCCESS CHECKLIST

- [ ] Database table created (gauntlet_runs)
- [ ] Agent DAG updated with 5 Gauntlet agents
- [ ] server.py routes added (/api/gauntlet/*)
- [ ] server.py agents list updated (_ORCHESTRATION_AGENTS)
- [ ] Startup event wired
- [ ] Local testing passes (GET /api/gauntlet/spec)
- [ ] Execution test passes (POST /api/gauntlet/execute)
- [ ] Status endpoint works (GET /api/gauntlet/status/{id})
- [ ] Deployed to Railway/production
- [ ] Production endpoints tested

---

## LIVE DEPLOYMENT

When everything is ready:

```bash
# 1. Final commit
git add -A
git commit -m "🚀 GAUNTLET LIVE: Full deployment to production

- Gauntlet agents wired to agent_dag.py
- Endpoints added to server.py
- Database schema created
- Ready for autonomous SaaS building
- Phase 1-4 execution pipeline active"

# 2. Push and deploy
git push origin gauntlet-elite-run

# 3. Monitor deployment
# Railway logs show startup messages:
# ✅ Gauntlet integration loaded
# ✅ Gauntlet agents registered
# ✅ Ready to execute

# 4. Test production
curl https://crucibai-production.up.railway.app/api/gauntlet/execute -X POST ...

# 5. Start execution
# Watch it autonomously build Titan Forge for ~16 hours

# 6. Check results
curl https://crucibai-production.up.railway.app/api/gauntlet/status/{id}

# 7. Publish
# "CrucibAI autonomously built Titan Forge in 16 hours
#  with 100% test pass rate, zero scaffolding, all honest"
```

---

## GOING LIVE CHECKLIST

✅ **Before Deployment:**
- Code review complete
- All tests pass locally
- Database migration tested
- Endpoints functional
- Agent dispatch verified

✅ **At Deployment:**
- Merge gauntlet-elite-run to main (or keep branch)
- Push to Railway
- Monitor startup logs
- Verify endpoints accessible

✅ **Post-Deployment:**
- Test /api/gauntlet/spec
- Test POST /api/gauntlet/execute
- Test GET /api/gauntlet/status
- Monitor database growth
- Track execution progress

---

**End of GAUNTLET_DEPLOYMENT_GUIDE.md**

You are now ready to deploy Gauntlet to production and let CrucibAI autonomously build systems!
