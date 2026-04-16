"""
Feature-flagged permission engine for tool calls.

When CRUCIB_ENABLE_TOOL_POLICY is disabled, decisions are permissive and do not
change existing behavior. When enabled, this engine can block risky calls with
clear reasons for auditability.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    mode: str  # "disabled" | "allow" | "deny"


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


def evaluate_tool_call(tool_name: str, params: Dict[str, Any]) -> PermissionDecision:
    """
    Evaluate whether a tool call should be allowed.

    Default is non-breaking:
    - disabled: always allow
    - enabled: deny only clearly unsafe patterns
    """
    if not _policy_enabled():
        return PermissionDecision(
            allowed=True,
            reason="tool policy disabled",
            mode="disabled",
        )

    t = (tool_name or "").strip().lower()
    if t not in {"file", "run", "api", "browser", "db"}:
        return PermissionDecision(False, f"unknown tool: {t}", "deny")

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
            )

    if t == "run":
        cmd = params.get("command")
        if isinstance(cmd, list):
            cmd_parts = [str(x) for x in cmd]
            if _contains_dangerous_token(cmd_parts):
                return PermissionDecision(False, "blocked dangerous command token", "deny")
            if _contains_ask_token(cmd_parts):
                return PermissionDecision(False, "operator approval required", "ask")

    if t in {"api", "browser"}:
        url = str(params.get("url") or "").lower()
        if url.startswith("file://"):
            return PermissionDecision(False, "blocked local file URL", "deny")

    return PermissionDecision(True, "allowed by policy", "allow")
