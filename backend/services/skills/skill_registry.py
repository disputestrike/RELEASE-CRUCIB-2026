"""Lightweight skill registry with trigger matching and tool constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class SkillDef:
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    allowed_tools: Set[str] = field(default_factory=set)


_BUILTINS: Dict[str, SkillDef] = {
    "commit": SkillDef(
        name="commit",
        description="Review git state and prepare a safe commit.",
        triggers=["/commit", "commit changes", "make a commit"],
        allowed_tools={"run", "file"},
    ),
    "review": SkillDef(
        name="review",
        description="Review code changes for correctness, security, and tests.",
        triggers=["/review", "review this", "code review"],
        allowed_tools={"file", "run"},
    ),
}


def list_skills() -> List[SkillDef]:
    return list(_BUILTINS.values())


def resolve_skill(user_text: str) -> Optional[SkillDef]:
    t = (user_text or "").lower()
    for skill in _BUILTINS.values():
        if any(trigger in t for trigger in skill.triggers):
            return skill
    return None
