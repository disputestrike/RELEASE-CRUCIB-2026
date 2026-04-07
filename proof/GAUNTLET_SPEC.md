# 🎯 TITAN FORGE CONTROL — GAUNTLET SPECIFICATION

**Status:** CrucibAI Test Prompt v1.0

**Objective:** Build a multi-tenant SaaS platform with honest verification and no scaffolding.

---

## SYSTEM OVERVIEW

**Name:** Titan Forge Control

**Purpose:** Multi-tenant operations platform for solar/energy field services. Demonstrates AI-powered recommendations with human approval gates.

**Target:** Prove that CrucibAI can build production-ready systems with real tests and honest verification.

---

## ARCHITECTURE REQUIREMENTS

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Style:** Tailwind CSS
- **Components:** Shadcn/ui where applicable
- **Pages:**
  - Customer portal (login, dashboard, lead capture)
  - Admin portal (user management, reporting)
  - Role-based navigation

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (prod) / SQLite (dev)
- **ORM:** SQLAlchemy 2 async
- **Auth:** JWT + refresh token rotation
- **Deployment:** Railway ready

### Infrastructure
- **Git:** All code in GitHub (disputestrike/TitanForge repo)
- **Database Migrations:** Alembic
- **Environment:** .env for secrets (NEVER committed)

---

## PHASE 1: SPECIFICATION (YOU ARE HERE)

### Phase 1 Deliverables
- [ ] Architecture document
- [ ] 13 trap map (known failure modes + prevention)
- [ ] GDPR vs audit conflict resolution
- [ ] AI approval boundary (hardcoded rules)
- [ ] Runtime limits honestly stated

**Status:** Phase 1 must be 100% complete before Phase 2.

---

## PHASE 2: FOUNDATION (4-6 hours)

### 2.1 Authentication
- JWT access tokens (15-min expiry)
- Refresh tokens (7-day expiry)
- Password hashing (Argon2id)
- Token rotation endpoint

**Requirements:**
- Login endpoint: POST /api/auth/login
- Refresh endpoint: POST /api/auth/refresh
- User info endpoint: GET /api/auth/me
- Logout with audit trail

**Proof:**
- test_foundation.py::TestAuthentication (8 tests)
- FOUNDATION_AUDIT.md with code excerpts

### 2.2 RBAC (Role-Based Access Control)
- 6 roles: global_admin, org_admin, operator, sales_rep, viewer, customer
- Permission enforcement on endpoints
- Role assignment UI

**Requirements:**
- Role model with permission JSON
- UserRole join table
- @require_permission() decorator
- Role assignment endpoints

**Proof:**
- test_foundation.py::TestRBAC (4 tests)
- All roles testable without login

### 2.3 Multi-Tenancy
- org_id on every table
- Query filtering by org_id
- JWT encodes org_id
- Cross-org isolation test

**Requirements:**
- Organization model
- org_id foreign key on users, roles, audit_logs, etc.
- Middleware injects org_id from token
- No cross-org data leakage

**Proof:**
- test_foundation.py::TestMultiTenancy (2 tests)
- TENANCY_VERIFICATION.md

### 2.4 Encryption
- AES-256-GCM via Fernet
- Master key from environment ONLY (never in DB)
- Per-org DEK (Data Encryption Key)
- Key wrapper table (encrypted DEK storage)

**Requirements:**
- CryptoService class
- encrypt_field() / decrypt_field() methods
- KeyWrapper table with encrypted_dek column
- No plaintext keys in code or DB

**Proof:**
- test_foundation.py::TestEncryption (3 tests)
- CRYPTO_VERIFICATION.md
- Grep for MASTER_KEY in code: 0 results

### 2.5 Audit Chain
- SHA256 hash chain (immutable log)
- Every action logged (login, approve, create, etc.)
- Hash chain verification method
- Audit endpoint

**Requirements:**
- AuditLog model with prev_hash, current_hash
- Create log → compute hash, link to previous
- verify_chain() checks integrity
- GET /api/audit/chain/verify endpoint

**Proof:**
- test_foundation.py::TestAuditChain (7 tests)
- Audit login recorded + hash chain verified

### 2.6 Database Schema
- 9 tables minimum
- Foreign key constraints enforced
- Proper NULL/NOT NULL
- Alembic migration ready

**Requirements:**
- organizations, users, roles, user_roles, audit_logs, key_wrappers
- SessionLocal + Base for SQLAlchemy
- migrations/ folder with Alembic setup

**Proof:**
- All tables created on startup
- Constraints enforced
- Schema in FOUNDATION_AUDIT.md

**Phase 2 End State:**
- ✅ Real authentication (not scaffolding)
- ✅ Real RBAC (not theater)
- ✅ Real tenancy (not fake isolation)
- ✅ Real encryption (not mock keys)
- ✅ Real audit (not silent failures)
- ✅ 35+ tests passing
- ✅ 3 proof documents

---

## PHASE 3: BUSINESS LOGIC (6-8 hours)

### 3.1 CRM Entities
```
Leads → Accounts → Opportunities → Quotes → Projects → Tasks
```

**Models:**
- Lead (name, email, phone, source, status)
- Account (company_name, address, owner_id)
- Opportunity (account_id, value, stage, close_date)
- Quote (opportunity_id, total_price, line_items[], status)
- Project (quote_id, address, start_date, end_date)
- Task (project_id, title, assigned_to, status)

### 3.2 Quote Approval Workflow
```
draft → pending_review → approved / rejected / expired
```

**Rules:**
- AI recommends discount (separate table: ai_recommendations)
- Human must approve (separate table: approvals)
- DB constraint: policy_decisions require approval_status == APPROVED
- Recommendation ≠ enforcement (core Trap #1)

### 3.3 AI Recommendation Engine
**Separate from enforcement:**
- Table: ai_recommendations (org_id, quote_id, recommended_action, reasoning, confidence)
- Cannot directly mutate quote status
- Must be reviewed by human
- All recommendations logged

**Example:**
```
Quote #123: suggested 15% discount
Reasoning: customer is high-value (3 projects past year)
Confidence: 92%
Human review: APPROVED or REJECTED
```

### 3.4 Policy Engine
**Rules table:**
- policy_id, org_id, rule_name, rule_type (discount_limit, payment_term, etc.)
- conditions: JSON ({"quote_value": ">5000", "customer_tier": "gold"})
- action: JSON ({"max_discount": 0.20, "payment_term": 30})
- approval_required: boolean

**Enforcement:**
- Rule evaluation: do conditions match?
- If matches: recommend action (not enforce)
- If approval_required: add to approval queue
- Human approves → then apply

### 3.5 Async Jobs
**BullMQ queue for:**
- email notifications (send_quote_approval_email)
- report generation (generate_monthly_report)
- integration callbacks (call_crm_webhook)

**Idempotency:**
- Every job has idempotency_key
- If job failed, retry with same key
- Database deduplicates

### 3.6 Integration Adapters
**All mocked, all labeled with is_mock=True:**
- CRM webhook: POST to /webhook/crm/{org_id}
- Solar API: GET /api/solar/feasibility/{address}
- Email provider: POST /send_email

**Proof:**
- Every mock has `is_mock=True` flag
- Config toggles real vs mock
- Tests verify flag set

**Phase 3 End State:**
- ✅ Full CRM pipeline (leads → projects)
- ✅ Quote workflow with approvals
- ✅ AI recommendations (separate from enforcement)
- ✅ Policy engine
- ✅ Async jobs with retry
- ✅ All mocks labeled
- ✅ 50+ new tests
- ✅ 3 proof documents (integration, AI boundary, async)

---

## PHASE 4: VERIFICATION (2-4 hours)

### 4.1 Migration Safety
- Test: rollback migrations
- Test: data integrity after rollback
- Test: forward migration works again

### 4.2 Adversarial Resistance
- Test: attempt cross-org data access → 403
- Test: attempt to skip approval gate → 403
- Test: attempt to enforce without approval → 403

### 4.3 Concurrency Safety
- Test: 50 parallel quote updates (idempotency key prevents duplicates)
- Test: audit chain integrity under concurrent writes
- Test: race condition on quote approval

### 4.4 Analytics Trust
- Every metric has `proof_snapshot_id`
- Metrics are re-runnable
- GET /api/analytics/verify returns proof

### 4.5 Final Proof Bundle
**Output:**
- ELITE_DELIVERY_CERT.md (signed declaration)
- TEST_RESULTS.md (all test passes)
- CHANGES.md (what was built, what wasn't)
- phase4_verify.sh (runnable test script)

**Status Codes:**
```bash
./phase4_verify.sh
# Output: ✅ ELITE VERIFIED
# or: ❌ CRITICAL BLOCK (with reason)
```

**Phase 4 End State:**
- ✅ All migrations tested
- ✅ Adversarial attacks blocked
- ✅ Concurrency tests pass
- ✅ Analytics verified
- ✅ Final proof bundle signed
- ✅ Deployment ready

---

## 🎯 THE 13 TRAPS (Known Failure Modes)

| ID | Trap | Prevention | Test |
|----|------|-----------|------|
| T1 | Recommendation vs Enforcement | Separate tables + DB constraint | approve quote → must have approval record |
| T2 | Multi-Tenant Data Leak | org_id FK on every table; query filter | query Org A → no Org B data |
| T3 | Async Duplicate Transitions | Idempotency keys + terminal state guard | 50 parallel updates → only one wins |
| T4 | Mock Integration Honesty | All mocks labeled `is_mock=True` | config check → mocks declared |
| T5 | Analytics Trust | Every metric has `proof_snapshot_id` | re-run query → same result |
| T6 | Spec Honesty | IMPLEMENTED/SCAFFOLDED/STUBBED matrix | delivery cert lists all 3 |
| T7 | GDPR vs Audit Conflict | Tombstone + hash chain (redaction event) | delete user PII → audit log shows redaction |
| T8 | Crypto Key Mishandling | Master key from env only | grep DB for MASTER_KEY → 0 |
| T9 | Migration Corruption | Rollback test + data integrity check | rollback then forward → same schema |
| T10 | Adversarial Override | AI boundary hardcoded (no policy enforcement without approval) | force enforce → 403 |
| T11 | Race Condition Silent Failures | Pessimistic locking + serializable txns | concurrency test → no duplicates |
| T12 | Proof Without Reality | /health endpoint + migrations run | curl /health → 200 |
| T13 | Hidden Auto-Enforcement | Grep all enforce calls; all require approval | grep enforce → all checks approval_status |

---

## 🎨 GDPR vs AUDIT CONFLICT RESOLUTION

**Conflict:** User requests deletion (GDPR) but audit trail says we must keep all records.

**Solution: Three-Layer Strategy**

1. **Redaction Event (not deletion)**
   - Mark user PII fields as redacted: email, phone, address → NULL
   - Add column `redacted=True` to user record
   - Keeps user_id for FK integrity

2. **Hash Chain Preserved**
   - SHA256 hashes in audit_logs stay intact
   - Redaction is logged as separate event
   - Hash chain unbroken

3. **Redaction Itself Audited**
   - New audit log: action="user_redaction", actor_id="system", timestamp, details
   - Linked to previous audit log via hash chain

**Proof:**
- Test: user deletion request
- Verify: user.email = NULL, user.redacted = True
- Verify: audit_log entry for redaction
- Verify: hash chain still valid

---

## 🔐 AI APPROVAL BOUNDARY (Hardcoded Rule)

**AI can:**
- Recommend actions (store in ai_recommendations table)
- Draft content (quotes, emails)
- Score leads (store in lead_score table)
- Flag risky deals
- Summarize data

**AI CANNOT:**
- Approve quotes (requires human)
- Enforce policies (requires human approval)
- Apply compliance actions (requires human)
- Mutate protected state (is_approved, policy_enforced, etc.)
- Elevate user privileges

**Implementation:**
```python
# Separate tables: AI recommendations are READ-ONLY to AI
ai_recommendations = Table("ai_recommendations", ...)  # AI can INSERT
approvals = Table("approvals", ...)  # Only humans can INSERT

# DB constraint: policy enforcement requires approval
ALTER TABLE policy_decisions ADD CONSTRAINT 
  CHECK (approval_status = 'APPROVED');

# Code: All enforce() calls check permission
def enforce_policy(policy_id, actor_id):
    approval = db.query(Approval).filter(
        Approval.policy_id == policy_id,
        Approval.approval_status == "APPROVED"
    ).first()
    if not approval:
        raise PermissionError("Policy not approved")
```

**Test:**
- AI tries to call enforce_policy() → 403
- Human approves → enforce_policy() succeeds

---

## ✅ HONEST RUNTIME LIMITS

**What we build:**
- ✅ Multi-tenant system (truly isolated)
- ✅ Auth + RBAC (real enforcement)
- ✅ Quote workflow (working UI + backend)
- ✅ AI recommendations (separate from enforcement)
- ✅ Async jobs (with retry)
- ✅ Audit trail (immutable)

**What we DON'T build (Phase 5+):**
- ❌ Mobile app (scope creep)
- ❌ Real solar API integration (use mocks)
- ❌ Advanced analytics (dashboard UI only)
- ❌ Multi-region support (single region)
- ❌ High-frequency trading (not a trading system)

---

## 📊 SUCCESS CRITERIA

**Phase 2:**
- ✅ 35+ tests pass
- ✅ 660 lines of real code
- ✅ 0 plaintext secrets in DB
- ✅ Audit chain verified

**Phase 3:**
- ✅ 50+ new tests pass
- ✅ 2,000 new lines of code
- ✅ Quote workflow end-to-end
- ✅ AI boundary enforced (test: AI cannot approve)

**Phase 4:**
- ✅ Migrations safe (rollback tested)
- ✅ Adversarial attacks blocked (cross-org test)
- ✅ Concurrency safe (50 parallel updates)
- ✅ Final proof bundle signed

**Overall:**
```bash
./phase4_verify.sh
# Output: ✅ ELITE VERIFIED
```

---

## 📝 DELIVERABLE CHECKLIST

- [ ] Phase 1: ELITE_ANALYSIS.md (done: /proof/ELITE_ANALYSIS.md)
- [ ] Phase 1: TRAP_MAP.md (done: /proof/TRAP_MAP.md)
- [ ] Phase 1: ARCHITECTURE.md (done: /proof/ARCHITECTURE.md)
- [ ] Phase 1: COMPLIANCE_TRADEOFF.md (done: /proof/COMPLIANCE_TRADEOFF.md)

- [ ] Phase 2: backend/titan_forge_main.py (660 lines)
- [ ] Phase 2: tests/test_foundation.py (35+ tests)
- [ ] Phase 2: proof/FOUNDATION_AUDIT.md
- [ ] Phase 2: proof/TENANCY_VERIFICATION.md
- [ ] Phase 2: proof/CRYPTO_VERIFICATION.md

- [ ] Phase 3: backend/models/ (CRM entities)
- [ ] Phase 3: backend/routes/ (API endpoints)
- [ ] Phase 3: backend/jobs/ (async jobs)
- [ ] Phase 3: tests/test_business_logic.py (50+ tests)
- [ ] Phase 3: proof/INTEGRATION_PROOF.md
- [ ] Phase 3: proof/AI_APPROVAL_BOUNDARY.md
- [ ] Phase 3: proof/ASYNC_CONSISTENCY.md
- [ ] Phase 3: proof/ANALYTICS_TRUST.md

- [ ] Phase 4: tests/test_migrations.py
- [ ] Phase 4: tests/test_adversarial.py
- [ ] Phase 4: tests/test_concurrency.py
- [ ] Phase 4: proof/MIGRATION_SAFETY.md
- [ ] Phase 4: proof/SECURITY_AUDIT.md
- [ ] Phase 4: proof/TEST_RESULTS.md
- [ ] Phase 4: proof/CHANGES.md
- [ ] Phase 4: proof/ELITE_DELIVERY_CERT.md
- [ ] Phase 4: scripts/phase4_verify.sh (exit 0 or 1)

---

## 🚀 FINAL DELIVERABLE

After all 4 phases:

**GitHub Repo:** disputestrike/TitanForge
- Main branch: full working system
- Branch: gauntlet-elite-run: proof artifacts

**Proof Bundle:**
- ELITE_DELIVERY_CERT.md (signed)
- 150+ page combined proof documents
- phase4_verify.sh (returns ✅ or ❌)

**Benchmark Ready:**
- "CrucibAI built Titan Forge in 18 hours"
- "100% test pass rate, 0 security issues"
- "All code honest, all tests real"

---

**End of GAUNTLET_SPEC.md**

**Next:** CrucibAI receives this spec and autonomously executes Phase 2-4.
