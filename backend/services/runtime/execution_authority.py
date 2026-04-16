"""Global execution authority for runtime-engine-owned execution.

This module is the single source of truth for whether execution is allowed.
All executors and legacy orchestration paths must validate here.
"""

from __future__ import annotations

from typing import Any, Dict, List

from services.runtime.execution_context import (
    current_project_id,
    current_skill_hint,
    current_task_id,
)


class ExecutionAuthorityError(PermissionError):
    """Raised when execution is attempted outside runtime authority."""


def require_runtime_authority(
    component: str,
    *,
    detail: str = "execution",
    error_cls: type[Exception] = ExecutionAuthorityError,
) -> None:
    """Fail unless the current code is running inside runtime_engine context."""
    if not current_task_id() or not current_project_id():
        raise error_cls(
            f"{component} {detail} forbidden outside runtime_engine context"
        )


def runtime_authority_snapshot() -> Dict[str, str | None]:
    """Return current runtime ownership metadata for debugging and tracing."""
    return {
        "project_id": current_project_id(),
        "task_id": current_task_id(),
        "skill_hint": current_skill_hint(),
    }


def build_runtime_native_step_defs(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build runtime-native step records without using DAG planning.

    The plan is treated as an ordered execution intent list, not a graph.
    """
    ordered_agents = []
    for key in ("selected_agents", "prioritized_agents", "recommended_agents", "agents"):
        value = plan.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    ordered_agents.append(item.strip())

    phases = plan.get("phases") if isinstance(plan.get("phases"), list) else []

    steps: List[Dict[str, Any]] = []
    if ordered_agents:
        for idx, agent_name in enumerate(ordered_agents, start=1):
            steps.append(
                {
                    "step_key": f"runtime.step.{idx}",
                    "agent_name": agent_name,
                    "phase": phases[idx - 1] if idx - 1 < len(phases) else "runtime_execution",
                    "depends_on": [],
                }
            )

    if not steps:
        steps.append(
            {
                "step_key": "runtime.step.1",
                "agent_name": "RuntimeEngine",
                "phase": "runtime_execution",
                "depends_on": [],
            }
        )
    return steps