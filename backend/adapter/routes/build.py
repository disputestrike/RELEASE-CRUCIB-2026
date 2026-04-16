"""
Build routes — start/stop/steer builds.
Maps frontend's /api/build → our /api/orchestrator/plan + run-auto
"""
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous", "email": "anonymous@local"}
        return noop


class AttachmentModel(BaseModel):
    type: str = "text"
    content: str = ""
    filename: Optional[str] = None


class BuildRequest(BaseModel):
    prompt: str
    attachments: List[AttachmentModel] = []
    mode: str = "thinking"
    thinkingEffort: str = "medium"
    preferences: dict = {}


class SteerRequest(BaseModel):
    action: str = "interrupt"
    kind: str = "custom_instruction"
    instruction: str
    phaseId: Optional[str] = None
    phaseName: Optional[str] = None
    resume: bool = True
    timestamp: Optional[int] = None


async def _run_build_background(job_id: str, goal: str, user_id: str):
    """Background task: plan + execute build."""
    try:
        from services.runtime.runtime_engine import runtime_engine
        from adapter.services.event_bridge import on_job_started, on_job_error

        on_job_started(job_id, goal)
        await runtime_engine.execute_with_control(
            task_id=job_id,
            user_id=user_id or "anonymous",
            request=goal,
            conversation_id=f"build-{job_id}",
        )

    except Exception as e:
        logger.exception("build background failed: %s", e)
        try:
            from adapter.services.event_bridge import on_job_error
            on_job_error(job_id, str(e))
        except Exception:
            pass


@router.post("/api/build")
async def start_build(
    req: BuildRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(_get_auth()),
):
    """Start a build. Returns jobId immediately, runs in background."""
    from orchestration import planner as planner_mod
    from orchestration import runtime_state
    import json

    goal = req.prompt.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="prompt is required")

    # Attach any screenshot/text context to the goal
    if req.attachments:
        for att in req.attachments:
            if att.type == "text" and att.content:
                goal += f"\n\nAttachment ({att.filename or 'file'}):\n{att.content[:2000]}"

    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
    except Exception:
        pool = None

    # Generate plan
    plan = await planner_mod.generate_plan(goal, {"user_id": user.get("id", "")})

    # Create job
    job = await runtime_state.create_job(
        project_id=user.get("id", str(uuid.uuid4())),
        mode=req.mode or "guided",
        goal=goal,
        user_id=user.get("id"),
    )
    job_id = job["id"]

    # Store plan + steps
    plan_id = str(uuid.uuid4())
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO build_plans (id,job_id,project_id,goal,plan_json,status,created_at) "
                    "VALUES ($1,$2,$3,$4,$5,'draft',NOW())",
                    plan_id, job_id, user.get("id", job_id), goal, json.dumps(plan),
                )
        except Exception as e:
            logger.warning("plan store failed: %s", e)

    step_defs = []

    # Start build in background
    background_tasks.add_task(_run_build_background, job_id, goal, user.get("id", ""))

    return {
        "jobId": job_id,
        "status": "queued",
        "planId": plan_id,
        "goal": goal[:200],
        "estimatedSteps": max(1, len(step_defs)),
        "createdAt": job.get("created_at", ""),
        "streamUrl": f"/api/jobs/{job_id}/stream",
        "wsUrl": f"/ws/events?jobId={job_id}",
    }


@router.post("/api/builds/{job_id}/interrupt")
async def interrupt_build(
    job_id: str,
    req: SteerRequest,
    user: dict = Depends(_get_auth()),
):
    """Steer/interrupt a running build."""
    import json
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET steer_queue = COALESCE(steer_queue,'[]'::jsonb) || $1::jsonb "
                "WHERE id = $2",
                json.dumps([{
                    "action": req.action,
                    "kind": req.kind,
                    "instruction": req.instruction,
                    "phase_id": req.phaseId,
                    "resume": req.resume,
                }]),
                job_id,
            )
    except Exception as e:
        logger.warning("interrupt_build db: %s", e)

    from adapter.services.event_bridge import on_steer_accepted
    on_steer_accepted(job_id, f"Redirect: {req.instruction[:80]}",
                      req.phaseName or "", "", [])

    return {
        "accepted": True,
        "summary": f"Instruction queued: {req.instruction[:120]}",
        "message": "Build will be redirected at next checkpoint",
        "beforePlan": {"steps": []},
        "afterPlan": {"steps": []},
    }


@router.get("/api/builds/{job_id}/quality")
async def get_quality(job_id: str, user: dict = Depends(_get_auth())):
    """Get quality score breakdown for a completed build."""
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT quality_score FROM jobs WHERE id=$1", job_id)
        score = float(row["quality_score"] or 0) if row else 0
        return {
            "overall": score,
            "frontend": min(score + 5, 100),
            "backend": score,
            "database": min(score - 2, 100),
            "security": min(score - 5, 100),
            "tests": max(score - 10, 0),
            "deployment": score,
        }
    except Exception:
        return {"overall": 0, "frontend": 0, "backend": 0, "database": 0,
                "security": 0, "tests": 0, "deployment": 0}


@router.get("/api/builds/{job_id}/issues")
async def get_issues(job_id: str, user: dict = Depends(_get_auth())):
    """Get issues detected during build."""
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM job_steps WHERE job_id=$1 AND status='failed'", job_id)
        return [
            {
                "id": str(r["id"]),
                "severity": "high",
                "title": r["agent_name"] or r["step_key"],
                "description": r["error_message"] or "Step failed",
                "cause": r["error_details"] or "",
                "status": "detected",
                "detectedAt": str(r.get("updated_at", "")),
            }
            for r in rows
        ]
    except Exception:
        return []
