from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


def planner_project_state_service(user: Optional[dict], *, user_credits: Callable[[dict], int]) -> Dict[str, Any]:
    env_vars: Dict[str, str] = {}
    import os
    for key in (
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "ANTHROPIC_API_KEY",
        "CEREBRAS_API_KEY",
        "LLAMA_API_KEY",
        "OPENAI_API_KEY",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
        "TAVILY_API_KEY",
    ):
        if os.environ.get(key, "").strip():
            env_vars[key] = "configured"
    out: Dict[str, Any] = {"env_vars": env_vars}
    if user:
        out["billing"] = {
            "plan": (user.get("plan") or "free"),
            "credits": user_credits(user),
        }
    return out



def update_last_build_state_service(
    plan: Dict[str, Any],
    *,
    last_build_state: dict,
    recent_agent_selection_logs: list,
    logger: Any,
) -> None:
    phase_count = int(plan.get("phase_count") or len(plan.get("phases", [])))
    selected_agent_count = int(plan.get("selected_agent_count") or 0)
    orchestration_mode = plan.get("orchestration_mode", "unknown")
    selected_agents = plan.get("selected_agents", [])
    last_build_state.update(
        {
            "selected_agents": selected_agents,
            "selected_agent_count": selected_agent_count,
            "phase_count": phase_count,
            "orchestration_mode": orchestration_mode,
            "selection_explanation": plan.get("selection_explanation") or {},
            "controller_summary": plan.get("controller_summary") or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    if orchestration_mode == "agent_swarm":
        log_lines = [
            f"Agent selection triggered for goal: {plan.get('goal', '')[:120]}",
            f"Generated {phase_count} phases from DAG",
            f"Executing swarm with {selected_agent_count} selected agents",
        ]
    else:
        log_lines = [
            f"Agent selection not triggered for goal: {plan.get('goal', '')[:120]}",
            f"Falling back to {orchestration_mode}",
        ]
    for line in log_lines:
        logger.info(line)
        recent_agent_selection_logs.append(line)
    del recent_agent_selection_logs[:-20]



def public_plan_summary_service(plan: Dict[str, Any], *, max_agents: int = 60) -> Dict[str, Any]:
    selected_agents = list(plan.get("selected_agents") or [])
    phases = list(plan.get("phases") or [])
    controller_summary = dict(plan.get("controller_summary") or {})
    selection_explanation = dict(plan.get("selection_explanation") or {})
    matched_keywords = list(selection_explanation.get("matched_keywords") or [])
    return {
        "goal": plan.get("goal", ""),
        "summary": plan.get("summary", ""),
        "orchestration_mode": plan.get("orchestration_mode", "unknown"),
        "phase_count": int(plan.get("phase_count") or len(phases)),
        "selected_agent_count": int(plan.get("selected_agent_count") or len(selected_agents)),
        "selected_agents": selected_agents[:max_agents],
        "selected_agents_truncated": len(selected_agents) > max_agents,
        "phase_sizes": [len(phase or []) for phase in phases],
        "recommended_build_target": plan.get("recommended_build_target"),
        "missing_inputs": list(plan.get("missing_inputs") or []),
        "risk_flags": list(plan.get("risk_flags") or []),
        "selection_explanation": {
            **selection_explanation,
            "matched_keywords": matched_keywords[:20],
            "matched_keywords_truncated": len(matched_keywords) > 20,
        },
        "controller_summary": {
            "execution_strategy": controller_summary.get("execution_strategy"),
            "parallel_phase_count": controller_summary.get("parallel_phase_count"),
            "recommended_focus": controller_summary.get("recommended_focus"),
            "next_actions": list(controller_summary.get("next_actions") or [])[:8],
            "replan_triggers": list(controller_summary.get("replan_triggers") or [])[:8],
            "memory_strategy": controller_summary.get("memory_strategy"),
        },
    }


async def generate_public_plan_service(
    *,
    goal: str,
    user: Optional[dict],
    planner_mod: Any,
    planner_project_state: Dict[str, Any],
    update_last_build_state: Callable[[Dict[str, Any]], None],
) -> Dict[str, Any]:
    plan = await planner_mod.generate_plan(goal, project_state=planner_project_state)
    plan["phase_count"] = int(plan.get("phase_count") or len(plan.get("phases", [])))
    update_last_build_state(plan)
    return plan


async def estimate_orchestration_service(
    *,
    goal: str,
    build_target: Optional[str],
    user: Optional[dict],
    planner_mod: Any,
    normalize_build_target: Callable[[Optional[str]], str],
    planner_project_state: Dict[str, Any],
) -> Dict[str, Any]:
    plan = await planner_mod.generate_plan(goal, project_state=planner_project_state)
    requested_target = (build_target or "").strip()
    bt = normalize_build_target(requested_target or plan.get("recommended_build_target"))
    estimate = planner_mod.estimate_tokens(plan)
    return {
        "success": True,
        "estimate": estimate,
        "plan_summary": plan.get("summary", ""),
        "build_target": bt,
    }
