"""Skills package — re-exports for legacy callers + new file-based MD loader.

IMPORTANT: `detect_skill` must remain exported from this package. The WS-A
file-based loader introduced Skill / SkillRegistry but consumers like
services.llm_service still import `detect_skill` from backend.services.skills.
"""

# Legacy executor-level API (used by services.llm_service, routes.skills, etc.)
from .skill_executor import detect_skill, skill_allows_tool, skill_meta  # noqa: F401
from .skill_registry import SkillDef, resolve_skill  # noqa: F401

# WS-A file-based MD loader
from .md_loader import Skill, SkillRegistry, get_registry  # noqa: F401

__all__ = [
    # legacy
    "detect_skill",
    "skill_allows_tool",
    "skill_meta",
    "SkillDef",
    "resolve_skill",
    # WS-A
    "Skill",
    "SkillRegistry",
    "get_registry",
]
