"""
Feature-flagged permission engine for tool calls. Version 2.

When CRUCIB_ENABLE_TOOL_POLICY is disabled, decisions are permissive and do not
change existing behavior. When enabled, this engine enforces four layers of
policy before allowing a tool call:

    1. Tool contract allowed_modes gate — rejects tool when called from a
       workspace surface (mode) not listed in its ToolContract.
    2. Skill-scope gate — rejects tool when not in the active SkillDef's
       allowed_tools set.
    3. Per-project policy override — WORKSPACE_ROOT/{project_id}/policy.json
       can force a tool into ask/deny for that project only.
    4. Legacy v1 pattern gates — dangerous-token, ask-token, sensitive-path,
       SSRF local-file URL checks (retained verbatim for backward compat).

PermissionDecision.mode is now an explicit 4-state Literal:

    - "disabled" : policy flag is off, allow and skip enforcement
    - "allow"    : policy passed all gates
    - "ask"      : operator approval required before executing
    - "deny"     : reject outright

``allowed`` stays True only for ``disabled`` and ``allow``; ``ask`` and ``deny``
both return allowed=False. A separate ``ask`` bool is exposed so callers can
distinguish "needs operator confirmation" from "refuse completely" without
string-matching ``mode``.

Backward compat: ``evaluate_tool_call(tool_name, params)`` continues to work.
New kwargs ``surface``, ``skill_name``, ``project_id`` are optional; if omitted,
the corresponding enforcement layer is skipped (v1 behavior).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

DecisionMode = Literal["disabled", "allow", "ask", "deny"]


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    mode: DecisionMode
    ask: bool = False
    layer: str = ""  # Which gate produced this decision; "" for v1 allow path.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "mode": self.mode,
            "ask": self.ask,
            "layer": self.layer,
        }


def _policy_enabled() -> bool:
    return os.environ.get("CRUCIB_ENABLE_TOOL_POLICY", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _contains_dangerous_token(parts: List[str]) -> bool:
    joined = " ".join((p or "") for p in parts).lower()
    blocked_tokens = [
        "rm -rf",
        "del /f",
        "format ",
        "shutdown ",
        "reboot",
        "curl | sh",
        "wget | sh",
    ]
    return any(tok in joined for tok in blocked_tokens)


def _contains_ask_token(parts: List[str]) -> bool:
    """Tokens that should require operator confirmation when policy is enabled."""
    joined = " ".join((p or "") for p in parts).lower()
    ask_tokens = [
        "git push",
        "vercel",
        "deploy",
        "publish",
    ]
    return any(tok in joined for tok in ask_tokens)


def _load_project_policy(project_id: Optional[str]) -> Dict[str, Any]:
    """
    Per-project policy override.

    Expected format at WORKSPACE_ROOT/{project_id}/policy.json:
        {
          "tool_overrides": {
            "run":   { "mode": "ask",  "reason": "project requires approval for shell" },
            "db":    { "mode": "deny", "reason": "read-only project" }
          }
        }

    Silently returns {} on any load/parse error (permissive fallback).
    """
    if not project_id:
        return {}
    try:
        from project_state import WORKSPACE_ROOT
    except Exception:
        return {}
    try:
        safe_pid = (project_id or "").replace("/", "_").replace("\\", "_")
        path = Path(WORKSPACE_ROOT) / safe_pid / "policy.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _contract_mode_allowed(tool_name: str, surface: Optional[str]) -> Optional[PermissionDecision]:
    """
    Layer 1: ToolContract.allowed_modes enforcement.

    Returns deny decision if the tool is called from a surface not in its
    allowed_modes. Returns None if no enforcement applies (no surface supplied,
    contract missing, or contract leaves allowed_modes empty).
    """
    if not surface:
        return None
    try:
        from services.tools import get_tool_contract
    except Exception:
        return None
    contract = get_tool_contract(tool_name)
    if not contract or not contract.allowed_modes:
        return None
    surf = str(surface).strip().lower()
    allowed = [str(m).strip().lower() for m in contract.allowed_modes]
    if surf not in allowed:
        return PermissionDecision(
            allowed=False,
            reason=f"tool '{tool_name}' not allowed in workspace surface '{surf}' (allowed: {', '.join(allowed)})",
            mode="deny",
            layer="contract_mode",
        )
    return None


def _skill_scope_allowed(tool_name: str, skill_name: Optional[str]) -> Optional[PermissionDecision]:
    """
    Layer 2: Skill.allowed_tools enforcement.

    If a skill_name is supplied and the skill is known, reject tool when it is
    not in the skill's allowed_tools set. If skill is not found, return None
    (permissive — tool_executor has its own skill match layer that handles this
    more strictly).
    """
    if not skill_name:
        return None
    try:
        from services.skills.skill_registry import get_skill
    except Exception:
        return None
    skill = get_skill(skill_name)
    if skill is None:
        return None
    tool = (tool_name or "").strip().lower()
    allowed = {str(t).strip().lower() for t in (skill.allowed_tools or set())}
    if allowed and tool not in allowed:
        return PermissionDecision(
            allowed=False,
            reason=f"skill '{skill_name}' does not allow tool '{tool}' (allowed: {', '.join(sorted(allowed))})",
            mode="deny",
            layer="skill_scope",
        )
    return None


def _project_override_decision(tool_name: str, project_id: Optional[str]) -> Optional[PermissionDecision]:
    """
    Layer 3: project-level policy override.

    Returns ask/deny decision if the project config forces one.
    Returns None if no override applies.
    """
    config = _load_project_policy(project_id)
    overrides = (config.get("tool_overrides") or {}) if isinstance(config, dict) else {}
    entry = overrides.get(tool_name)
    if not isinstance(entry, dict):
        return None
    mode = str(entry.get("mode") or "").strip().lower()
    reason = str(entry.get("reason") or "") or f"project override for {tool_name}"
    if mode == "deny":
        return PermissionDecision(
            allowed=False,
            reason=reason,
            mode="deny",
            layer="project_override",
        )
    if mode == "ask":
        return PermissionDecision(
            allowed=False,
            reason=reason,
            mode="ask",
            ask=True,
            layer="project_override",
        )
    return None


def _v1_pattern_decision(tool_name: str, params: Dict[str, Any]) -> PermissionDecision:
    """
    Layer 4 (legacy): preserved from v1 — dangerous-token, ask-token, sensitive
    path, SSRF local file URL.
    """
    t = (tool_name or "").strip().lower()
    if t not in {"file", "run", "api", "browser", "db"}:
        return PermissionDecision(False, f"unknown tool: {t}", "deny", layer="unknown_tool")

    if t == "file":
        action = (params.get("action") or "read").strip().lower()
        path = (params.get("path") or "").strip().lower()
        if action == "write" and (
            path.endswith(".env")
            or path.endswith("id_rsa")
            or "secret" in path
            or "credentials" in path
        ):
            return PermissionDecision(
                False,
                f"blocked write to sensitive path: {path}",
                "deny",
                layer="sensitive_path",
            )

    if t == "run":
        cmd = params.get("command")
        if isinstance(cmd, list):
            cmd_parts = [str(x) for x in cmd]
            if _contains_dangerous_token(cmd_parts):
                return PermissionDecision(
                    False,
                    "blocked dangerous command token",
                    "deny",
                    layer="dangerous_token",
                )
            if _contains_ask_token(cmd_parts):
                return PermissionDecision(
                    False,
                    "operator approval required",
                    "ask",
                    ask=True,
                    layer="ask_token",
                )

    if t in {"api", "browser"}:
        url = str(params.get("url") or "").lower()
        if url.startswith("file://"):
            return PermissionDecision(False, "blocked local file URL", "deny", layer="ssrf_local")

    return PermissionDecision(True, "allowed by policy", "allow", layer="default_allow")


def evaluate_tool_call(
    tool_name: str,
    params: Dict[str, Any],
    *,
    surface: Optional[str] = None,
    skill_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> PermissionDecision:
    """
    Evaluate whether a tool call should be allowed.

    Layers applied in order (short-circuit on first non-None):

      1. Policy flag off       -> disabled / allow
      2. ToolContract.allowed_modes vs surface   -> deny if violated
      3. SkillDef.allowed_tools vs tool_name     -> deny if violated
      4. Per-project policy override             -> ask or deny
      5. v1 pattern gates                        -> allow / ask / deny

    Backward compat: callers passing (tool_name, params) only get the v1
    behavior plus the default-allow result; optional kwargs light up the
    richer v2 enforcement.
    """
    if not _policy_enabled():
        return PermissionDecision(
            allowed=True,
            reason="tool policy disabled",
            mode="disabled",
            layer="flag_off",
        )

    for layer_fn_result in (
        _contract_mode_allowed(tool_name, surface),
        _skill_scope_allowed(tool_name, skill_name),
        _project_override_decision(tool_name, project_id),
    ):
        if layer_fn_result is not None:
            return layer_fn_result

    return _v1_pattern_decision(tool_name, params or {})
