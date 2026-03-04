# Pricing Alignment — Proof of Completion

**Date:** March 2026  
**Scope:** Align all pricing to **free, builder, pro, scale, teams**. Remove **starter** and **light/dev** add-ons. Single source of truth; everything tested.

---

## 1. How to run the full verification

From the **backend** directory:

```bash
python scripts/run_pricing_verification.py
```

This script:

1. Runs **scripts/verify_linear_pricing.py** (CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan).
2. Runs **pytest** for `tests/test_pricing_alignment.py` and the bundles single-source-of-truth test.
3. Prints **confirmed removals** and **in-place** alignment.

**Expected result:** `OVERALL: ALL PRICING CHECKS PASSED` and exit code 0.

---

## 2. What was removed (confirmed by tests)

| Item | Status |
|------|--------|
| **starter** plan | Removed from CREDIT_PLANS |
| **starter** bundle | Removed from TOKEN_BUNDLES |
| **light** / **dev** add-ons | ADDONS = {} (no fixed add-on bundles) |
| **starter** in PLAN_SPEED_ACCESS | Removed from SpeedTierRouter |
| **starter** branch in CreditTracker | Removed (builder+ only) |
| **starter** in TokenPurchaseValidator | Validator rejects `bundle="starter"` |
| **starter** in LLM router | Removed; builder is first paid tier |
| **starter** in admin segment filter doc | Docstring now free\|builder\|pro\|scale\|teams |
| **Starter / light / dev** in frontend FAQ | Landing page FAQ updated to Builder, Pro, Scale, Teams + custom slider |

---

## 3. What is in place (verified)

| Component | Expected |
|-----------|----------|
| **CREDIT_PLANS** keys | `free`, `builder`, `pro`, `scale`, `teams` |
| **TOKEN_BUNDLES** keys | `builder`, `pro`, `scale`, `teams` |
| **PLAN_SPEED_ACCESS** (SpeedTierRouter) | `free`, `builder`, `pro`, `scale`, `teams`; **scale** has lite/pro/max |
| **_speed_from_plan** | free→lite, builder→pro, pro/scale/teams→max; starter→pro (legacy only) |
| **Credits/prices** | free 100/0, builder 250/15, pro 500/30, scale 1000/60, teams 2500/150 |
| **API GET /api/tokens/bundles** | Returns builder, pro, scale, teams with credits, price, name; no starter, light, dev |
| **Validators** | TokenPurchaseValidator accepts builder, pro, scale, teams, custom; rejects starter |
| **Frontend** | Pricing.jsx, TokenCenter.jsx, LandingPage.jsx use builder/pro/scale/teams and custom slider |

---

## 4. Test files and counts

- **tests/test_pricing_alignment.py** — 20 tests: pricing_plans, speed_tier_router, credit_tracker, validators, API bundles.
- **tests/test_single_source_of_truth.py::test_tokens_bundles_returns_200_and_bundles_with_expected_keys** — Bundles content and keys.
- **scripts/verify_linear_pricing.py** — No starter; CREDIT_PLANS/TOKEN_BUNDLES/_speed_from_plan values.

**Total pricing-related assertions:** 22 tests in the verification run; all must pass.

---

## 5. Single source of truth for constants

- **backend/pricing_plans.py** — Defines CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan, ADDONS, ANNUAL_PRICES. No heavy deps (no server import).
- **backend/server.py** — Imports from `pricing_plans`; keeps MIN_CREDITS_FOR_LLM, FREE_TIER_CREDITS.
- **scripts/verify_linear_pricing.py** — Imports from `pricing_plans` only (so it runs without full server stack).

---

## 6. Last verification run (proof)

Run:

```bash
cd backend
python scripts/run_pricing_verification.py
```

You should see:

- `OK: CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan verified.`
- `22 passed` for pytest.
- Section 3 (CONFIRMED REMOVALS & ALIGNMENT) with all `True` and correct keys.
- `OVERALL: ALL PRICING CHECKS PASSED`

This document serves as the proof that all instructed changes are done, removals are confirmed, and alignment is tested and working.
