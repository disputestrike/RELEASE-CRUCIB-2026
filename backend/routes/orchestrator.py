import logging
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from ..deps import get_current_user, get_optional_user
from ..db_pg import get_pg_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

BENCHMARK_SECRET = os.environ.get("BENCHMARK_SECRET", "crucibai_benchmark_2026_secret_key")

class RunAutoRequest(BaseModel):
    job_id: str

class BenchmarkRunRequest(BaseModel):
    goal: str
    secret: str

async def _background_auto_runner_job(job_id: str, workspace_path: str):
    """Background task to run the orchestrator for a job."""
    try:
        from ..orchestration.executor import execute_build
        await execute_build(job_id, workspace_path)
    except Exception as e:
        logger.exception(f"Error in background auto runner for job {job_id}: {e}")

@router.post("/run-auto")
async def run_auto(
    body: RunAutoRequest,
    background_tasks: BackgroundTasks,
    x_benchmark_secret: Optional[str] = Header(None, alias="x-benchmark-secret")
):
    """
    Start auto-runner for an existing job.
    """
    # Allow if valid benchmark secret is provided
    if x_benchmark_secret != BENCHMARK_SECRET:
        raise HTTPException(status_code=401, detail=f"Not authenticated (secret: {x_benchmark_secret})")
        
    try:
        from ..orchestration.runtime_state import runtime_state_adapter as runtime_state
        from ..server import _project_workspace_path
        
        job = await runtime_state.get_job(body.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        project_id = job.get("project_id")
        workspace_path = _project_workspace_path(project_id)
        
        # Start background execution
        background_tasks.add_task(_background_auto_runner_job, body.job_id, str(workspace_path))
        
        return {"success": True, "job_id": body.job_id, "status": "started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("orchestrator/run-auto error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/benchmark/run")
async def run_benchmark_job(
    body: BenchmarkRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Special endpoint for running benchmarks without a user session.
    Protected by BENCHMARK_SECRET.
    """
    if body.secret != BENCHMARK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid benchmark secret")
        
    try:
        from ..services.runtime.task_manager import task_manager
        from ..server import _project_workspace_path
        
        # Create job with a system user ID
        job = await task_manager.create_task(
            goal=body.goal,
            user_id="system-benchmark-user",
            mode="guided"
        )
        
        job_id = job["id"]
        project_id = job.get("project_id")
        workspace_path = _project_workspace_path(project_id)
        
        # Start background execution
        background_tasks.add_task(_background_auto_runner_job, job_id, str(workspace_path))
        
        return {
            "success": True, 
            "job_id": job_id, 
            "project_id": project_id,
            "status": "started"
        }
        
    except Exception as e:
        logger.exception("benchmark/run error")
        raise HTTPException(status_code=500, detail=str(e))
