#!/usr/bin/env python3
"""Verify linear pricing implementation: CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan, optional API checks."""

import os
import sys

# Run from backend so server can be imported
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
os.chdir(BACKEND)


def main():
    from pricing_plans import CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan

    errors = []

    # No starter in CREDIT_PLANS
    if "starter" in CREDIT_PLANS:
        errors.append("CREDIT_PLANS must not contain 'starter'")

    # Expected plans and values (credits, price)
    expected = {
        "free": (100, 0),
        "builder": (250, 15),
        "pro": (500, 30),
        "scale": (1000, 60),
        "teams": (2500, 150),
    }
    for plan, (credits, price) in expected.items():
        if plan not in CREDIT_PLANS:
            errors.append(f"CREDIT_PLANS missing '{plan}'")
        else:
            c = CREDIT_PLANS[plan]
            if c.get("credits") != credits:
                errors.append(
                    f"CREDIT_PLANS['{plan}'].credits = {c.get('credits')}, expected {credits}"
                )
            if c.get("price") != price:
                errors.append(
                    f"CREDIT_PLANS['{plan}'].price = {c.get('price')}, expected {price}"
                )

    # TOKEN_BUNDLES keys exactly builder, pro, scale, teams
    want_bundles = {"builder", "pro", "scale", "teams"}
    got_bundles = set(TOKEN_BUNDLES.keys())
    if got_bundles != want_bundles:
        errors.append(f"TOKEN_BUNDLES keys = {got_bundles}, expected {want_bundles}")

    # _speed_from_plan
    speed_checks = [
        ("free", "lite"),
        ("builder", "pro"),
        ("pro", "max"),
        ("scale", "max"),
        ("teams", "max"),
    ]
    for plan, expected_speed in speed_checks:
        got = _speed_from_plan(plan)
        if got != expected_speed:
            errors.append(
                f"_speed_from_plan('{plan}') = '{got}', expected '{expected_speed}'"
            )

    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1

    print("OK: CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
