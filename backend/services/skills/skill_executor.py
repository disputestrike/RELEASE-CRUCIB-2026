"""Skill execution helpers and policy checks."""

from __future__ import annotations

from typing import Dict, Optional

from services.skills.skill_registry import SkillDef, resolve_skill


def detect_skill(user_text: str) -> Optional[SkillDef]:
    return resolve_skill(user_text)


def skill_allows_tool(skill: SkillDef, tool_name: str) -> bool:
    t = (tool_name or "").lower().strip()
    return t in {x.lower() for x in skill.allowed_tools}


def skill_meta(user_text: str) -> Dict[str, str]:
    s = detect_skill(user_text)
    if not s:
        return {"matched": "false"}
    return {"matched": "true", "skill": s.name}
