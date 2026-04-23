#!/usr/bin/env python3
"""
Run pytest -m golden; print JSON score (Fifty-point #43, #50). Non-zero exit if any golden test fails.
CI: called from .github/workflows/ci-verify-full.yml after the full pytest job (golden is a subset).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-path eval runner")
    parser.add_argument(
        "--write-report",
        metavar="PATH",
        help="Write JSON report (e.g. golden_eval_report.json for CI artifacts)",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-m",
        "golden",
        "-q",
        "--tb=short",
        "--ignore=tests/run_production_validation.py",
    ]
    env = os.environ.copy()
    proc = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True, env=env)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")

    m = re.search(r"(\d+)\s+passed", out)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+failed", out)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+error", out)
    errors = int(m.group(1)) if m else 0

    total_ran = passed + failed + errors
    score = 100.0 if total_ran == 0 else round(100.0 * passed / total_ran, 2)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "score_percent": score,
        "exit_code": proc.returncode,
    }
    if total_ran == 0:
        report["note"] = "no golden tests collected — check pytest markers"

    line = json.dumps(report, indent=2)
    print(line)
    if args.write_report:
        with open(args.write_report, "w", encoding="utf-8") as f:
            f.write(line + "\n")

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
