"""
Workflows API — expose named workflows to the frontend.
POST /api/workflows/run → triggers orchestrator/plan with workflow goal
GET  /api/workflows     → list all workflows by category
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["workflows"])

def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous", "email": "anonymous@local"}
        return noop


class WorkflowRunRequest(BaseModel):
    workflow_key: str
    project_id: Optional[str] = None
    context: Optional[str] = ""  # existing code context


@router.get("/workflows")
async def list_workflows():
    """List all workflows grouped by category."""
    from workflows import get_workflows_by_category, WORKFLOWS
    return {
        "workflows": get_workflows_by_category(),
        "total": len(WORKFLOWS),
    }


@router.post("/workflows/run")
async def run_workflow(
    body: WorkflowRunRequest,
    user: dict = Depends(_get_auth()),
):
    """Trigger a named workflow — creates a plan and starts execution."""
    from workflows import get_workflow, workflow_to_plan_goal, WORKFLOWS
    import asyncio

    wf = get_workflow(body.workflow_key)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{body.workflow_key}' not found")

    goal = workflow_to_plan_goal(body.workflow_key, body.context or "")
    if not goal:
        raise HTTPException(status_code=400, detail="Could not generate goal for workflow")

    # Trigger plan + run via orchestrator
    try:
        from orchestration.runtime_state import create_job, create_step
        from orchestration.planner import generate_plan, estimate_tokens
        from orchestration.dag_engine import build_dag_from_plan
        from orchestration.auto_runner import run_job
        from db_pg import get_pg_pool
        import json, uuid

        pool = await get_pg_pool()

        # Create job
        from services.orchestration_service import create_job_service
        job = await create_job_service(
            project_id=body.project_id or user["id"],
            mode="auto",
            goal=goal,
            user_id=user["id"],
            pool=pool,
        )
        job_id = job["id"]

        # Generate plan
        plan = await generate_plan(goal)
        plan["workflow_key"] = body.workflow_key
        plan["workflow_name"] = wf["name"]

        # Prioritize workflow-specific agents
        if wf.get("agents"):
            plan["prioritized_agents"] = wf["agents"]

        # Store plan
        plan_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO build_plans (id, job_id, project_id, goal, plan_json, status, created_at) VALUES ($1,$2,$3,$4,$5,'draft',NOW())",
                plan_id, job_id, body.project_id or user["id"], goal, json.dumps(plan),
            )

        # Create DAG steps
        step_defs = build_dag_from_plan(plan)
        for idx, sd in enumerate(step_defs):
            await create_step(
                job_id=job_id,
                step_key=sd["step_key"],
                agent_name=sd["agent_name"],
                phase=sd["phase"],
                depends_on=sd["depends_on"],
                order_index=idx,
                pool=pool,
            )

        # Start background execution
        import asyncio
        from orchestration.auto_runner import run_auto_runner
        asyncio.create_task(run_auto_runner(job_id, "", pool))

        return {
            "success": True,
            "job_id": job_id,
            "workflow": wf["name"],
            "goal": goal[:200],
            "stream_url": f"/api/jobs/{job_id}/stream",
        }

    except Exception as e:
        logger.exception("workflow run error: %s", e)
        # Fallback: just return the goal for the frontend to submit normally
        return {
            "success": False,
            "fallback": True,
            "goal": goal,
            "workflow": wf["name"],
            "error": str(e),
        }
