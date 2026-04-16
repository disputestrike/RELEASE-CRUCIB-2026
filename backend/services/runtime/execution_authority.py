"""Minimal runtime authority helpers for the surviving single-runtime stack."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from services.runtime.execution_context import (
    current_project_id,
    current_skill_hint,
    current_task_id,
)


def runtime_authority_snapshot() -> Dict[str, Any]:
    """Return the current runtime-owned execution scope."""
    return {
        "project_id": current_project_id(),
        "task_id": current_task_id(),
        "skill_hint": current_skill_hint(),
        "runtime_active": bool(current_project_id() and current_task_id()),
    }


def require_runtime_authority(source: str, detail: str = "execution") -> Dict[str, Any]:
    """Enforce that execution only happens inside a runtime-owned scope."""
    snapshot = runtime_authority_snapshot()
    if not snapshot["runtime_active"]:
        raise PermissionError(
            f"runtime_engine_required: source={source} detail={detail}"
        )
    return snapshot


def build_runtime_native_step_defs(plan: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    """Normalize a planner payload into the runtime step contract."""
    if not isinstance(plan, dict):
        return [_default_step()]

    phases = plan.get("phases")
    if not isinstance(phases, list) or not phases:
        return [_step_from_plan(plan, phase_name="runtime", order_index=0)]

    out: List[Dict[str, Any]] = []
    order_index = 0
    for phase_idx, phase in enumerate(phases, start=1):
        phase_name = _phase_name(phase, phase_idx)
        steps = _phase_steps(phase)
        if not steps:
            continue
        for step in steps:
            out.append(
                _step_from_plan(
                    step,
                    phase_name=phase_name,
                    order_index=order_index,
                )
            )
            order_index += 1

    return out or [_default_step()]


def _default_step() -> Dict[str, Any]:
    return {
        "step_key": "runtime.execute",
        "agent_name": "Runtime Engine",
        "phase": "runtime",
        "depends_on": [],
    }


def _phase_name(phase: Any, phase_idx: int) -> str:
    if isinstance(phase, dict):
        for key in ("phase", "name", "id", "title"):
            value = str(phase.get(key) or "").strip()
            if value:
                return value
    return f"phase_{phase_idx}"


def _phase_steps(phase: Any) -> List[Any]:
    if isinstance(phase, dict):
        raw = phase.get("steps")
        if isinstance(raw, list):
            return raw
    if isinstance(phase, list):
        return phase
    return []


def _step_from_plan(step: Any, *, phase_name: str, order_index: int) -> Dict[str, Any]:
    if not isinstance(step, dict):
        label = str(step or "").strip() or f"step_{order_index + 1}"
        return {
            "step_key": _normalize_step_key(label, order_index),
            "agent_name": label,
            "phase": phase_name,
            "depends_on": [],
        }

    label = _first_non_empty(
        step,
        ("step_key", "key", "agent_name", "agent", "name", "title", "id"),
        default=f"step_{order_index + 1}",
    )
    agent_name = _first_non_empty(
        step,
        ("agent_name", "agent", "name", "title", "step_key", "key", "id"),
        default=label,
    )
    depends_on = step.get("depends_on")
    if not isinstance(depends_on, list):
        depends_on = []
    return {
        "step_key": _normalize_step_key(label, order_index),
        "agent_name": agent_name,
        "phase": phase_name,
        "depends_on": [str(item) for item in depends_on if str(item).strip()],
    }


def _first_non_empty(data: Dict[str, Any], keys: Iterable[str], *, default: str) -> str:
    for key in keys:
        value = str(data.get(key) or "").strip()
        if value:
            return value
    return default


def _normalize_step_key(value: str, order_index: int) -> str:
    raw = str(value or "").strip().lower().replace(" ", ".")
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "." for ch in raw)
    cleaned = ".".join(part for part in cleaned.split(".") if part)
    return cleaned or f"runtime.step_{order_index + 1}"