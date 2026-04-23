"""Compatibility wrapper for backend architecture guardrail checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
_BACKEND_SCRIPT = BACKEND_ROOT / "scripts" / "verify_architecture_guardrails.py"

_spec = importlib.util.spec_from_file_location("backend_verify_architecture_guardrails", _BACKEND_SCRIPT)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def run_all_guardrails(root: Path | None = None):
    """Expose backend guardrail entrypoint under legacy import path."""
    return _module.run_all_guardrails(root)


def main() -> int:
    violations = run_all_guardrails(BACKEND_ROOT)
    if violations:
        print("ARCHITECTURE GUARDRAILS: FAILED")
        for v in violations:
            print(f" - {v}")
        return 1
    print("ARCHITECTURE GUARDRAILS: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
