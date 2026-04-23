from __future__ import annotations

from pathlib import Path

from scripts.verify_architecture_guardrails import run_all_guardrails


def test_architecture_guardrails_pass_current_repo():
    backend_root = Path(__file__).resolve().parents[1]
    violations = run_all_guardrails(backend_root)
    assert violations == [], "\n".join(violations)
