#!/usr/bin/env python3
"""
Run proof tests on THIS codebase (no external services required).
Usage: cd backend && python run_proof_tests.py

Runs:
- test_orchestration_e2e.py (quality score, agent failure recovery, DAG phases — all mocked, no DB/LLM)
and reports pass/fail. Exit 0 if all pass.
"""

import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("CrucibAI proof tests (this repo only, no DB/API keys)\n")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_orchestration_e2e.py",
            "-v",
            "--tb=short",
        ],
        cwd=os.getcwd(),
        timeout=120,
    )
    if r.returncode == 0:
        print(
            "\n[PASS] Orchestration E2E: quality score, failure recovery, DAG phases OK."
        )
    else:
        print("\n[FAIL] Some tests failed.")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
