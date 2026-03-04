#!/usr/bin/env python3
"""
Run all pricing alignment checks and tests. Proof that:
- Plans: free, builder, pro, scale, teams (NO starter)
- Bundles: builder, pro, scale, teams only (NO light/dev add-ons)
- Speed tier access and _speed_from_plan aligned
- Credit tracker has no starter branch; validators reject starter
"""
import os
import sys
import subprocess

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
os.chdir(BACKEND)


def run_verify_linear_pricing():
    """Run scripts/verify_linear_pricing.py (uses pricing_plans only, no server)."""
    print("=" * 60)
    print("1. VERIFY LINEAR PRICING (CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan)")
    print("=" * 60)
    code = subprocess.run(
        [sys.executable, os.path.join(BACKEND, "scripts", "verify_linear_pricing.py")],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=15,
    )
    out = (code.stdout or "").strip()
    err = (code.stderr or "").strip()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    if code.returncode != 0:
        print("FAILED: verify_linear_pricing exited with", code.returncode)
        return False
    print("PASSED: Linear pricing verified.\n")
    return True


def run_pricing_tests():
    """Run pytest for test_pricing_alignment and related tests."""
    print("=" * 60)
    print("2. PYTEST: test_pricing_alignment + bundles single-source-of-truth")
    print("=" * 60)
    code = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/test_pricing_alignment.py",
            "tests/test_single_source_of_truth.py::test_tokens_bundles_returns_200_and_bundles_with_expected_keys",
            "-v",
            "--tb=short",
            "-q",
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(code.stdout or "")
    if code.stderr:
        print(code.stderr, file=sys.stderr)
    if code.returncode != 0:
        print("FAILED: some tests failed.")
        return False
    print("PASSED: All pricing alignment tests passed.\n")
    return True


def print_removal_confirmation():
    print("=" * 60)
    print("3. CONFIRMED REMOVALS & ALIGNMENT")
    print("=" * 60)
    from pricing_plans import CREDIT_PLANS, TOKEN_BUNDLES, ADDONS, _speed_from_plan
    from speed_tier_router import SpeedTierRouter

    print("REMOVED:")
    print("  - 'starter' plan: not in CREDIT_PLANS:", "starter" not in CREDIT_PLANS)
    print("  - 'starter' bundle: not in TOKEN_BUNDLES:", "starter" not in TOKEN_BUNDLES)
    print("  - 'light' / 'dev' add-ons: ADDONS empty:", ADDONS == {})
    print("  - PLAN_SPEED_ACCESS has no 'starter':", "starter" not in SpeedTierRouter.PLAN_SPEED_ACCESS)

    print("IN PLACE:")
    print("  - CREDIT_PLANS keys:", list(CREDIT_PLANS.keys()))
    print("  - TOKEN_BUNDLES keys:", list(TOKEN_BUNDLES.keys()))
    print("  - PLAN_SPEED_ACCESS keys:", list(SpeedTierRouter.PLAN_SPEED_ACCESS.keys()))
    print("  - _speed_from_plan(free)=lite, builder=pro, pro/scale/teams=max:",
          _speed_from_plan("free") == "lite" and _speed_from_plan("builder") == "pro"
          and _speed_from_plan("pro") == "max" and _speed_from_plan("scale") == "max")
    print()


def main():
    ok1 = run_verify_linear_pricing()
    ok2 = run_pricing_tests()
    print_removal_confirmation()
    if ok1 and ok2:
        print("=" * 60)
        print("OVERALL: ALL PRICING CHECKS PASSED")
        print("=" * 60)
        return 0
    print("OVERALL: SOME CHECKS FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
