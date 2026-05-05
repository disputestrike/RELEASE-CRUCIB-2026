from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import HTTPException
from ..services.runtime_contract import require_canonical_db

_logger = logging.getLogger(__name__)


def _single_runtime_plan(goal: str) -> Dict[str, Any]:
    return {
        "engine": "single_tool_runtime",
        "goal": str(goal or ""),
        "orchestration_mode": "single_tool_runtime",
        "recommended_build_target": "full_system_generator",
        "phase_count": 0,
        "selected_agent_count": 0,
        "selected_agents": [],
        "legacy_job_steps": False,
        "summary": str(goal or "")[:500],
        "phases": [],
        "steps": [
            "Inspect the scaffold and workspace files",
            "Write the requested application through file tools",
            "Install dependencies",
            "Run build proof checks",
            "Repair failing output and verify again",
            "Expose preview, files, and proof",
        ],
    }


def _legacy_job_steps_enabled() -> bool:
    return False


async def create_job_service(
    *,
    body,
    user: dict,
    runtime_state_getter: Callable[[], Any],
    pool_getter: Callable[[], Awaitable[Any]],
    generate_plan: Callable[..., Awaitable[Any]],
    resolve_project_id: Optional[Callable[[str, dict], Awaitable[str]]] = None,
    update_last_build_state: Optional[Callable[[Any], None]] = None,
    planner_project_state: Optional[dict] = None,
):
    rs = runtime_state_getter()
    # Surface failures in pool acquisition explicitly — raising HTTPException(503)
    # instead of swallowing and returning None fixes the downstream
    # "object NoneType can't be used in 'await' expression" errors.
    try:
        pool = await pool_getter()
        rs.set_pool(pool)
    except Exception as exc:
        import logging as _lg
        _lg.getLogger(__name__).warning("create_job_service: pool unavailable", exc_info=True)
        pool = None
    pool = require_canonical_db(pool, action="create_job")

    project_id = body.project_id or user.get("id", "default")
    if resolve_project_id is not None:
        project_id = await resolve_project_id(project_id, user)

    use_legacy_steps = False
    plan = _single_runtime_plan(body.goal)
    if update_last_build_state is not None:
        try:
            update_last_build_state(plan)
        except Exception:
            pass

    if pool:
        await rs.ensure_job_fk_prerequisites(project_id, user.get("id"))
        job = await rs.create_job(
            project_id=project_id,
            mode=body.mode or "guided",
            goal=body.goal,
            user_id=user.get("id"),
        )
    else:
        import uuid as _uuid
        from datetime import datetime as _dt, timezone as _tz

        job = {
            "id": str(_uuid.uuid4()),
            "project_id": project_id,
            "status": "planned",
            "mode": body.mode or "guided",
            "goal": body.goal,
            "user_id": user.get("id"),
            "created_at": _dt.now(_tz.utc).isoformat(),
        }

    if pool:
        await rs.append_job_event(
            job["id"],
            "runtime_backend_selected",
            {
                "engine": "single_tool_runtime",
                "legacy_job_steps": False,
            },
        )
    return {
        "success": True,
        "job": job,
        "plan": plan,
        "websocket_url": f"/api/job/{job['id']}/progress",
    }


async def list_jobs_service(
    *,
    user: dict,
    status: Optional[str],
    limit: int,
    runtime_state_getter: Callable[[], Any],
    pool_getter: Callable[[], Awaitable[Any]],
):
    rs = runtime_state_getter()
    pool = await pool_getter()
    rs.set_pool(pool)
    jobs = await rs.list_jobs_for_user(user["id"], limit=limit)
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    return {"success": True, "jobs": jobs, "count": len(jobs)}


async def get_job_service(
    *,
    job_id: str,
    user: dict,
    resolve_job: Callable[[str, dict], Awaitable[dict]],
    runtime_state_getter: Callable[[], Any],
    pool_getter: Optional[Callable[[], Awaitable[Any]]] = None,
):
    job = await resolve_job(job_id, user)
    latest_failure = None
    controller_progress = None
    try:
        rs = runtime_state_getter()
        latest_failure = await rs.load_checkpoint(job_id, "latest_failure")
    except Exception:
        latest_failure = None

    _ = pool_getter
    out: Dict[str, Any] = {
        "success": True,
        "job": job,
        "latest_failure": latest_failure,
    }
    if controller_progress is not None:
        out["controller_progress"] = controller_progress
    return out


async def get_job_checkpoint_service(
    *,
    job_id: str,
    checkpoint_key: str,
    user: dict,
    resolve_job: Callable[[str, dict], Awaitable[dict]],
    runtime_state_getter: Callable[[], Any],
    pool_getter: Callable[[], Awaitable[Any]],
):
    await resolve_job(job_id, user)
    rs = runtime_state_getter()
    pool = await pool_getter()
    rs.set_pool(pool)
    data = await rs.load_checkpoint(job_id, checkpoint_key)
    return {"success": True, "checkpoint_key": checkpoint_key, "data": data}


async def update_job_service(
    *,
    job_id: str,
    update,
    user: dict,
    resolve_job: Callable[[str, dict], Awaitable[dict]],
    runtime_state_getter: Callable[[], Any],
    publish: Optional[Callable[[str, str, dict], Awaitable[None]]] = None,
):
    await resolve_job(job_id, user)
    rs = runtime_state_getter()
    extra: Dict[str, Any] = {}
    if update.progress is not None:
        extra["quality_score"] = update.progress
    if update.message:
        extra["error_message"] = update.message
    await rs.update_job_state(job_id, update.status, extra=extra or None)
    if publish is not None:
        try:
            await publish(
                job_id,
                "job_status_changed",
                {"job_id": job_id, "status": update.status, "progress": update.progress},
            )
        except Exception:
            pass
    updated = await rs.get_job(job_id)
    return {"success": True, "job": updated}
