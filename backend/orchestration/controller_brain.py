"""
controller_brain.py - live controller summaries for plans and running jobs.

This is not another executor. It is the single place that translates:
- planned DAG phases into controller metadata
- live job steps/events into UI-facing progress, blockers, and next actions
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List


def _truncate_text(value: Any, limit: int = 220) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)]}..."


def _phase_steps(phase: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(phase.get("steps") or [])


def _phase_parallel_groups(phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    for phase in phases or []:
        steps = _phase_steps(phase)
        if len(steps) <= 1:
            continue
        groups.append(
            {
                "phase": phase.get("key") or phase.get("label") or "phase",
                "label": phase.get("label") or phase.get("key") or "phase",
                "step_count": len(steps),
                "agents": [
                    step.get("agent") or step.get("name") or step.get("key") or "Agent"
                    for step in steps[:8]
                ],
            }
        )
    return groups[:8]


def _build_plan_next_actions(
    selected_agents: List[str], phases: List[Dict[str, Any]]
) -> List[str]:
    if not selected_agents:
        return ["scaffold_primary_pack", "compile_preview_bundle", "verify_core_routes"]

    actions = [
        "launch_parallel_specialists",
        "synthesize_phase_outputs",
        "run_verification_gates",
    ]
    if any(len(_phase_steps(phase)) > 1 for phase in phases or []):
        actions.insert(1, "continue_dependency_aware_parallelism")
    return actions


def build_plan_controller_summary(
    *,
    goal: str,
    phases: List[Dict[str, Any]],
    selected_agents: List[str],
    selection_explanation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    explanation = selection_explanation or {}
    phase_labels = [
        phase.get("label") or phase.get("key") or "phase" for phase in phases[:12]
    ]
    parallel_groups = _phase_parallel_groups(phases)
    specialized_agents = list(explanation.get("specialized_agents") or [])[:12]
    return {
        "controller_mode": (
            "selective_parallel_swarm" if selected_agents else "fixed_autorunner"
        ),
        "goal_excerpt": (goal or "")[:180],
        "selected_agent_count": len(selected_agents or []),
        "specialized_agent_count": int(explanation.get("specialized_agent_count") or 0),
        "matched_keywords": list(explanation.get("matched_keywords") or [])[:12],
        "matched_rules": list(explanation.get("matched_rules") or [])[:12],
        "phase_labels": phase_labels,
        "has_parallel_phases": any(
            len((phase.get("steps") or [])) > 1 for phase in phases
        ),
        "recovery_strategy": "verification_repair_and_retry",
        "synthesis_strategy": "phase_summary_then_verify",
        "execution_strategy": (
            "dependency_aware_parallelism" if parallel_groups else "sequenced_execution"
        ),
        "parallel_groups": parallel_groups,
        "recommended_focus": specialized_agents or list(selected_agents or [])[:8],
        "synthesis_checkpoints": (
            phase_labels[-3:] if len(phase_labels) >= 3 else phase_labels
        ),
        "replan_triggers": [
            "verification failure",
            "agent blocker detected",
            "missing runtime artifact",
        ],
        "next_actions": _build_plan_next_actions(selected_agents, phases),
        "memory_strategy": "scoped_project_job_phase_memory",
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
        "error": _truncate_text(step.get("error_message") or "", limit=180),
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
        return _truncate_text(payload["message"], limit=240)
    if payload.get("error"):
        return _truncate_text(payload["error"], limit=240)
    if payload.get("failure_reason"):
        return _truncate_text(payload["failure_reason"], limit=240)
    if payload.get("agent_name"):
        return f"{payload['agent_name']} {event_type}"
    if payload.get("step_key"):
        return f"{payload['step_key']} {event_type}"
    return event_type.replace("_", " ")


def _derive_recovery_plan(blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for blocker in blockers[:6]:
        error_text = str(blocker.get("error") or "").lower()
        agent_text = str(
            blocker.get("agent_name") or blocker.get("step_key") or ""
        ).lower()
        if any(word in error_text for word in ("preview", "vite", "compile", "import")):
            action = "run_build_validator_and_preview_repair"
        elif any(
            word in error_text for word in ("security", "cors", "headers", "validation")
        ) or any(
            word in agent_text
            for word in ("security", "cors", "headers", "validation", "rate limiting")
        ):
            action = "run_security_hardening_pass"
        elif any(word in error_text for word in ("timeout", "retry")):
            action = "retry_with_repair_context"
        else:
            action = "inspect_blocker_and_resume"
        plan.append(
            {
                "step_key": blocker.get("step_key"),
                "agent_name": blocker.get("agent_name"),
                "action": action,
            }
        )
    return plan


def _derive_recommended_focus(
    *,
    blockers: List[Dict[str, Any]],
    active_agents: List[str],
    queued_agents: List[str],
) -> str:
    if blockers:
        lead = blockers[0]
        return f"Unblock {lead.get('agent_name') or lead.get('step_key')}"
    if active_agents:
        return f"Watch {' + '.join(active_agents[:3])}"
    if queued_agents:
        return f"Advance {queued_agents[0]}"
    return "Await new work"


def _get_agent_description(agent_key: str) -> str:
    """Map technical agent keys to human-readable Manus-style descriptions."""
    mapping = {
        "scaffold": "Scaffolding project structure",
        "frontend.generate": "Generating frontend components",
        "frontend.styling": "Applying design tokens and CSS",
        "backend.models": "Designing database models",
        "backend.routes": "Implementing API endpoints",
        "backend.auth": "Configuring authentication",
        "verification.preview": "Verifying build bundle",
        "verification.routes": "Testing API health",
        "verification.security": "Running security audit",
    }
    return mapping.get(agent_key.lower(), f"Executing {agent_key.replace('_', ' ')}")


def build_live_job_progress(
    *,
    job: Dict[str, Any] | None,
    steps: List[Dict[str, Any]],
    events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    # ── Manus-style Task Progress Card ────────────────────────────────────────
    task_progress = []
    current_idx = 0
    for i, s in enumerate(steps or []):
        status = str(s.get("status") or "pending").lower()
        if status in ("running", "verifying", "retrying"):
            current_idx = i
        task_progress.append({
            "index": i,
            "description": _get_agent_description(str(s.get("step_key") or "")),
            "status": status
        })

    # ── Manus-style Action Chips ──────────────────────────────────────────────
    action_chips = []
    for i in range(current_idx, min(len(steps or []), current_idx + 3)):
        s = steps[i]
        action_chips.append({
            "action": _get_agent_description(str(s.get("step_key") or "")),
            "status": str(s.get("status") or "pending").lower(),
            "icon": "file" if "generate" in str(s.get("step_key") or "") else "arrow"
        })

    ordered_phases: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for step in sorted(
        steps or [],
        key=lambda row: (
            int(row.get("order_index") or 0),
            str(row.get("created_at") or ""),
        ),
    ):
        phase_key = str(step.get("phase") or "unassigned")
        ordered_phases.setdefault(phase_key, []).append(_normalize_agent_row(step))

    phases: List[Dict[str, Any]] = []
    for phase_key, agents in ordered_phases.items():
        total = len(agents)
        completed = sum(
            1
            for agent in agents
            if str(agent.get("status")).lower() in ("completed", "skipped")
        )
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
    completed_steps = sum(
        1
        for step in steps or []
        if str(step.get("status") or "").lower() in ("completed", "skipped")
    )
    total_progress = round((completed_steps / total_steps) * 100) if total_steps else 0
    active_agents = [
        step.get("agent_name") or step.get("step_key") or "Agent"
        for step in steps or []
        if str(step.get("status") or "").lower() in ("running", "verifying", "retrying")
    ]
    queued_agents = [
        step.get("agent_name") or step.get("step_key") or "Agent"
        for step in steps or []
        if str(step.get("status") or "").lower() in ("queued", "pending")
    ]
    blockers = [
        {
            "step_key": step.get("step_key"),
            "agent_name": step.get("agent_name"),
            "error": _truncate_text(step.get("error_message") or "blocked", limit=180),
        }
        for step in steps or []
        if str(step.get("status") or "").lower() in ("failed", "blocked")
    ]
    current_phase = next(
        (phase["id"] for phase in phases if phase["status"] in ("running", "error")),
        phases[-1]["id"] if phases else None,
    )
    is_running = (
        str((job or {}).get("status") or "").lower()
        not in ("completed", "failed", "cancelled")
        and total_steps > 0
    )
    parallel_phases = [phase for phase in phases if len(phase.get("agents") or []) > 1]
    repair_plan = _derive_recovery_plan(blockers)

    if blockers:
        next_actions = [
            "repair_failed_steps",
            "rerun_verification",
            "resume_from_checkpoint",
        ]
        controller_status = "attention_required"
    elif is_running:
        next_actions = [
            "continue_parallel_execution",
            "synthesize_phase_outputs",
            "advance_when_dependencies_clear",
        ]
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
                "agent": payload.get("agent_name")
                or payload.get("agent")
                or payload.get("step_key")
                or "system",
                "message": _event_message(event),
                "level": (
                    "error"
                    if (payload.get("error") or payload.get("failure_reason"))
                    else "info"
                ),
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
        "task_progress": {
            "total": len(steps or []),
            "current": current_idx + 1,
            "percentage": total_progress,
            "summary": _get_agent_description(str(steps[current_idx].get("step_key") or "")) if steps and current_idx < len(steps) else "Initializing...",
            "label": _get_agent_description(str(steps[current_idx].get("step_key") or "")) if steps and current_idx < len(steps) else "Initializing...",
            "detail": _event_message(events[-1]) if events else "Waiting for orchestrator...",
            "current_step": steps[current_idx].get("step_key") if steps and current_idx < len(steps) else None,
            "next_steps": [s.get("step_key") for s in steps[current_idx+1:current_idx+4]] if steps and current_idx < len(steps) else [],
            "tasks": task_progress
        },
        "action_chips": action_chips,
        "controller": {
            "status": controller_status,
            "state": controller_status,
            "current_focus": _derive_recommended_focus(
                blockers=blockers,
                active_agents=active_agents,
                queued_agents=queued_agents,
            ),
            "recommendation": repair_plan if blockers else "Continue with current plan.",
            "next_actions": next_actions,
            "blocker_count": len(blockers),
            "blockers": blockers[:12],
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "active_agents": active_agents[:12],
            "active_agent_count": len(active_agents),
            "queued_agents": queued_agents[:12],
            "queued_agent_count": len(queued_agents),
            "recommended_focus": _derive_recommended_focus(
                blockers=blockers,
                active_agents=active_agents,
                queued_agents=queued_agents,
            ),
            "repair_plan": repair_plan,
            "parallel_phase_count": len(parallel_phases),
            "parallel_phases": [
                {
                    "id": phase["id"],
                    "agent_count": len(phase.get("agents") or []),
                    "active_agents": [
                        agent.get("name")
                        for agent in (phase.get("agents") or [])
                        if str(agent.get("status") or "").lower()
                        in ("running", "verifying", "retrying")
                    ][:6],
                }
                for phase in parallel_phases[:6]
            ],
        },
    }
