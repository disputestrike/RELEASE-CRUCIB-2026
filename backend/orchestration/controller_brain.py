"""
controller_brain.py - live controller summaries for plans and running jobs.

This is not another executor. It is the single place that translates:
- planned DAG phases into controller metadata
- live job steps/events into UI-facing progress, blockers, and next actions
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List


def build_plan_controller_summary(
    *,
    goal: str,
    phases: List[Dict[str, Any]],
    selected_agents: List[str],
    selection_explanation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    explanation = selection_explanation or {}
    phase_labels = [phase.get("label") or phase.get("key") or "phase" for phase in phases[:12]]
    return {
        "controller_mode": "selective_parallel_swarm" if selected_agents else "fixed_autorunner",
        "goal_excerpt": (goal or "")[:180],
        "selected_agent_count": len(selected_agents or []),
        "specialized_agent_count": int(explanation.get("specialized_agent_count") or 0),
        "matched_keywords": list(explanation.get("matched_keywords") or [])[:12],
        "matched_rules": list(explanation.get("matched_rules") or [])[:12],
        "phase_labels": phase_labels,
        "has_parallel_phases": any(len((phase.get("steps") or [])) > 1 for phase in phases),
        "recovery_strategy": "verification_repair_and_retry",
        "synthesis_strategy": "phase_summary_then_verify",
    }


def _step_progress(step: Dict[str, Any]) -> int:
    status = str(step.get("status") or "").lower()
    if status == "completed":
        return 100
    if status in ("failed", "blocked"):
        return 100
    if status in ("running", "verifying", "retrying"):
        return 50
    if status == "skipped":
        return 100
    return 0


def _normalize_agent_row(step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": step.get("id"),
        "step_key": step.get("step_key"),
        "name": step.get("agent_name") or step.get("step_key") or "Agent",
        "status": step.get("status") or "pending",
        "progress": _step_progress(step),
        "error": step.get("error_message") or "",
        "started_at": step.get("started_at"),
        "completed_at": step.get("completed_at"),
        "phase": step.get("phase") or "unassigned",
    }


def _derive_phase_status(agents: List[Dict[str, Any]]) -> str:
    statuses = [str(agent.get("status") or "").lower() for agent in agents]
    if any(status in ("failed", "blocked") for status in statuses):
        return "error"
    if statuses and all(status in ("completed", "skipped") for status in statuses):
        return "complete"
    if any(status in ("running", "verifying", "retrying") for status in statuses):
        return "running"
    return "queued"


def _event_message(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    event_type = event.get("event_type") or event.get("type") or "event"
    if payload.get("message"):
        return str(payload["message"])
    if payload.get("error"):
        return str(payload["error"])
    if payload.get("failure_reason"):
        return str(payload["failure_reason"])
    if payload.get("agent_name"):
        return f"{payload['agent_name']} {event_type}"
    if payload.get("step_key"):
        return f"{payload['step_key']} {event_type}"
    return event_type.replace("_", " ")


def build_live_job_progress(
    *,
    job: Dict[str, Any] | None,
    steps: List[Dict[str, Any]],
    events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    ordered_phases: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for step in sorted(steps or [], key=lambda row: (int(row.get("order_index") or 0), str(row.get("created_at") or ""))):
        phase_key = str(step.get("phase") or "unassigned")
        ordered_phases.setdefault(phase_key, []).append(_normalize_agent_row(step))

    phases: List[Dict[str, Any]] = []
    for phase_key, agents in ordered_phases.items():
        total = len(agents)
        completed = sum(1 for agent in agents if str(agent.get("status")).lower() in ("completed", "skipped"))
        phase_status = _derive_phase_status(agents)
        phases.append(
            {
                "id": phase_key,
                "name": phase_key.replace("_", " ").title(),
                "status": phase_status,
                "progress": round((completed / total) * 100) if total else 0,
                "completed": completed,
                "total": total,
                "agents": agents,
            }
        )

    total_steps = len(steps or [])
    completed_steps = sum(1 for step in steps or [] if str(step.get("status") or "").lower() in ("completed", "skipped"))
    total_progress = round((completed_steps / total_steps) * 100) if total_steps else 0
    blockers = [
        {
            "step_key": step.get("step_key"),
            "agent_name": step.get("agent_name"),
            "error": step.get("error_message") or "blocked",
        }
        for step in steps or []
        if str(step.get("status") or "").lower() in ("failed", "blocked")
    ]
    current_phase = next((phase["id"] for phase in phases if phase["status"] in ("running", "error")), phases[-1]["id"] if phases else None)
    is_running = str((job or {}).get("status") or "").lower() not in ("completed", "failed", "cancelled") and total_steps > 0

    if blockers:
        next_actions = ["repair_failed_steps", "rerun_verification", "resume_from_checkpoint"]
        controller_status = "attention_required"
    elif is_running:
        next_actions = ["continue_parallel_execution", "synthesize_phase_outputs", "advance_when_dependencies_clear"]
        controller_status = "executing"
    elif phases:
        next_actions = ["publish_proof_bundle", "present_results"]
        controller_status = "completed"
    else:
        next_actions = ["waiting_for_job_steps"]
        controller_status = "idle"

    logs = []
    for event in (events or [])[-50:]:
        payload = event.get("payload") or {}
        logs.append(
            {
                "timestamp": event.get("created_at") or payload.get("timestamp"),
                "type": event.get("event_type") or event.get("type") or "event",
                "agent": payload.get("agent_name") or payload.get("agent") or payload.get("step_key") or "system",
                "message": _event_message(event),
                "level": "error" if (payload.get("error") or payload.get("failure_reason")) else "info",
            }
        )

    return {
        "job_id": (job or {}).get("id"),
        "job_status": (job or {}).get("status") or "unknown",
        "current_phase": current_phase,
        "phases": phases,
        "total_progress": total_progress,
        "is_running": is_running,
        "logs": logs,
        "controller": {
            "status": controller_status,
            "next_actions": next_actions,
            "blocker_count": len(blockers),
            "blockers": blockers[:12],
            "completed_steps": completed_steps,
            "total_steps": total_steps,
        },
    }
