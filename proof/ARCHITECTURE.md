# 🏗️ ARCHITECTURE: Titan Forge Technical Design

**Status:** Phase 1 Analysis Complete

## Quick Ref: System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js App Router)           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Auth Flow │ Dashboard │ CRM │ Quotes │ Policy │ Audit │  │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ JWT + Org Header
┌────────────────────────▼────────────────────────────────────┐
│              FastAPI Backend (Async)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Auth │ RBAC │ Tenancy │ CRM │ AI │ Policy │ Jobs   │    │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL
┌────────────────────────▼────────────────────────────────────┐
│         PostgreSQL (Production) / SQLite (Dev)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Auth │ Tenancy │ CRM │ Policy │ Audit │ Crypto     │    │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Multi-Tenancy: Application-Layer + Optional RLS

Every table has `org_id` foreign key. Enforced at application layer (every query filters by org).
Optional: Enable PostgreSQL RLS for defense-in-depth.

### 2. AI Boundary: Separate Tables + Approval Gate

Recommendations and enforcement are in separate tables.
No AI can approve or enforce; only recommend.
Database constraints prevent enforcement without approval.

### 3. Audit Trail: Hash Chain + GDPR Redaction

Every critical action logged with SHA256 hash chain.
GDPR deletion: redact PII, preserve hash chain integrity.

### 4. Encryption: Master Key from Environment

Master key never persisted in DB.
Per-org DEK encrypted with master key.
All credentials encrypted before storage.

### 5. Async: Idempotent + Terminal State Guards

All background jobs track idempotency keys.
Terminal states (approved, rejected) cannot be re-entered.
Retries check previous state before acting.

---

## Phase 1 Artifact Checklist

- ✅ ELITE_ANALYSIS.md (this document + runtime limits)
- ✅ TRAP_MAP.md (13 failure modes + prevention)
- ✅ ARCHITECTURE.md (this file: design decisions)
- ✅ COMPLIANCE_TRADEOFF.md (GDPR vs audit)

**Next Phase:** Phase 2 (Foundation) begins with:
- Auth system implementation
- RBAC enforcement
- Tenancy middleware
- Encryption module
- Audit chain setup
