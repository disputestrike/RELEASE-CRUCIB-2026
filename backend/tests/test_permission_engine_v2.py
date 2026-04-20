"""
Tests for permission_engine v2 — mode gating, skill scope, project overrides.

Covers the four new enforcement layers on top of v1 patterns. Each test sets
CRUCIB_ENABLE_TOOL_POLICY=1 via monkeypatch and relies on the in-repo
ToolContract registry and SkillDef registry.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Make backend/ importable when running pytest from repo root or from backend/.
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.policy import permission_engine as pe  # noqa: E402
from services.policy.permission_engine import (  # noqa: E402
    PermissionDecision,
    evaluate_tool_call,
)


@pytest.fixture(autouse=True)
def _enable_policy(monkeypatch):
    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    yield


def test_disabled_flag_short_circuits(monkeypatch):
    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "0")
    d = evaluate_tool_call("run", {"command": ["rm", "-rf", "/"]})
    assert d.allowed is True
    assert d.mode == "disabled"
    assert d.layer == "flag_off"


def test_v1_dangerous_token_still_denies():
    d = evaluate_tool_call("run", {"command": ["rm -rf", "/"]})
    assert d.allowed is False
    assert d.mode == "deny"
    assert d.layer == "dangerous_token"


def test_v1_ask_token_sets_ask_flag():
    d = evaluate_tool_call("run", {"command": ["git push", "origin", "main"]})
    assert d.allowed is False
    assert d.mode == "ask"
    assert d.ask is True
    assert d.layer == "ask_token"


def test_v1_default_allow_when_safe():
    d = evaluate_tool_call("file", {"action": "read", "path": "src/index.js"})
    assert d.allowed is True
    assert d.mode == "allow"
    assert d.layer == "default_allow"


# ── Layer 1: contract allowed_modes gate ──────────────────────────────────────
def test_layer1_contract_mode_denies_when_surface_not_allowed():
    # 'db' contract allowed_modes = ['guided', 'inspect', 'repair'] — surface
    # 'what-if' is not in that list, so this must deny.
    d = evaluate_tool_call(
        "db",
        {"action": "query", "sql": "SELECT 1"},
        surface="what-if",
    )
    assert d.allowed is False
    assert d.mode == "deny"
    assert d.layer == "contract_mode"
    assert "what-if" in d.reason


def test_layer1_contract_mode_allows_when_surface_matches():
    # 'api' contract allowed_modes includes 'inspect'.
    d = evaluate_tool_call(
        "api",
        {"url": "https://example.com"},
        surface="inspect",
    )
    assert d.allowed is True
    assert d.mode == "allow"


def test_layer1_missing_surface_skips_gate():
    # No surface supplied -> layer 1 returns None, falls through to v1 default.
    d = evaluate_tool_call("db", {"action": "query", "sql": "SELECT 1"})
    # v1 doesn't deny db, so this allows.
    assert d.allowed is True
    assert d.layer == "default_allow"


# ── Layer 2: skill scope gate ─────────────────────────────────────────────────
def test_layer2_skill_scope_denies_when_tool_not_in_allowed_tools():
    # Skill 'plan' has allowed_tools={'file'} — 'run' is not in there.
    d = evaluate_tool_call(
        "run",
        {"command": ["ls"]},
        skill_name="plan",
    )
    assert d.allowed is False
    assert d.mode == "deny"
    assert d.layer == "skill_scope"
    assert "plan" in d.reason


def test_layer2_skill_scope_allows_when_tool_in_allowed_tools():
    # Skill 'commit' has allowed_tools={'run', 'file'} — 'file' is in there.
    d = evaluate_tool_call(
        "file",
        {"action": "read", "path": "README.md"},
        skill_name="commit",
    )
    assert d.allowed is True
    assert d.mode == "allow"


def test_layer2_unknown_skill_is_permissive():
    # Unknown skill name → layer 2 returns None (defer to downstream).
    d = evaluate_tool_call(
        "file",
        {"action": "read", "path": "README.md"},
        skill_name="nonexistent-skill-xyz",
    )
    assert d.allowed is True


# ── Layer 3: per-project policy override ──────────────────────────────────────
def test_layer3_project_override_forces_deny(tmp_path, monkeypatch):
    from project_state import WORKSPACE_ROOT  # noqa: WPS433

    proj = "policy-override-test-deny"
    root = Path(WORKSPACE_ROOT) / proj
    root.mkdir(parents=True, exist_ok=True)
    (root / "policy.json").write_text(
        json.dumps({"tool_overrides": {"db": {"mode": "deny", "reason": "read-only project"}}}),
        encoding="utf-8",
    )

    d = evaluate_tool_call(
        "db",
        {"action": "query"},
        project_id=proj,
    )
    assert d.allowed is False
    assert d.mode == "deny"
    assert d.layer == "project_override"
    assert "read-only project" in d.reason


def test_layer3_project_override_forces_ask(tmp_path):
    from project_state import WORKSPACE_ROOT  # noqa: WPS433

    proj = "policy-override-test-ask"
    root = Path(WORKSPACE_ROOT) / proj
    root.mkdir(parents=True, exist_ok=True)
    (root / "policy.json").write_text(
        json.dumps({"tool_overrides": {"run": {"mode": "ask", "reason": "confirm shell"}}}),
        encoding="utf-8",
    )

    d = evaluate_tool_call(
        "run",
        {"command": ["ls"]},
        project_id=proj,
    )
    assert d.allowed is False
    assert d.mode == "ask"
    assert d.ask is True
    assert d.layer == "project_override"


def test_layer3_missing_project_policy_is_permissive():
    d = evaluate_tool_call(
        "file",
        {"action": "read", "path": "README.md"},
        project_id="project-that-has-no-policy-json",
    )
    # v1 default_allow path
    assert d.allowed is True


# ── Integration: layer precedence ─────────────────────────────────────────────
def test_precedence_contract_before_skill_before_project():
    # Surface denies BEFORE skill scope runs. db + what-if should deny at layer 1
    # even though skill 'plan' would also deny it at layer 2.
    d = evaluate_tool_call(
        "db",
        {"action": "query"},
        surface="what-if",
        skill_name="plan",
    )
    assert d.layer == "contract_mode"


def test_decision_to_dict_is_jsonable():
    d = evaluate_tool_call("file", {"action": "read", "path": "README.md"})
    out = d.to_dict()
    assert out["mode"] == "allow"
    assert out["layer"] == "default_allow"
    json.dumps(out)  # must not raise
