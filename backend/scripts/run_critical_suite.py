#!/usr/bin/env python3
"""
Master critical test suite runner.
Runs: pricing verification, backend pytest (auth, orchestration, security, chaos, load, gaps, edge),
      frontend tests. Writes JSON report to docs/CRITICAL_TEST_SUITE_RESULTS.json.
Run from repo root: python backend/scripts/run_critical_suite.py
Or from backend: python scripts/run_critical_suite.py (REPO_ROOT inferred).
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# Repo root: script is backend/scripts/run_critical_suite.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND)
DOCS = os.path.join(REPO_ROOT, "docs")
RESULTS_JSON = os.path.join(DOCS, "CRITICAL_TEST_SUITE_RESULTS.json")

# Ensure backend on path for imports
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Test env for pytest (CSRF disabled, high rate limit)
TEST_ENV = os.environ.copy()
TEST_ENV["DISABLE_CSRF_FOR_TEST"] = "1"
TEST_ENV.setdefault("RATE_LIMIT_PER_MINUTE", "99999")
TEST_ENV.setdefault("MONGO_URL", "mongodb://localhost:27017")
TEST_ENV.setdefault("DB_NAME", "crucibai")


def _run(cmd, cwd, timeout=300, env=None):
    env = env or TEST_ENV
    r = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _parse_pytest_summary(stdout):
    """Parse 'X passed, Y failed, Z skipped' from pytest output."""
    # e.g. "==== 42 passed, 2 skipped in 12.34s ====" or "42 passed, 12 failed in 5.00s"
    m = re.search(r"(\d+)\s+passed", stdout)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+failed", stdout)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+skipped", stdout)
    skipped = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+error", stdout)
    errors = int(m.group(1)) if m else 0
    return {"passed": passed, "failed": failed, "skipped": skipped, "errors": errors}


def run_pricing_verification():
    print("=" * 60)
    print("1. PRICING VERIFICATION")
    print("=" * 60)
    code, out, err = _run(
        [sys.executable, os.path.join(BACKEND, "scripts", "run_pricing_verification.py")],
        cwd=BACKEND,
        timeout=120,
    )
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return {"ok": code == 0, "exit_code": code, "output_tail": (out + "\n" + err)[-1500:]}


def run_backend_critical_pytest():
    print("=" * 60)
    print("2. BACKEND CRITICAL PYTEST (auth, orchestration, security, chaos, load, gaps, edge)")
    print("=" * 60)
    tests = [
        "tests/test_pricing_alignment.py",
        "tests/test_single_source_of_truth.py",
        "tests/test_auth.py",
        "tests/test_orchestration_e2e.py",
        "tests/test_security.py",
        "tests/test_chaos.py",
        "tests/test_load.py",
        "tests/test_gaps.py",
        "tests/test_edge_cases.py",
        "tests/test_agents.py",
    ]
    code, out, err = _run(
        [sys.executable, "-m", "pytest"] + tests + ["-v", "--tb=line", "-q"],
        cwd=BACKEND,
        timeout=300,
    )
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    summary = _parse_pytest_summary(out + "\n" + err)
    return {
        "ok": code == 0,
        "exit_code": code,
        "summary": summary,
        "output_tail": (out + "\n" + err)[-2000:],
    }


def run_frontend_tests():
    print("=" * 60)
    print("3. FRONTEND TESTS")
    print("=" * 60)
    frontend = os.path.join(REPO_ROOT, "frontend")
    if not os.path.isdir(frontend):
        return {"ok": False, "exit_code": -1, "output_tail": "frontend/ not found", "summary": {}}
    # On Windows npm may be npm.cmd; use shell so PATH is respected
    cmd = "npm test -- --watchAll=false --no-cache --passWithNoTests"
    try:
        r = subprocess.run(
            cmd,
            cwd=frontend,
            capture_output=True,
            text=True,
            timeout=180,
            env=TEST_ENV,
            shell=True,
        )
        code, out, err = r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except FileNotFoundError:
        return {"ok": False, "exit_code": -1, "output_tail": "npm not found in PATH", "summary": {}}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "output_tail": "Frontend tests timed out", "summary": {}}
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    # Parse "Tests: 32 passed, 32 total" or "Test Suites: 6 passed, 6 total"
    combined = out + "\n" + err
    m = re.search(r"Tests:\s*(\d+)\s+passed", combined)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+total", combined)
    total = int(m.group(1)) if m else passed
    return {
        "ok": code == 0,
        "exit_code": code,
        "summary": {"passed": passed, "total": total},
        "output_tail": combined[-1500:],
    }


def main():
    started = datetime.now(timezone.utc).isoformat()
    results = {
        "started": started,
        "pricing": run_pricing_verification(),
        "backend_pytest": run_backend_critical_pytest(),
        "frontend": run_frontend_tests(),
    }
    results["finished"] = datetime.now(timezone.utc).isoformat()
    results["overall_ok"] = (
        results["pricing"]["ok"]
        and results["backend_pytest"]["ok"]
        and results["frontend"]["ok"]
    )

    os.makedirs(DOCS, exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n" + "=" * 60)
    print("REPORT WRITTEN:", RESULTS_JSON)
    print("Pricing:", "PASS" if results["pricing"]["ok"] else "FAIL")
    print("Backend pytest:", "PASS" if results["backend_pytest"]["ok"] else "FAIL", results["backend_pytest"].get("summary", {}))
    print("Frontend:", "PASS" if results["frontend"]["ok"] else "FAIL", results["frontend"].get("summary", {}))
    print("OVERALL:", "ALL GREEN" if results["overall_ok"] else "SOME FAILURES")
    print("=" * 60)
    return 0 if results["overall_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
