"""Permission mode state machine.

Adapted from claude-code-source-code/src/utils/permissions/getNextPermissionMode.ts.
Defines graduated permission modes and the legal transitions between them.

Modes (least → most permissive):
    default        — prompt on anything risky
    plan           — read-only plan mode; no writes, no bash
    accept_edits   — auto-approve FS writes in workspace, ask for bash
    bypass         — no prompts, still blocks hard-blocked bash patterns
    yolo           — no prompts at all (admin-only)
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Optional


class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    ACCEPT_EDITS = "accept_edits"
    BYPASS = "bypass"
    YOLO = "yolo"


# Legal transitions — safer to more-permissive requires ladder; can always drop
# back to DEFAULT from anywhere. YOLO requires admin_role.
_LEGAL: Dict[PermissionMode, FrozenSet[PermissionMode]] = {
    PermissionMode.DEFAULT:      frozenset({PermissionMode.PLAN, PermissionMode.ACCEPT_EDITS}),
    PermissionMode.PLAN:         frozenset({PermissionMode.DEFAULT, PermissionMode.ACCEPT_EDITS}),
    PermissionMode.ACCEPT_EDITS: frozenset({PermissionMode.DEFAULT, PermissionMode.PLAN, PermissionMode.BYPASS}),
    PermissionMode.BYPASS:       frozenset({PermissionMode.DEFAULT, PermissionMode.ACCEPT_EDITS, PermissionMode.YOLO}),
    PermissionMode.YOLO:         frozenset({PermissionMode.DEFAULT, PermissionMode.BYPASS}),
}


def can_transition(current: PermissionMode, target: PermissionMode, *, admin: bool = False) -> bool:
    """Return True if `current -> target` is allowed."""
    if current == target:
        return True
    if target == PermissionMode.DEFAULT:
        return True  # safety-downshift always legal
    if target == PermissionMode.YOLO and not admin:
        return False
    return target in _LEGAL.get(current, frozenset())


def next_mode(current: PermissionMode, *, direction: str = "up", admin: bool = False) -> Optional[PermissionMode]:
    """Cycle through modes. direction: 'up' (more permissive) or 'down'."""
    ladder = [PermissionMode.PLAN, PermissionMode.DEFAULT, PermissionMode.ACCEPT_EDITS,
              PermissionMode.BYPASS, PermissionMode.YOLO]
    try:
        idx = ladder.index(current)
    except ValueError:
        return PermissionMode.DEFAULT
    if direction == "up":
        while idx + 1 < len(ladder):
            idx += 1
            if ladder[idx] == PermissionMode.YOLO and not admin:
                continue
            return ladder[idx]
        return None
    if direction == "down":
        return ladder[idx - 1] if idx - 1 >= 0 else None
    return None


def describe(mode: PermissionMode) -> str:
    return {
        PermissionMode.DEFAULT:      "Prompt on risky actions (writes + bash).",
        PermissionMode.PLAN:         "Read-only planning mode. No writes, no bash.",
        PermissionMode.ACCEPT_EDITS: "Auto-approve workspace writes. Still ask for bash.",
        PermissionMode.BYPASS:       "No prompts. Hard-blocked bash patterns still rejected.",
        PermissionMode.YOLO:         "No prompts at all. Admin only.",
    }[mode]
