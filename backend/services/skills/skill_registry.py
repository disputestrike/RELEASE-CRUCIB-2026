"""Skill registry with trigger matching and tool constraints.

Skills are the first-class execution objects that map user intent to a
controlled set of allowed tools.  Every agent invocation should resolve
to a skill so that the permission engine can enforce tool boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class SkillDef:
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    allowed_tools: Set[str] = field(default_factory=set)
    # Surface hint — matches workspace surface modes (build/inspect/etc.)
    surface: Optional[str] = None


_BUILTINS: Dict[str, SkillDef] = {
    # ── Code-level skills ──────────────────────────────────────────────────
    "commit": SkillDef(
        name="commit",
        description="Review git state and prepare a safe commit.",
        triggers=["/commit", "commit changes", "make a commit", "git commit"],
        allowed_tools={"run", "file"},
        surface="build",
    ),
    "review": SkillDef(
        name="review",
        description="Review code changes for correctness, security, and tests.",
        triggers=["/review", "review this", "code review", "review code"],
        allowed_tools={"file", "run"},
        surface="inspect",
    ),
    # ── Build surface skills ───────────────────────────────────────────────
    "plan": SkillDef(
        name="plan",
        description="Analyse the request and produce a structured execution plan.",
        triggers=["/plan", "plan this", "make a plan", "create a plan", "plan out"],
        allowed_tools={"file"},
        surface="build",
    ),
    "build": SkillDef(
        name="build",
        description="Build, scaffold, or generate code/files for the project.",
        triggers=[
            "/build",
            "build this",
            "scaffold",
            "generate code",
            "write the code",
            "implement",
        ],
        allowed_tools={"file", "run"},
        surface="build",
    ),
    "test": SkillDef(
        name="test",
        description="Run tests and report results.",
        triggers=[
            "/test",
            "run tests",
            "run the tests",
            "execute tests",
            "pytest",
            "jest",
        ],
        allowed_tools={"run", "file"},
        surface="build",
    ),
    # ── Deploy surface skills ──────────────────────────────────────────────
    "deploy": SkillDef(
        name="deploy",
        description="Deploy the application to a target environment.",
        triggers=["/deploy", "deploy this", "push to production", "ship it"],
        allowed_tools={"run", "api"},
        surface="deploy",
    ),
    # ── Inspect surface skills ─────────────────────────────────────────────
    "inspect": SkillDef(
        name="inspect",
        description="Inspect, audit, or analyse existing code or system state.",
        triggers=[
            "/inspect",
            "inspect this",
            "audit",
            "analyse",
            "analyze",
            "what is going on",
            "explain this",
        ],
        allowed_tools={"file", "run"},
        surface="inspect",
    ),
    # ── What-if surface skills ─────────────────────────────────────────────
    "what_if": SkillDef(
        name="what_if",
        description="Simulate or reason about a hypothetical scenario without side effects.",
        triggers=[
            "/what-if",
            "what if",
            "simulate",
            "hypothetically",
            "what would happen",
        ],
        allowed_tools={"file"},
        surface="what-if",
    ),
    # ── Repair surface skills ──────────────────────────────────────────────
    "repair": SkillDef(
        name="repair",
        description="Diagnose and fix failures, errors, or broken state.",
        triggers=[
            "/repair",
            "repair this",
            "fix this",
            "debug",
            "broken",
            "not working",
            "error in",
        ],
        allowed_tools={"file", "run", "db"},
        surface="repair",
    ),
}


def list_skills() -> List[SkillDef]:
    """Return all registered skills."""
    return list(_BUILTINS.values())


def resolve_skill(user_text: str) -> Optional[SkillDef]:
    """Return the first skill whose triggers match ``user_text``, or None."""
    t = (user_text or "").lower()
    for skill in _BUILTINS.values():
        if any(trigger in t for trigger in skill.triggers):
            return skill
    return None


def get_skill(name: str) -> Optional[SkillDef]:
    """Look up a skill by exact name."""
    return _BUILTINS.get(name)


def skill_names() -> List[str]:
    """Return all registered skill names."""
    return list(_BUILTINS.keys())
