# Proof weighting — presence demoted for routes / production readiness

## 1. Production readiness score (`truth_scores.py`)

**File:** `backend/orchestration/truth_scores.py` — `compute_production_readiness()`

**Change:** Route bundle contribution is **conditional on a runtime hint** in flat proof:

- Counts `route_n` from `bundle["routes"]`.
- Sets `has_runtime_route` if any flat item has `payload.check == "health_endpoint"` or title contains `"api smoke"`.
- If `route_n > 0`:
  - **With** runtime hint: `score += min(12, 4 + route_n)` and reason `route_proof_with_runtime_hint`
  - **Without** runtime hint: `score += min(4, 2 + max(1, route_n // 2))` and reason `route_proof_structure_only_demoted`

**Before/after interpretation:** Declared routes alone no longer earn the same cap as routes backed by health/API smoke evidence.

## 2. Elite builder gate — critical features

**File:** `backend/orchestration/elite_builder_gate.py`

For goals tagged **tenancy**, the gate requires vocabulary suggesting **tests or runtime** in the delivery classification text, not merely migration/RLS **presence** (see `test_tenancy_goal_gate_fails_when_classification_has_no_runtime_hints`).

## 3. Existing proof checks (unchanged but complementary)

`compute_production_readiness` already gives higher weight to checks such as:

- `tenancy_isolation_proven`
- `stripe_webhook_idempotency_proven`
- `rbac_escalation_blocked` / `rbac_anonymous_blocked`

Those remain the **strong** signals vs. title-only or file-presence proofs.

## 4. Example: presence-only routes

| Scenario | Approx. route contribution |
|----------|----------------------------|
| 5 routes in bundle, no health/smoke proof | `min(4, …)` — demoted |
| 5 routes + health_endpoint proof | `min(12, …)` — full branch |

## 5. Test evidence

- `test_tenancy_goal_gate_fails_when_classification_has_no_runtime_hints` — elite gate fails on structure-only tenancy wording.
- Behavior verification: `tests/test_behavior_verification.py` — deploy depends on `verification.elite_builder` (completion ordering).
