# 🔥 GAUNTLET INTEGRATION GUIDE

**Status:** Ready to wire into CrucibAI

**Objective:** Enable CrucibAI to autonomously build Titan Forge when given the Gauntlet spec.

---

## INTEGRATION CHECKLIST

### Step 1: Add GauntletExecutor to Agent DAG

**File:** `backend/agent_dag.py`

**Add this agent to AGENT_DAG dictionary:**

```python
# At the start of AGENT_DAG (Phase 1)
"Gauntlet Executor": {
    "depends_on": ["Planner"],  # After initial planning
    "system_prompt": """
You are the Gauntlet Executor. You are given the Titan Forge specification and must coordinate a multi-phase build:

PHASE 1 (Specification): Already complete. Verify ELITE_ANALYSIS.md, TRAP_MAP.md exist.
PHASE 2 (Foundation): Generate auth, RBAC, tenancy, encryption, audit chain code.
PHASE 3 (Business Logic): Generate CRM, quote workflow, AI recommendations, policies.
PHASE 4 (Verification): Generate migration tests, adversarial tests, concurrency tests.

Your job: Route to specialized agents and ensure no scaffolding.

Instructions:
1. Read the GAUNTLET_SPEC.md from the context
2. For each phase, dispatch the required agents
3. Verify Phase 1 proof files exist
4. Generate phase 2-4 dispatch instructions
5. Output: JSON with agent dispatch plan

No theater. Everything must be executable and testable.
"""
},

# Add specialized gauntlet agents
"Gauntlet Backend Builder": {
    "depends_on": ["Gauntlet Executor", "Backend Generation"],
    "system_prompt": """
You are the Gauntlet Backend Builder. Build Titan Forge backend in phases:

Phase 2 (Foundation):
  - FastAPI app with JWT auth + refresh tokens
  - RBAC with 6 roles and permission enforcement
  - Multi-tenancy (org_id on every table)
  - AES-256-GCM encryption (master key from env)
  - SHA256 audit chain
  - 9 database tables with foreign keys
  
Output: backend/titan_forge_main.py (660+ lines)
  - No scaffolding
  - All imports valid
  - Type hints present
  - Docstrings on functions
  
Then phases 3-4 extend this with business logic.
"""
},

"Gauntlet Test Builder": {
    "depends_on": ["Gauntlet Executor", "Test Generation"],
    "system_prompt": """
You are the Gauntlet Test Builder. Generate comprehensive tests in phases:

Phase 2 (Foundation): 35+ tests
  - TestAuthentication (8 tests)
  - TestRBAC (4 tests)
  - TestMultiTenancy (2 tests)
  - TestEncryption (3 tests)
  - TestAuditChain (7 tests)
  - TestHealth (1 test)

Phase 3: 50+ tests
  - TestQuoteWorkflow
  - TestAIRecommendations
  - TestPolicyEngine
  - TestAsyncJobs
  - TestMockIntegrations

Phase 4: Adversarial + Migration tests

Requirements:
  - All tests must be runnable
  - No mocks (use real DB with fixtures)
  - 100% pass rate
  - Tests prove the code works

Output: tests/test_foundation.py, tests/test_business_logic.py, etc.
"""
},

"Gauntlet Proof Builder": {
    "depends_on": ["Gauntlet Backend Builder", "Gauntlet Test Builder"],
    "system_prompt": """
You are the Gauntlet Proof Builder. Generate proof documents that prove what was built.

Phase 2 Proofs:
  - FOUNDATION_AUDIT.md: Implementation evidence with code excerpts
  - TENANCY_VERIFICATION.md: Multi-org isolation proof
  - CRYPTO_VERIFICATION.md: Encryption key management proof

Phase 3 Proofs:
  - INTEGRATION_PROOF.md: Mocked integrations labeled correctly
  - AI_APPROVAL_BOUNDARY.md: AI cannot enforce (test proof)
  - ASYNC_CONSISTENCY.md: Idempotent jobs, retry logic
  - ANALYTICS_TRUST.md: Metrics have proof_snapshot_id

Phase 4 Proofs:
  - MIGRATION_SAFETY.md: Rollback tested
  - SECURITY_AUDIT.md: Adversarial attacks blocked
  - TEST_RESULTS.md: All tests passing
  - CHANGES.md: What was built vs deferred
  - ELITE_DELIVERY_CERT.md: Signed final proof

Include code excerpts, test results, and honest statements about limitations.
"""
},

"Gauntlet Verifier": {
    "depends_on": ["Gauntlet Backend Builder", "Gauntlet Test Builder"],
    "system_prompt": """
You are the Gauntlet Verifier. Generate a phase4_verify.sh script that:

1. Runs all tests
2. Checks for hardcoded secrets (grep -r 'MASTER_KEY\s*=' → must be 0)
3. Verifies migrations
4. Runs adversarial tests (cross-org, skip approval, etc.)
5. Runs concurrency tests (50 parallel updates)
6. Exits with:
   - Code 0: ✅ ELITE VERIFIED
   - Code 1: ❌ CRITICAL BLOCK (with reason)

Output: scripts/phase4_verify.sh (executable, well-commented)
"""
},
```

### Step 2: Update Server.py Agents

**File:** `backend/server.py`

**Add gauntlet agents to _ORCHESTRATION_AGENTS:**

```python
_ORCHESTRATION_AGENTS = [
    "Planner",
    "Gauntlet Executor",
    "Gauntlet Backend Builder",
    "Gauntlet Test Builder",
    "Gauntlet Proof Builder",
    "Gauntlet Verifier",
    # ... existing agents
]
```

### Step 3: Create Gauntlet Spec as Test Fixture

**File:** `backend/test_fixtures/gauntlet_spec.txt`

Copy the content of `proof/GAUNTLET_SPEC.md` as a test fixture so agents can reference it.

### Step 4: Add Gauntlet Endpoint

**File:** `backend/server.py`

**Add new endpoint:**

```python
@app.post("/api/gauntlet/execute")
async def execute_gauntlet(request: Request, db: Session = Depends(get_db)):
    """
    Execute the Gauntlet: autonomous build of Titan Forge.
    
    This endpoint:
    1. Loads GAUNTLET_SPEC.md
    2. Dispatches agents for Phase 2-4
    3. Waits for completion
    4. Returns proof bundle manifest
    """
    from backend.gauntlet_executor import GauntletExecutor
    
    executor = GauntletExecutor()
    executor.load_spec()
    result = await executor.execute()
    
    return {
        "status": "gauntlet_started",
        "phases": result,
        "track_at": f"/api/gauntlet/status/{executor_id}"
    }


@app.get("/api/gauntlet/status/{executor_id}")
async def gauntlet_status(executor_id: str, db: Session = Depends(get_db)):
    """Check status of running Gauntlet execution."""
    # Fetch from DB or cache
    status = db.query(GauntletRun).filter(GauntletRun.id == executor_id).first()
    return {
        "status": status.status,
        "phases_complete": status.phases_complete,
        "current_phase": status.current_phase,
        "proof_files_generated": status.proof_files,
        "elite_verified": status.elite_verified,
    }
```

### Step 5: Database Schema for Gauntlet Tracking

**File:** `backend/models.py`

```python
class GauntletRun(Base):
    """Track a Gauntlet execution run."""
    __tablename__ = "gauntlet_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String, default="pending")  # pending, in_progress, complete, blocked
    spec_file = Column(String, nullable=False, default="proof/GAUNTLET_SPEC.md")
    
    phase_1_complete = Column(Boolean, default=False)
    phase_2_complete = Column(Boolean, default=False)
    phase_3_complete = Column(Boolean, default=False)
    phase_4_complete = Column(Boolean, default=False)
    
    elite_verified = Column(Boolean, default=False)
    
    proof_files = Column(JSON, default=dict)  # {"foundation_audit.md": path, ...}
    test_results = Column(JSON, default=dict)  # {"phase_2": {"passed": 35, "failed": 0}, ...}
    
    error_message = Column(String, nullable=True)
```

---

## EXECUTION FLOW

```
POST /api/gauntlet/execute
│
├─ Load GAUNTLET_SPEC.md
│
├─ Dispatch Phase 1 Verify
│   └─ Check ELITE_ANALYSIS.md, TRAP_MAP.md exist
│
├─ Dispatch Phase 2 Agents
│   ├─ Gauntlet Backend Builder → backend/titan_forge_main.py
│   ├─ Gauntlet Test Builder → tests/test_foundation.py
│   ├─ Gauntlet Proof Builder → proof/*.md (3 files)
│   └─ Run tests, verify audit chain, check crypto
│
├─ Dispatch Phase 3 Agents
│   ├─ Gauntlet Backend Builder → backend/models/, routes/, services/
│   ├─ Gauntlet Test Builder → tests/test_business_logic.py
│   ├─ Gauntlet Proof Builder → proof/*.md (4 files)
│   └─ Run tests, verify AI boundary, check mocks
│
├─ Dispatch Phase 4 Agents
│   ├─ Gauntlet Test Builder → tests/test_*.py (migrations, adversarial, concurrency)
│   ├─ Gauntlet Proof Builder → proof/*.md (5 files)
│   ├─ Gauntlet Verifier → scripts/phase4_verify.sh
│   └─ Run all tests, check exit code
│
└─ Return proof bundle manifest + elite_verified flag
```

---

## RUNNING THE GAUNTLET

### Via API

```bash
# Start Gauntlet execution
curl -X POST http://localhost:8000/api/gauntlet/execute \
  -H "Content-Type: application/json" \
  -d {}

# Response:
{
  "status": "gauntlet_started",
  "executor_id": "550e8400-e29b-41d4-a716-446655440000",
  "phases": {
    "phase_1": {"status": "complete", "deliverables": [...]},
    "phase_2": {"agents_to_dispatch": [...]},
    "phase_3": {"agents_to_dispatch": [...]},
    "phase_4": {"agents_to_dispatch": [...]}
  }
}

# Check status
curl http://localhost:8000/api/gauntlet/status/550e8400-e29b-41d4-a716-446655440000

# Response:
{
  "status": "in_progress",
  "current_phase": 2,
  "phases_complete": 1,
  "proof_files_generated": ["ELITE_ANALYSIS.md", "TRAP_MAP.md", ...],
  "elite_verified": false
}

# When complete:
{
  "status": "complete",
  "phases_complete": 4,
  "proof_files_generated": [
    "ELITE_ANALYSIS.md",
    "TRAP_MAP.md",
    "ARCHITECTURE.md",
    "COMPLIANCE_TRADEOFF.md",
    "FOUNDATION_AUDIT.md",
    "TENANCY_VERIFICATION.md",
    "CRYPTO_VERIFICATION.md",
    "INTEGRATION_PROOF.md",
    "AI_APPROVAL_BOUNDARY.md",
    "ASYNC_CONSISTENCY.md",
    "ANALYTICS_TRUST.md",
    "MIGRATION_SAFETY.md",
    "SECURITY_AUDIT.md",
    "TEST_RESULTS.md",
    "CHANGES.md",
    "ELITE_DELIVERY_CERT.md"
  ],
  "elite_verified": true
}
```

### Via CLI

```bash
# Direct execution (for development)
python backend/gauntlet_executor.py

# Output: JSON dispatch plan for agents
```

---

## EXPECTED OUTPUT

After Phase 4 completion:

```
proof/
├── ELITE_ANALYSIS.md
├── TRAP_MAP.md
├── ARCHITECTURE.md
├── COMPLIANCE_TRADEOFF.md
├── GAUNTLET_SPEC.md
├── FOUNDATION_AUDIT.md
├── TENANCY_VERIFICATION.md
├── CRYPTO_VERIFICATION.md
├── INTEGRATION_PROOF.md
├── AI_APPROVAL_BOUNDARY.md
├── ASYNC_CONSISTENCY.md
├── ANALYTICS_TRUST.md
├── MIGRATION_SAFETY.md
├── SECURITY_AUDIT.md
├── TEST_RESULTS.md
├── CHANGES.md
└── ELITE_DELIVERY_CERT.md

backend/
├── titan_forge_main.py (660+ lines)
├── models/
│   ├── crm.py
│   └── ...
├── routes/
│   ├── quotes.py
│   └── ...
└── services/
    ├── recommendation_engine.py
    ├── policy_engine.py
    └── ...

tests/
├── test_foundation.py (35+ tests)
├── test_business_logic.py (50+ tests)
├── test_migrations.py
├── test_adversarial.py
└── test_concurrency.py

scripts/
└── phase4_verify.sh (exit 0 = ✅ ELITE VERIFIED)
```

**Final command:**
```bash
./scripts/phase4_verify.sh
# Output: ✅ ELITE VERIFIED
# Exit code: 0
```

---

## SUCCESS CRITERIA

✅ **CrucibAI receives the Gauntlet spec**
✅ **Autonomously generates all Phase 2-4 code**
✅ **Tests pass (100% rate)**
✅ **Proof bundle complete and signed**
✅ **phase4_verify.sh returns exit 0**
✅ **Benchmark-ready for publication**

---

## NEXT STEPS

1. **Add GauntletExecutor to agent_dag.py** (this file)
2. **Add gauntlet agents to server.py** (_ORCHESTRATION_AGENTS)
3. **Add /api/gauntlet/execute endpoint** (server.py)
4. **Test locally:** `POST /api/gauntlet/execute`
5. **Run Gauntlet:** Watch agents autonomously build Titan Forge
6. **Publish results:** "CrucibAI built Titan Forge in X hours with 100% test pass rate"

---

**End of INTEGRATION_GUIDE.md**
