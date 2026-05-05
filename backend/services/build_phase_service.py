from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

DEFAULT_SUGGESTIONS = [
    "Add more features",
    "Enhance reporting",
    "Improve accessibility",
]


async def build_plan_service(
    *,
    prompt: str,
    build_kind: str,
    use_swarm: bool,
    user: Optional[dict],
    db: Any,
    build_kinds: Iterable[str],
    kind_instruction_map: Dict[str, str],
    min_credits_for_llm: int,
    swarm_token_multiplier: float,
    screen_user_content: Callable[[str], Optional[str]],
    user_credits: Callable[[dict], int],
    get_workspace_api_keys: Callable[[Optional[dict]], Awaitable[dict]],
    effective_api_keys: Callable[[dict], dict],
    is_real_agent_only: Callable[[], bool],
    chat_llm_available: Callable[[dict], bool],
    real_agent_no_llm_keys_detail: str,
    get_model_chain: Callable[..., Any],
    call_llm_with_fallback: Callable[..., Awaitable[tuple[str, Any]]],
    ensure_credit_balance: Callable[[str], Awaitable[None]],
    tokens_to_credits: Callable[[int], int],
) -> dict:
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    plan_block = screen_user_content(prompt)
    if plan_block:
        raise HTTPException(status_code=400, detail=plan_block)
    build_kind = (build_kind or "").strip().lower() or "fullstack"
    if build_kind not in tuple(build_kinds):
        build_kind = "fullstack"
    if user is not None and not user.get("public_api"):
        credits = user_credits(user)
        required = min_credits_for_llm * (swarm_token_multiplier if use_swarm else 1)
        if credits < required:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits for {'Swarm ' if use_swarm else ''}plan. Need at least {int(required)}. Buy more in Credit Center.",
            )
    user_keys_plan = await get_workspace_api_keys(user)
    effective_plan = effective_api_keys(user_keys_plan)
    if is_real_agent_only() and not chat_llm_available(effective_plan):
        raise HTTPException(status_code=503, detail=real_agent_no_llm_keys_detail)
    kind_instruction = kind_instruction_map.get(build_kind, "")
    system = f'''You are a product and engineering planner. Given a user request to build an application, output a concise plan in this exact format (use the headings and bullets, no extra text before/after).{kind_instruction}

Plan
Key Features:
• [Feature 1] – [one line]
• [Feature 2] – [one line]
• (add 4-8 features as needed)

Design Language:
• [e.g. Dark navy + white + gold accent for premium feel]
• Clean, spacious layout with card-based UI
• (2-4 short design points)

Color Palette:
• Primary: [name] (#hex)
• Secondary: [name] (#hex)
• Accent: [name] (#hex)
• Background: [name] (#hex)

Components:
• [e.g. Layout with sidebar navigation]
• [e.g. Dashboard stats cards, charts]
• (list 6-12 UI components or pages)

End with exactly: "Let me build this now."
'''
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = effective_api_keys(user_keys)
        model_chain = get_model_chain("auto", prompt, effective_keys=effective)

        async def get_plan() -> str:
            pt, _ = await call_llm_with_fallback(
                message=f"User request: {prompt}",
                system_message=system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            return (pt or "").strip()

        async def get_suggestions_standalone() -> List[str]:
            sug_system = "Given the user request for an app, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
            resp, _ = await call_llm_with_fallback(
                message=f"User request: {prompt[:800]}",
                system_message=sug_system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            match = re.search(r"\[.*?\]", resp or "", re.DOTALL)
            arr = json.loads(match.group()) if match else []
            return [str(x).strip() for x in arr[:3]] if isinstance(arr, list) else []

        if use_swarm:
            plan_text, suggestions = await asyncio.gather(
                get_plan(), get_suggestions_standalone()
            )
            suggestions = suggestions or list(DEFAULT_SUGGESTIONS)
        else:
            plan_text = await get_plan()
            suggestions = []
            try:
                sug_system = "Given the app plan above, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
                sug_resp, _ = await call_llm_with_fallback(
                    message=f"Plan:\n{plan_text[:1500]}",
                    system_message=sug_system,
                    session_id=str(uuid.uuid4()),
                    model_chain=model_chain,
                    api_keys=effective,
                )
                match = re.search(r"\[.*?\]", sug_resp or "", re.DOTALL)
                arr = json.loads(match.group()) if match else []
                if isinstance(arr, list):
                    suggestions = [str(x).strip() for x in arr[:3]]
            except Exception:
                pass
            if not suggestions:
                suggestions = list(DEFAULT_SUGGESTIONS)

        tokens_estimate = max(
            1000, len(plan_text) * 2 + sum(len(s) for s in suggestions) * 2
        )
        if use_swarm:
            tokens_estimate = int(tokens_estimate * swarm_token_multiplier)
        if user and not user.get("public_api"):
            credits = user_credits(user)
            credit_deduct = min(tokens_to_credits(tokens_estimate), credits)
            if credit_deduct > 0:
                await ensure_credit_balance(user["id"])
                await db.users.update_one(
                    {"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}}
                )
        return {
            "plan_text": plan_text,
            "suggestions": suggestions,
            "model_used": "auto",
            "swarm_used": use_swarm,
            "plan_tokens": tokens_estimate,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("build/plan failed")
        raise HTTPException(status_code=500, detail=str(exc))


async def get_project_phases_service(*, project_id: str, user: dict, db: Any, build_phases: list[dict]) -> dict:
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statuses = await db.agent_status.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    by_agent = {s["agent_name"]: s for s in statuses}
    phases_out = []
    current_phase_id = None
    for phase in build_phases:
        agent_statuses = [by_agent.get(a, {"status": "pending", "progress": 0}) for a in phase["agents"]]
        completed = sum(1 for a in agent_statuses if a.get("status") == "completed")
        total = len(phase["agents"])
        status = (
            "completed" if completed == total else ("running" if completed > 0 or current_phase_id == phase["id"] else "pending")
        )
        if status == "running" and current_phase_id is None:
            current_phase_id = phase["id"]
        phases_out.append({
            "id": phase["id"],
            "name": phase["name"],
            "status": status,
            "progress": round(100 * completed / total) if total else 0,
            "agents": agent_statuses,
        })
    if not current_phase_id and project.get("status") == "completed":
        current_phase_id = "deployment"
    return {"phases": phases_out, "current_phase": current_phase_id, "project_status": project.get("status")}
