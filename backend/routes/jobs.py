"""
Job management routes module.
Handles job creation, execution, status, history, and management.

All persistent state is stored in the PostgreSQL ``jobs`` / ``job_steps`` /
``job_events`` tables (see migrations/001_full_schema.sql and
migrations/006_complete_schema.sql).  Reads and writes go through
``orchestration.runtime_state``; broadcasting uses
``orchestration.event_bus``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# ── Lazy-import helpers ───────────────────────────────────────────────────────

def _get_auth():
    from server import get_current_user
    return get_current_user


def _get_runtime_state():
    from orchestration import runtime_state
    return runtime_state


def _get_proof_service():
    from proof import proof_service
    return proof_service


async def _get_pool():
    from db_pg import get_pg_pool
    return await get_pg_pool()


async def _resolve_job(job_id: str, user: dict) -> dict:
    """Fetch a job from the DB and assert ownership. Raises 404/403 on failure."""
    rs = _get_runtime_state()
    pool = await _get_pool()
    rs.set_pool(pool)
    job = await rs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    owner = job.get("user_id")
    uid = (user or {}).get("id")
    if not owner or not uid or owner != uid:
        raise HTTPException(status_code=403, detail="Not your job")
    return job


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class JobCreateRequest(BaseModel):
    """Job creation request"""
    goal: str
    project_id: Optional[str] = None
    mode: Optional[str] = "guided"
    priority: Optional[str] = "normal"
    timeout: Optional[int] = 3600


class JobStatusUpdate(BaseModel):
    """Job status update"""
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# JOB MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/", status_code=201)
async def create_job(
    body: JobCreateRequest,
    user: dict = Depends(_get_auth()),
):
    """Create a new job (plan + steps) for a project."""
    try:
        rs = _get_runtime_state()
        pool = await _get_pool()
        rs.set_pool(pool)

        from orchestration import planner as planner_mod
        from orchestration.dag_engine import build_dag_from_plan

        # Auto-assign project_id from user when not supplied
        project_id = body.project_id or user.get("id", "default")

        # Ensure FK prerequisites exist
        await rs.ensure_job_fk_prerequisites(project_id, user.get("id"))

        plan = await planner_mod.generate_plan(body.goal, project_state={})
        job = await rs.create_job(
            project_id=project_id,
            mode=body.mode or "guided",
            goal=body.goal,
            user_id=user.get("id"),
        )
        step_defs = build_dag_from_plan(plan)
        for idx, sd in enumerate(step_defs):
            await rs.create_step(
                job_id=job["id"],
                step_key=sd["step_key"],
                agent_name=sd["agent_name"],
                phase=sd["phase"],
                depends_on=sd["depends_on"],
                order_index=idx,
            )
        return {
            "success": True,
            "job": job,
            "plan": plan,
            "websocket_url": f"/api/job/{job['id']}/progress",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/jobs error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(_get_auth()),
):
    """List recent jobs for the authenticated user."""
    try:
        rs = _get_runtime_state()
        pool = await _get_pool()
        rs.set_pool(pool)
        jobs = await rs.list_jobs_for_user(user["id"], limit=limit)
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        return {"success": True, "jobs": jobs, "count": len(jobs)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Get job status and details."""
    try:
        job = await _resolve_job(job_id, user)
        return {"success": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}")
async def update_job(
    job_id: str,
    update: JobStatusUpdate,
    user: dict = Depends(_get_auth()),
):
    """Update job status and optionally broadcast progress."""
    try:
        job = await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        extra: Dict[str, Any] = {}
        if update.progress is not None:
            extra["quality_score"] = update.progress
        if update.message:
            extra["error_message"] = update.message
        await rs.update_job_state(job_id, update.status, extra=extra or None)
        # Broadcast so SSE listeners see the change
        try:
            from orchestration.event_bus import publish
            await publish(job_id, "job_status_changed", {
                "job_id": job_id,
                "status": update.status,
                "progress": update.progress,
            })
        except Exception:
            pass
        updated = await rs.get_job(job_id)
        return {"success": True, "job": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PATCH /api/jobs/%s error", job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Cancel a running job and broadcast the cancellation event."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        await rs.update_job_state(job_id, "cancelled")
        try:
            from orchestration.event_bus import publish
            await publish(job_id, "job_cancelled", {"job_id": job_id})
        except Exception:
            pass
        return {"success": True, "job_id": job_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Requeue a failed/cancelled job by resetting its state to 'queued'."""
    try:
        job = await _resolve_job(job_id, user)
        current_status = job.get("status", "")
        if current_status not in ("failed", "cancelled", "error"):
            raise HTTPException(
                status_code=400,
                detail=f"Only failed or cancelled jobs can be retried (current: {current_status})",
            )
        rs = _get_runtime_state()
        await rs.update_job_state(
            job_id,
            "queued",
            extra={
                "retry_count": (job.get("retry_count") or 0) + 1,
                "error_message": None,
                "error_details": None,
                "failure_reason": None,
            },
        )
        try:
            from orchestration.event_bus import publish
            await publish(job_id, "job_requeued", {"job_id": job_id})
        except Exception:
            pass
        return {"success": True, "job_id": job_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/history")
async def get_job_history(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Get phase execution history (job steps) for a job."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        steps = await rs.get_steps(job_id)
        events = await rs.get_job_events(job_id)
        return {"success": True, "job_id": job_id, "steps": steps, "events": events}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    level: Optional[str] = None,
    since_id: Optional[str] = None,
    user: dict = Depends(_get_auth()),
):
    """Get job event log, optionally filtered by level."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        events = await rs.get_job_events(job_id, since_id=since_id)
        import json as _json
        logs = []
        for e in events:
            try:
                payload = _json.loads(e.get("payload_json") or "{}")
            except Exception:
                payload = {}
            entry = {
                "id": e.get("id"),
                "timestamp": e.get("created_at"),
                "level": payload.get("level", "info"),
                "event_type": e.get("event_type"),
                "message": payload.get("message") or e.get("event_type"),
                "payload": payload,
            }
            if level and entry["level"] != level:
                continue
            logs.append(entry)
        return {"success": True, "job_id": job_id, "logs": logs, "count": len(logs)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/result")
async def get_job_result(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Get job result and generated artifacts from DB."""
    try:
        job = await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        steps = await rs.get_steps(job_id)
        completed = [s for s in steps if s.get("status") == "completed"]
        artifacts = []
        for s in completed:
            ref = s.get("output_ref")
            if ref:
                artifacts.append({"step_key": s.get("step_key"), "output_ref": ref})
        return {
            "success": True,
            "job_id": job_id,
            "status": job.get("status"),
            "quality_score": job.get("quality_score"),
            "output": {
                "current_phase": job.get("current_phase"),
                "completed_steps": len(completed),
                "total_steps": len(steps),
            },
            "artifacts": artifacts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/webhook")
async def webhook_job_event(
    job_id: str,
    event: Dict[str, Any],
    user: dict = Depends(_get_auth()),
):
    """Accept a webhook event for a job, persist it, and broadcast to SSE listeners."""
    try:
        await _resolve_job(job_id, user)
        event_type = event.get("event_type", "webhook")
        rs = _get_runtime_state()
        await rs.append_job_event(job_id, event_type, event)
        # Update job status if the webhook carries one
        new_status = event.get("status")
        if new_status:
            await rs.update_job_state(job_id, new_status)
        try:
            from orchestration.event_bus import publish
            await publish(job_id, event_type, event)
        except Exception:
            pass
        return {"success": True, "received": True, "event_type": event_type}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/proof")
async def get_job_proof(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Get the full proof bundle for a job."""
    try:
        await _resolve_job(job_id, user)
        ps = _get_proof_service()
        pool = await _get_pool()
        ps.set_pool(pool)
        proof = await ps.get_proof(job_id)
        return {"success": True, **proof}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs/%s/proof error", job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Delete a job and all its associated steps and events from the DB."""
    try:
        await _resolve_job(job_id, user)
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM job_events WHERE job_id=$1", job_id)
            await conn.execute("DELETE FROM job_steps WHERE job_id=$1", job_id)
            await conn.execute(
                "DELETE FROM job_checkpoints WHERE job_id=$1", job_id
            )
            await conn.execute("DELETE FROM jobs WHERE id=$1", job_id)
        return {"success": True, "job_id": job_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("DELETE /api/jobs/%s error", job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/estimate")
async def estimate_job_cost(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Estimate token/credit cost for a job based on its plan steps."""
    try:
        job = await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        steps = await rs.get_steps(job_id)
        # Simple heuristic: 1 000 tokens per step, ~0.002 USD/1K tokens
        step_count = max(1, len(steps))
        estimated_tokens = step_count * 1000
        estimated_cost_usd = round(estimated_tokens * 0.002 / 1000, 4)
        return {
            "success": True,
            "job_id": job_id,
            "goal": job.get("goal"),
            "step_count": step_count,
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "currency": "USD",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

