"""
Master test runner: 5-Layer Production Validation.
Run: cd backend && python -m pytest tests/test_endpoint_mapping.py tests/test_webhook_flows.py tests/test_data_integrity.py tests/test_user_journeys.py tests/test_security.py -v --tb=short
Or:  cd backend && python tests/run_production_validation.py

Note: Tests that use auth (register + protected routes) may hit async DB "Future attached to a different loop"
when run in-process. For full pass, start the backend (uvicorn server:app) then run pytest with
CRUCIBAI_API_URL=http://localhost:8000 (and use a client that hits that URL instead of ASGITransport).
"""

import subprocess
import sys
import os
from datetime import datetime

# Run from backend directory
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LAYERS = [
    ("Layer 1: Endpoint mapping", "tests/test_endpoint_mapping.py"),
    ("Layer 2: Webhook & event flow", "tests/test_webhook_flows.py"),
    ("Layer 3: Data integrity", "tests/test_data_integrity.py"),
    ("Layer 4: User journeys", "tests/test_user_journeys.py"),
    ("Layer 5: Security", "tests/test_security.py"),
]


def run_layer(name, path):
    """Run pytest for one layer. Returns (passed, failed, status)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", path, "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        out = result.stdout + result.stderr
        passed = out.count(" PASSED") + out.count(" passed")
        failed = out.count(" FAILED") + out.count(" failed")
        if result.returncode != 0 and failed == 0:
            failed = 1
        status = "PASS" if result.returncode == 0 else "FAIL"
        return status, passed, failed, out
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 0, 1, "Layer timed out"
    except Exception as e:
        return "ERROR", 0, 1, str(e)


def main():
    print("\n" + "=" * 70)
    print("  PRODUCTION VALIDATION - 5-LAYER TEST SUITE")
    print("=" * 70)
    results = []
    total_pass, total_fail = 0, 0
    for name, path in LAYERS:
        print(f"\n  {name} ({path})")
        status, passed, failed, out = run_layer(name, path)
        total_pass += passed
        total_fail += failed
        results.append((name, status, passed, failed))
        icon = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {status}  (passed: {passed}, failed: {failed})")
        if status != "PASS" and out:
            for line in out.splitlines()[-15:]:
                print(f"     {line}")
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name, status, passed, failed in results:
        icon = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {name}: {status}")
    print(f"\n  TOTAL: {total_pass} passed | {total_fail} failed")
    all_ok = all(r[1] == "PASS" for r in results)
    print(f"  VERDICT: {'ALL SYSTEMS GO' if all_ok else 'ISSUES FOUND'}")
    print("=" * 70 + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
