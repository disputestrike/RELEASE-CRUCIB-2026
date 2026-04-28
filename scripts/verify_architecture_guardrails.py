"""Architecture guardrails verifier."""
from __future__ import annotations
import re as _re
from pathlib import Path
from typing import List


def run_all_guardrails(backend_root: Path) -> List[str]:
    """Run all guardrail checks. Returns list of violation strings (empty = all pass)."""
    violations: List[str] = []

    # Guardrail 1: No direct os.system calls
    for py in backend_root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            text = py.read_text(errors="ignore")
        except Exception:
            continue
        if "os.system(" in text:
            violations.append(f"os.system() in {py.relative_to(backend_root)}")

    # Guardrail 2: No hardcoded live-secret values (skip detection-pattern files)
    _PATTERN_FILES = {"production_gate.py", "secret_management", "check-no-secrets"}
    _LIVE_KEY_PAT = _re.compile(r"sk-live-[0-9a-zA-Z]{30,}")
    for py in backend_root.rglob("*.py"):
        rel = str(py.relative_to(backend_root))
        if "__pycache__" in rel or any(pf in rel for pf in _PATTERN_FILES):
            continue
        try:
            text = py.read_text(errors="ignore")
        except Exception:
            continue
        if _LIVE_KEY_PAT.search(text):
            violations.append(f"Possible hardcoded live key in {rel}")

    # Guardrail 3: Test files outside tests/ must be in an allowed directory
    _ALLOWED_TEST_DIRS = {"orchestration", "benchmarks", "automation"}
    for py in backend_root.rglob("test_*.py"):
        rel = py.relative_to(backend_root)
        parts = rel.parts
        if "tests" not in parts and not any(d in parts for d in _ALLOWED_TEST_DIRS):
            violations.append(f"Test file outside allowed dirs: {rel}")

    return violations
