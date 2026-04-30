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

import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from ..services.job_service import (
    create_job_service,
    get_job_checkpoint_service,
    get_job_service,
    list_jobs_service,
    update_job_service,
)
from ..services.job_runtime_service import retry_step_service
from ..services.job_event_service import (
    get_job_steps_service,
    get_job_events_service,
)
from ..services.runtime_contract import require_canonical_db
from pydantic import BaseModel, Field
from ..deps import get_current_user

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Running-task registry — allows cancel/pause to interrupt live asyncio Tasks
# ---------------------------------------------------------------------------

_running_tasks: Dict[str, asyncio.Task] = {}


def register_running_task(job_id: str, task: asyncio.Task) -> None:
    """Store a reference to the background asyncio Task for a job."""
    _running_tasks[job_id] = task


def unregister_running_task(job_id: str) -> None:
    """Remove a completed/cancelled task from the registry."""
    _running_tasks.pop(job_id, None)


def get_running_task(job_id: str) -> Optional[asyncio.Task]:
    """Return the asyncio Task if the job is currently executing."""
    return _running_tasks.get(job_id)

# Lazy imports for SSE streaming; kept here so server import graph stays identical.
import asyncio as _asyncio
import json as _json
from fastapi.responses import StreamingResponse as _StreamingResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

class BenchmarkRunRequest(BaseModel):
    goal: str
    secret: str


class TranscriptAppend(BaseModel):
    """Durable workspace chat line (UnifiedWorkspace) stored as a job event."""

    role: Literal["user", "assistant"] = "user"
    body: str = Field(..., min_length=1, max_length=32000)


def _event_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload")
    if isinstance(payload, dict):
        return payload
    try:
        return _json.loads(event.get("payload_json") or "{}")
    except Exception:
        return {}


def _transcript_messages_from_events(events: List[Dict[str, Any]], job_id: str) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    for event in events:
        event_type = event.get("event_type") or event.get("type")
        if event_type != "workspace_transcript":
            continue
        payload = _event_payload(event)
        body = (payload.get("text") or payload.get("body") or "").strip()
        if not body:
            continue
        role = payload.get("role") if payload.get("role") in {"user", "assistant"} else "user"
        messages.append(
            {
                "id": event.get("id") or event.get("event_id"),
                "jobId": job_id,
                "role": role,
                "body": body,
                "text": body,
                "created_at": event.get("created_at"),
                "ts": payload.get("ts"),
                "source": payload.get("source") or "workspace_transcript",
            }
        )
    return messages


@router.post("/benchmark/run")
async def run_benchmark_job_fallback(
    body: BenchmarkRunRequest,
    request: Request
):
    """
    Fallback benchmark endpoint in jobs router.
    """
    benchmark_secret = os.environ.get("CRUCIBAI_BENCHMARK_SECRET")
    if not benchmark_secret:
        raise HTTPException(status_code=500, detail="Benchmark secret not configured (set CRUCIBAI_BENCHMARK_SECRET)")
    if body.secret != benchmark_secret:
        raise HTTPException(status_code=401, detail="Invalid benchmark secret")
        
    try:
        from ..services.runtime.task_manager import task_manager
        from ..server import _project_workspace_path
        from fastapi import BackgroundTasks
        
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
        from .orchestrator import _background_auto_runner_job
        # We need a BackgroundTasks object. FastAPI injects it if we add it to params.
        # But since we're in a route, we can just use the one from the request if we had it.
        # Let's just use a simple background task if possible or import it.
        
        # For now, let's just return the job_id and let the runner call run-auto if needed.
        return {
            "success": True, 
            "job_id": job_id, 
            "project_id": project_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.exception("benchmark/run fallback error")
        raise HTTPException(status_code=500, detail=str(e))


# Safe checkpoint keys for GET (alphanumeric, underscore, hyphen; bounded length).
_CHECKPOINT_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# ── Lazy-import helpers ───────────────────────────────────────────────────────


def _get_auth():
    from ..server import get_current_user

    return get_current_user


def _get_runtime_state():
    from ..orchestration import runtime_state

    return runtime_state


def _get_proof_service():
    from ..proof import proof_service

    return proof_service


async def _get_pool():
    """Return the asyncpg pool, raising HTTPException(503) if unavailable.

    Previously this helper returned ``None`` on any failure, which caused
    downstream ``object NoneType can't be used in 'await' expression`` errors
    when callers did ``await pool.acquire()``. We now surface the failure
    explicitly so FastAPI returns a proper 503 to the client.
    """
    from ..db_pg import get_pg_pool

    try:
        pool = await get_pg_pool()
        return require_canonical_db(pool, action="jobs_route")
    except Exception as exc:
        logger.warning("jobs: DB pool unavailable", exc_info=True)
        return require_canonical_db(None, action="jobs_route")


async def _resolve_job(job_id: str, user: dict) -> dict:
    """Fetch a job from the DB and assert ownership. Raises 404/403 on failure."""
    rs = _get_runtime_state()
    pool = await _get_pool()
    if pool is not None:
        rs.set_pool(pool)
    job = await rs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    owner = job.get("user_id")
    uid = (user or {}).get("id")
    is_admin = bool((user or {}).get("is_admin"))
    if not is_admin and (not owner or not uid or owner != uid):
        raise HTTPException(status_code=403, detail="Not your job")
    return job


def _assert_owner(owner_id: Optional[str], user: Optional[dict]) -> None:
    uid = (user or {}).get("id")
    is_admin = bool((user or {}).get("is_admin"))
    if not is_admin and (not owner_id or not uid or owner_id != uid):
        raise HTTPException(status_code=403, detail="Not your job")


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


async def create_job(
    body: JobCreateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(_get_auth()),
):
    """Create a new job (plan + steps) for a project."""
    try:
        from ..orchestration import planner as planner_mod
        # NOTE: build_dag_from_plan is no longer passed — create_job_service uses
        # services.runtime.execution_authority.build_runtime_native_step_defs directly.
        # Passing it caused every POST /api/jobs to fail with TypeError: unexpected
        # keyword argument, which was the root cause of the NoneType-await surface.

        result = await create_job_service(
            body=body,
            user=user,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
            generate_plan=planner_mod.generate_plan,
        )
        job = (result or {}).get("job") or {}
        job_id = job.get("id") or job.get("job_id")
        if str(body.mode or "").strip().lower() == "auto" and job_id:
            from .orchestrator import RunAutoRequest, run_auto

            result["auto_run"] = await run_auto(
                RunAutoRequest(job_id=job_id),
                background_tasks,
                user,
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/jobs error")
        raise HTTPException(status_code=500, detail=str(e))


router.add_api_route("", create_job, methods=["POST"], status_code=201, include_in_schema=False)
router.add_api_route("/", create_job, methods=["POST"], status_code=201)


@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(_get_auth()),
):
    """List recent jobs for the authenticated user."""
    try:
        return await list_jobs_service(
            user=user,
            status=status,
            limit=limit,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
        )
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
    """Get job status and details.

    Includes ``latest_failure`` when a checkpoint exists (verification or step exception),
    so the UI can narrate blockers even if proof rows are still loading.
    """
    try:
        return await get_job_service(
            job_id=job_id,
            user=user,
            resolve_job=_resolve_job,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/steps")
async def get_job_steps(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Get persisted execution steps for a job (owner-scoped)."""
    try:
        return await get_job_steps_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
            assert_owner=_assert_owner,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs/%s/steps error", job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/events")
async def get_job_events(
    job_id: str,
    since_id: Optional[str] = None,
    user: dict = Depends(_get_auth()),
):
    """Get persisted event stream for a job (owner-scoped)."""
    try:
        return await get_job_events_service(
            job_id=job_id,
            user=user,
            since_id=since_id,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
            assert_owner=_assert_owner,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs/%s/events error", job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/transcript")
async def append_job_transcript(
    job_id: str,
    body: TranscriptAppend,
    user: dict = Depends(_get_auth()),
):
    """Append a user (or assistant) line to the durable job event log (E6)."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        pool = await _get_pool()
        if pool is not None:
            rs.set_pool(pool)
        rec = await rs.append_job_event(
            job_id,
            "workspace_transcript",
            {
                "role": body.role,
                "text": body.body,
                "ts": time.time(),
                "source": "unified_workspace",
            },
        )
        try:
            from ..orchestration.event_bus import publish

            await publish(
                job_id,
                "workspace_transcript",
                {"role": body.role, "text": body.body},
            )
        except Exception:
            pass
        return {"success": True, "event": rec}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/jobs/%s/transcript error", job_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{job_id}/transcript")
async def get_job_transcript(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Return durable workspace chat lines for a job."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        pool = await _get_pool()
        if pool is not None:
            rs.set_pool(pool)
        events = await rs.get_job_events(job_id)
        messages = _transcript_messages_from_events(events, job_id)
        return {
            "success": True,
            "job_id": job_id,
            "messages": messages,
            "count": len(messages),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs/%s/transcript error", job_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{job_id}/stream")
async def stream_job_events(job_id: str, request: Request):
    """Server-Sent Events stream of live job events.

    Subscribes to ``orchestration.event_bus`` and forwards each published event
    as an SSE frame. Emits a heartbeat every 15s so dev proxies (CRA, nginx)
    do not idle-close the connection. Clients should reconnect on error; the
    companion ``/api/jobs/{id}/events`` endpoint serves backfill via ``since_id``.
    """
    from backend.orchestration.event_bus import subscribe, unsubscribe

    queue = await subscribe(job_id)

    async def _gen():
        # Initial hello so EventSource fires onopen immediately.
        yield f"event: connected\ndata: {_json.dumps({'job_id': job_id})}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await _asyncio.wait_for(queue.get(), timeout=15.0)
                except _asyncio.TimeoutError:
                    # Heartbeat; keeps proxies from closing the stream.
                    yield ": ping\n\n"
                    continue
                try:
                    etype = event.get("type", "message")
                    data = _json.dumps(event)
                except Exception:
                    etype = "message"
                    data = _json.dumps({"raw": str(event)})
                yield f"event: {etype}\ndata: {data}\n\n"
        finally:
            await unsubscribe(job_id, queue)

    return _StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{job_id}/checkpoint/{checkpoint_key}")
async def get_job_checkpoint(
    job_id: str,
    checkpoint_key: str,
    user: dict = Depends(_get_auth()),
):
    """Load a single persisted checkpoint snapshot for a job (owner-scoped).

    ``checkpoint_key`` is restricted to ``[a-zA-Z0-9_-]{1,64}`` to avoid path-style probes.
    """
    if not _CHECKPOINT_KEY_PATTERN.fullmatch(checkpoint_key or ""):
        raise HTTPException(status_code=400, detail="Invalid checkpoint_key")
    try:
        return await get_job_checkpoint_service(
            job_id=job_id,
            checkpoint_key=checkpoint_key,
            user=user,
            resolve_job=_resolve_job,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GET /api/jobs/%s/checkpoint/%s error", job_id, checkpoint_key)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}")
async def update_job(
    job_id: str,
    update: JobStatusUpdate,
    user: dict = Depends(_get_auth()),
):
    """Update job status and optionally broadcast progress."""
    try:
        try:
            from backend.orchestration.event_bus import publish
        except Exception:
            publish = None
        return await update_job_service(
            job_id=job_id,
            update=update,
            user=user,
            resolve_job=_resolve_job,
            runtime_state_getter=_get_runtime_state,
            publish=publish,
        )
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
            from backend.orchestration.event_bus import publish

            await publish(job_id, "job_cancelled", {"job_id": job_id})
        except Exception:
            pass
        return {"success": True, "job_id": job_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/pause")
async def pause_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Pause a running job. The auto-runner will check for 'paused' status and suspend."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        await rs.update_job_state(job_id, "paused")
        try:
            from backend.orchestration.event_bus import publish

            await publish(job_id, "job_paused", {"job_id": job_id})
        except Exception:
            pass
        return {"success": True, "job_id": job_id, "status": "paused"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/stop")
async def stop_job(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Immediately cancel a running job and interrupt its background asyncio Task."""
    try:
        await _resolve_job(job_id, user)
        rs = _get_runtime_state()
        await rs.update_job_state(job_id, "cancelled")
        try:
            from backend.orchestration.event_bus import publish

            await publish(job_id, "job_cancelled", {"job_id": job_id, "reason": "user_stopped"})
        except Exception:
            pass
        # Interrupt the running asyncio Task if one exists
        task = get_running_task(job_id)
        if task is not None and not task.done():
            task.cancel()
            unregister_running_task(job_id)
        return {"success": True, "job_id": job_id, "status": "cancelled", "interrupted": task is not None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/retry-step/{step_id}")
async def retry_job_step(
    job_id: str,
    step_id: str,
    user: dict = Depends(_get_auth()),
):
    """Mark a failed/blocked step as pending so the runner can execute it again."""
    try:
        return await retry_step_service(
            job_id=job_id,
            step_id=step_id,
            user=user,
            runtime_state_getter=_get_runtime_state,
            pool_getter=_get_pool,
            assert_owner=_assert_owner,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/jobs/%s/retry-step/%s error", job_id, step_id)
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
            from backend.orchestration.event_bus import publish

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
            from backend.orchestration.event_bus import publish

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
        # success = product verdict (gates + job terminal state), not "HTTP OK" (that's status 200).
        bv = bool(proof.get("build_verified"))
        return {**proof, "success": bv}
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
            await conn.execute("DELETE FROM job_checkpoints WHERE job_id=$1", job_id)
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


# ── Steer / Cancel / Resume — wired to UnifiedWorkspace ──────────────────────

@router.post("/{job_id}/steer")
async def steer_job(job_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Inject a steering instruction into a running job."""
    job = await _resolve_job(job_id, user)
    try:
        body = await request.json()
    except Exception:
        body = {}
    message = body.get("message") or body.get("instruction") or ""
    resume = body.get("resume", True)
    try:
        import json as _json
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE jobs SET
                   steer_queue = COALESCE(steer_queue, '[]'::jsonb) || $1::jsonb
                   WHERE id = $2""",
                _json.dumps([{"message": message, "resume": resume}]),
                job_id,
            )
        rs = _get_runtime_state()
        steering_payload = {"message": message, "resume": bool(resume), "source": "workspace"}
        try:
            from ..server import _project_workspace_path
            from ..orchestration.contract_artifacts import persist_steering_contract_delta

            project_id = str(job.get("project_id") or job.get("id") or job_id).strip()
            workspace_path = _project_workspace_path(project_id)
            workspace_path.mkdir(parents=True, exist_ok=True)
            delta_result = persist_steering_contract_delta(
                str(workspace_path),
                job,
                message,
                approved_by=str((user or {}).get("id") or "human_user"),
            )
            steering_payload["contract_delta"] = delta_result.get("delta")
            steering_payload["active_goal"] = delta_result.get("active_goal")
            await rs.save_checkpoint(
                job_id,
                "steering_context",
                {
                    "active_goal": delta_result.get("active_goal"),
                    "latest_instruction": message,
                    "latest_delta": delta_result.get("delta"),
                    "contract_missing": delta_result.get("missing"),
                    "contract_satisfied": delta_result.get("satisfied"),
                },
            )
        except Exception:
            logger.exception("steer_job: contract delta persistence failed")
            await rs.save_checkpoint(
                job_id,
                "steering_context",
                {
                    "active_goal": f"{job.get('goal') or ''}\n\nUser steering request:\n{message}".strip(),
                    "latest_instruction": message,
                    "latest_delta": None,
                    "contract_missing": {},
                    "contract_satisfied": False,
                },
            )
        await rs.append_job_event(
            job_id,
            "workspace_steer_queued",
            steering_payload,
        )
        try:
            from ..orchestration.event_bus import publish

            await publish(
                job_id,
                "workspace_steer_queued",
                steering_payload,
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning("steer_job db: %s", e)
    return {"accepted": True, "job_id": job_id, "message": message}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, user: dict = Depends(get_current_user)):
    """Resume a paused or failed job."""
    try:
        job = await _resolve_job(job_id, user)
        from ..orchestration.auto_runner import prepare_failed_job_for_rerun, resume_job as _resume
        import asyncio

        pool = await _get_pool()
        rs = _get_runtime_state()
        if pool is not None:
            rs.set_pool(pool)

        project_id = str(job.get("project_id") or job.get("id") or job_id).strip()
        if not project_id:
            project_id = job_id
        from ..server import _project_workspace_path

        workspace_path = _project_workspace_path(project_id)
        workspace_path.mkdir(parents=True, exist_ok=True)
        await prepare_failed_job_for_rerun(job_id)
        await rs.update_job_state(
            job_id,
            "running",
            {"current_phase": "resuming_from_workspace", "resume_requested": True},
        )
        await rs.append_job_event(
            job_id,
            "job_resume_requested",
            {"job_id": job_id, "workspace_path": str(workspace_path), "project_id": project_id},
        )
        try:
            from ..orchestration.event_bus import publish

            await publish(
                job_id,
                "job_resume_requested",
                {"job_id": job_id, "workspace_path": str(workspace_path), "project_id": project_id},
            )
        except Exception:
            pass

        asyncio.create_task(_resume(job_id, str(workspace_path), pool))
        return {"resumed": True, "job_id": job_id, "workspace_path": str(workspace_path)}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("resume_job: %s", e)
        return {"resumed": False, "job_id": job_id, "error": str(e)}
