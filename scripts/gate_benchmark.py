#!/usr/bin/env python3
"""Compare latest benchmark results to baseline and exit non-zero on regression.

Rules:
- Any previously-passing case that now fails           -> REGRESSION (exit 2)
- Any suite whose pass_count dropped                   -> REGRESSION (exit 2)
- Any top-level increase in fail_count vs baseline     -> REGRESSION (exit 2)
- If baseline does not exist, create it from latest and exit 0 (first-run).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def idx_cases(report):
    """Build {(suite, case_id): pass_bool} dict for comparison."""
    out = {}
    for s in report.get("suites", []):
        for c in s.get("cases", []):
            out[(s.get("suite", "?"), c.get("id", "?"))] = bool(c.get("pass"))
    return out


def idx_suite_passes(report):
    return {s.get("suite", "?"): int(s.get("pass", 0)) for s in report.get("suites", [])}


def main():
    if len(sys.argv) != 3:
        print("usage: gate_benchmark.py <latest.json> <baseline.json>", file=sys.stderr)
        sys.exit(64)
    latest_p, baseline_p = sys.argv[1], sys.argv[2]
    latest = load(latest_p)
    bp = Path(baseline_p)
    if not bp.exists():
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(Path(latest_p).read_text())
        print(f"[gate] no baseline — established from {latest_p}")
        sys.exit(0)
    baseline = load(baseline_p)

    regressions = []
    # Case-level regressions
    l_cases = idx_cases(latest)
    b_cases = idx_cases(baseline)
    for key, was_pass in b_cases.items():
        if was_pass and not l_cases.get(key, False):
            regressions.append(f"case regressed: {key[0]}::{key[1]}")
    # Suite-level pass count drop
    l_suites = idx_suite_passes(latest)
    b_suites = idx_suite_passes(baseline)
    for suite, b_pass in b_suites.items():
        l_pass = l_suites.get(suite, 0)
        if l_pass < b_pass:
            regressions.append(f"suite {suite}: pass {b_pass} -> {l_pass}")
    # Overall fail count increase
    if int(latest.get("fail_count", 0)) > int(baseline.get("fail_count", 0)):
        regressions.append(
            f"total fail count: {baseline.get('fail_count',0)} -> {latest.get('fail_count',0)}"
        )

    if regressions:
        print("[gate] FAIL — regressions:")
        for r in regressions:
            print(f"  - {r}")
        sys.exit(2)

    print(f"[gate] PASS — {latest.get('pass_count',0)} passing, {latest.get('fail_count',0)} failing, no regressions vs baseline")
    sys.exit(0)


if __name__ == "__main__":
    main()
