"""
Phase optimizer for CrucibAI — optimizes build phase ordering/selection.
Given DAG phases and optional build_kind / project context, returns reordered or filtered phases
for more efficient builds.
"""
from typing import List, Tuple, Dict, Any, Optional


def optimize_phases(
    phases: List[Tuple[int, List[str]]],
    build_kind: str = "fullstack",
    project_context: Optional[Dict[str, Any]] = None,
) -> List[Tuple[int, List[str]]]:
    """
    Optimize phase ordering/selection. phases is list of (phase_idx, [agent_names]).
    Returns phases (possibly reordered or with agents reordered within phase for priority).
    Current implementation: returns phases as-is; can be extended to reorder by critical path
    or skip phases for minimal builds.
    """
    if not phases:
        return []
    # Optional: for "minimal" or "bot" build_kind, filter to fewer phases (e.g. Planner, Stack, Frontend only)
    if build_kind in ("bot", "ai_agent") and project_context:
        # Could return only first N phases
        pass
    return list(phases)


def get_phase_priority_agents(phase_agent_names: List[str], build_kind: str = "fullstack") -> List[str]:
    """
    Within a phase, return agent names in priority order (e.g. critical agents first).
    Default: return as-is.
    """
    return list(phase_agent_names)
