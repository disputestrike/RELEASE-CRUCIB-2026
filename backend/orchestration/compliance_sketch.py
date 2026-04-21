"""
High-level compliance checklist artifact — educational only, not legal advice.
Emitted when goals suggest regulated domains (fintech, healthcare, etc.).
"""

from __future__ import annotations


def build_compliance_sketch_markdown(goal_excerpt: str) -> str:
    ex = ((goal_excerpt or "").strip()[:400] or "(no goal text)").replace("\n", " ")

    return f"""# Compliance sketch (NOT legal advice)

**CrucibAI Auto-Runner** generated this workspace from a goal that may imply regulated data or payments.
This file is **not** a certification, policy, or substitute for counsel.

## Goal excerpt (for traceability)

> {ex}

## Before handling regulated data or money

- [ ] **Data classification** — what you store (PII, PHI, payment metadata) and where
- [ ] **Retention + deletion** — documented schedules and erasure procedures
- [ ] **Vendor agreements** — DPAs, BAAs, subprocessors as applicable
- [ ] **Encryption** — at rest (KMS) and in transit (TLS); key rotation
- [ ] **Access control** — least privilege, MFA for admins, audit logs
- [ ] **Incident response** — breach notification aligned with your jurisdiction

## Payments (if you process cards or move funds)

- [ ] **PCI scope** — SAQ / ROC path with your acquirer; no PAN/CVC in app logs or non-PCI storage
- [ ] **Webhooks** — signature verification + idempotency (see `stripe_events_processed` sketch if present)
- [ ] **Settlement / reconciliation** — finance-owned processes

## Healthcare / PHI (if applicable)

- [ ] **HIPAA** — BAAs, minimum necessary, access logging, workforce training
- [ ] **No PHI in client-side logs** or third-party analytics without review

---

Replace this sketch with **your** security & compliance program. Delete this file when superseded.

_Schema: crucibai.compliance_sketch/v1_
"""
