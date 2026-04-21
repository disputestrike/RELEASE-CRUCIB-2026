"""CF25 — tests for the permission rule shadowed-rule linter."""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.permissions.rule_linter import lint_rules


def test_detects_shadow():
    findings = lint_rules(["Bash(npm:*)", "Bash(npm install:*)"])
    assert len(findings) == 1
    assert findings[0].shadowed == "Bash(npm install:*)"
    assert findings[0].by == "Bash(npm:*)"


def test_no_shadow_across_tools():
    findings = lint_rules(["Bash(npm:*)", "Write(src/**)"])
    assert findings == []


def test_exact_match_not_shadowed():
    findings = lint_rules(["Bash(git status)", "Bash(git log)"])
    assert findings == []
