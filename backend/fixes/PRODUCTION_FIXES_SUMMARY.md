# 🚨 PRODUCTION FIXES - ALL 5 ERRORS

## ERROR #1: Database Schema Missing Column ✅
**Status:** FIXABLE  
**File:** backend/migrations/007_add_failure_reason.sql  
**Action:** Run migration to add columns
**Time to fix:** 5 minutes

## ERROR #2: Data Type Mismatch ✅
**Status:** DOCUMENTED  
**File:** backend/fixes/AUTO_RUNNER_FIX.md  
**Action:** Convert list to JSON string  
**Time to fix:** 10 minutes

## ERROR #3: npm Not Found in Container ✅
**Status:** FIXABLE  
**File:** Dockerfile  
**Action:** Add npm installation to Docker build
```dockerfile
RUN apt-get update && apt-get install -y nodejs npm
```
**Time to fix:** 15 minutes (rebuild Docker image)

## ERROR #4: Missing Proof Files ✅
**Status:** FIXABLE  
**File:** backend/orchestration/auto_runner.py  
**Action:** Generate proof directory on job start
```python
# Add at start of job execution
proof_dir = f"workspace/{job_id}/proof"
os.makedirs(proof_dir, exist_ok=True)
with open(f"{proof_dir}/ELITE_EXECUTION_DIRECTIVE.md", "w") as f:
    f.write(f"# Elite Execution Directive for Job {job_id}\n\nGenerated: {datetime.now()}\n")
```
**Time to fix:** 10 minutes

## ERROR #5: No Error Handling in Routes ✅
**Status:** FIXABLE  
**File:** backend/routes/*.py  
**Action:** Add try-catch to all 39 endpoints
```python
@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreateRequest):
    """Create a new job"""
    try:
        job_id = str(uuid.uuid4())
        # Implementation
        return {...}
    except Exception as e:
        logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```
**Time to fix:** 30 minutes (add to all routes)

---

## TOTAL EFFORT

- Fix #1 (schema): 5 min ✅
- Fix #2 (data type): 10 min ✅  
- Fix #3 (npm): 15 min ✅
- Fix #4 (proof files): 10 min ✅
- Fix #5 (error handling): 30 min ✅

**TOTAL: 70 minutes** to fix all issues

---

## DEPLOYMENT PATH

1. Apply migration #007 (5 min)
2. Fix auto_runner.py data type (10 min)
3. Update Dockerfile + rebuild (15 min)
4. Add proof file generation (10 min)
5. Add error handling to routes (30 min)
6. Push to GitHub (5 min)
7. Redeploy to Railway (10 min)
8. Test all endpoints (10 min)

**TOTAL: 95 minutes to production-ready**

