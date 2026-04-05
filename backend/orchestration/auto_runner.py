"""
auto_runner.py — Continuous execution engine for CrucibAI.
Runs a job to completion: plan → approve → execute all steps → verify → finalize.
Never stops unless: success, max retries, unrecoverable failure, or cancellation.
"""
import asyncio
import logging
import json
from typing import Dict, Any, Optional

from .runtime_state import (
    get_job, update_job_state, get_steps, create_step,
    append_job_event, save_checkpoint, load_checkpoint
)
from .dag_engine import (
    get_ready_steps,
    has_blocking_failure,
    block_dependents,
    execution_quiescent,
    scheduler_deadlocked,
)
from .executor import execute_step
from .verifier import verify_step
from .fixer import classify_failure, build_retry_plan, apply_fix, MAX_RETRIES
from .event_bus import publish
from .planner import generate_plan
from .runtime_health import is_infrastructure_failure
from proof import proof_service

logger = logging.getLogger(__name__)

# Safety limits
MAX_TOTAL_RETRIES = 10
POLL_INTERVAL_SEC = 0.5
MAX_CONCURRENT_STEPS = 4


async def run_job_to_completion(job_id: str,
                                 workspace_path: str = "",
                                 db_pool=None) -> Dict[str, Any]:
    """
    Main auto-runner loop.
    mode=auto: runs until done without asking user.
    mode=guided: pauses before risky actions (future: emit guided_approval_needed event).
    """
    job = await get_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}

    if job["status"] in ("completed", "failed", "cancelled"):
        return {"success": job["status"] == "completed",
                "status": job["status"]}

    if db_pool:
        proof_service.set_pool(db_pool)

    await update_job_state(job_id, "running")
    await publish(job_id, "job_started",
                  {"job_id": job_id, "mode": job.get("mode"), "goal": job.get("goal", "")})
    await append_job_event(job_id, "job_started",
                           {"mode": job.get("mode"), "goal": job.get("goal", "")})

    total_retries = 0

    while True:
        # Check cancellation
        job = await get_job(job_id)
        if job["status"] == "cancelled":
            logger.info("auto_runner: job %s cancelled", job_id)
            return {"success": False, "status": "cancelled"}

        # Get ready steps (deps satisfied, status=pending)
        ready = await get_ready_steps(job_id)

        if not ready:
            steps_snapshot = await get_steps(job_id)
            if not steps_snapshot:
                logger.error(
                    "auto_runner: job %s has no job_steps — plan/run-auto must create steps first",
                    job_id,
                )
                await update_job_state(
                    job_id,
                    "failed",
                    {"current_phase": "no_job_steps"},
                )
                await publish(
                    job_id,
                    "job_failed",
                    {"reason": "no_job_steps", "message": "No DAG steps for this job; create a new plan."},
                )
                await append_job_event(
                    job_id,
                    "job_failed",
                    {"reason": "no_job_steps"},
                )
                return {
                    "success": False,
                    "status": "failed",
                    "reason": "no_job_steps",
                }

            if await scheduler_deadlocked(job_id):
                logger.error("auto_runner: job %s scheduler deadlock (pending steps never become ready)", job_id)
                await update_job_state(job_id, "failed", {"current_phase": "scheduler_deadlock"})
                await publish(
                    job_id,
                    "job_failed",
                    {"reason": "scheduler_deadlock", "message": "Step dependencies cannot be satisfied."},
                )
                return {"success": False, "status": "failed", "reason": "scheduler_deadlock"}

            if await execution_quiescent(job_id):
                # All work finished or blocked off — finalize (blocked/failed handled below)
                break

            if await has_blocking_failure(job_id):
                await update_job_state(job_id, "failed",
                                       {"current_phase": "blocked"})
                await publish(job_id, "job_failed",
                              {"reason": "Blocking step failure with no retry available"})
                return {"success": False, "status": "failed",
                        "reason": "Blocking step failure"}
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue

        # Execute ready steps (up to MAX_CONCURRENT_STEPS in parallel)
        batch = ready[:MAX_CONCURRENT_STEPS]
        tasks = [
            asyncio.create_task(
                _run_single_step(step, job, workspace_path, db_pool)
            )
            for step in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for step, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error("auto_runner: step %s raised %s",
                             step["step_key"], result)
                result = {"success": False, "error": str(result)}

            if not result["success"]:
                err_msg = result.get("error", "") or ""
                if is_infrastructure_failure(err_msg):
                    logger.error(
                        "auto_runner: infra failure on step %s — not retrying: %s",
                        step["step_key"], err_msg[:200],
                    )
                    await block_dependents(job_id, step["step_key"])
                    continue

                total_retries += 1
                if total_retries > MAX_TOTAL_RETRIES:
                    await update_job_state(job_id, "failed",
                                           {"current_phase": "max_retries_exceeded"})
                    await publish(job_id, "job_failed",
                                  {"reason": f"Max retries ({MAX_TOTAL_RETRIES}) exceeded"})
                    return {"success": False, "status": "failed",
                            "reason": "max_retries_exceeded"}

                retry_count = step.get("retry_count", 0)
                if retry_count >= MAX_RETRIES:
                    # Block dependents and continue
                    await block_dependents(job_id, step["step_key"])
                else:
                    # Queue retry (reset to pending)
                    from .runtime_state import update_step_state
                    await update_step_state(step["id"], "pending", {
                        "retry_count": retry_count + 1,
                        "error_message": result.get("error", ""),
                    })
                    await publish(job_id, "step_retrying",
                                  {"step_key": step["step_key"],
                                   "attempt": retry_count + 1,
                                   "error": result.get("error", "")})

    # Finalize job
    steps = await get_steps(job_id)
    failed_steps = [s for s in steps if s["status"] == "failed"]
    blocked_steps = [s for s in steps if s["status"] == "blocked"]
    completed_steps = [s for s in steps if s["status"] == "completed"]

    # Quality score = % of steps that passed verification
    total = len(steps)
    quality_score = round((len(completed_steps) / max(1, total)) * 100)

    if blocked_steps:
        await update_job_state(job_id, "failed", {
            "current_phase": "dependency_blocked",
            "quality_score": quality_score,
            "blocked_steps": [s["step_key"] for s in blocked_steps],
        })
        await publish(job_id, "job_failed", {
            "reason": "dependency_blocked",
            "quality_score": quality_score,
            "blocked_steps": [s["step_key"] for s in blocked_steps],
        })
        await append_job_event(job_id, "job_failed", {
            "reason": "dependency_blocked",
            "blocked_step_keys": [s["step_key"] for s in blocked_steps],
        })
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "dependency_blocked",
        }

    if failed_steps and quality_score < 60:
        await update_job_state(job_id, "failed", {
            "current_phase": "completed_with_failures",
            "quality_score": quality_score,
        })
        await publish(job_id, "job_failed",
                      {"quality_score": quality_score,
                       "failed_steps": [s["step_key"] for s in failed_steps]})
        return {"success": False, "status": "failed", "quality_score": quality_score}
    else:
        ws = (workspace_path or "").strip()
        if not ws:
            await update_job_state(job_id, "failed", {
                "current_phase": "no_workspace_for_preview",
                "quality_score": quality_score,
            })
            await append_job_event(job_id, "job_preview_failed", {
                "issues": ["No workspace_path — cannot verify preview bundle."],
            })
            await publish(job_id, "job_failed", {
                "reason": "no_workspace",
                "quality_score": quality_score,
            })
            return {
                "success": False,
                "status": "failed",
                "quality_score": quality_score,
                "reason": "no_workspace",
            }

        from .preview_gate import verify_preview_workspace
        pv = await verify_preview_workspace(ws)
        if not pv["passed"]:
            await update_job_state(job_id, "failed", {
                "current_phase": "preview_gate_failed",
                "quality_score": quality_score,
            })
            await append_job_event(job_id, "job_preview_failed", {
                "issues": pv["issues"],
                "score": pv["score"],
            })
            await publish(job_id, "job_failed", {
                "reason": "preview_gate",
                "issues": pv["issues"],
                "quality_score": quality_score,
            })
            return {
                "success": False,
                "status": "failed",
                "quality_score": quality_score,
                "reason": "preview_gate",
            }

        await update_job_state(job_id, "completed", {
            "current_phase": "completed",
            "quality_score": quality_score,
        })
        # Build completion summary
        proof = await proof_service.get_proof(job_id)
        summary = _build_completion_summary(steps, proof)
        await publish(job_id, "job_completed", {
            "quality_score": quality_score,
            "summary": summary,
            "proof": proof,
        })
        await append_job_event(job_id, "job_completed",
                               {"quality_score": quality_score, "summary": summary})
        return {"success": True, "status": "completed",
                "quality_score": quality_score, "summary": summary}


async def _run_single_step(step: Dict, job: Dict,
                            workspace_path: str, db_pool) -> Dict[str, Any]:
    """Execute one step with retry-aware error handling."""
    # Update current phase in job
    await update_job_state(job["id"], "running",
                           {"current_phase": step.get("phase", "")})
    return await execute_step(
        step, job, workspace_path,
        db_pool=db_pool,
        proof_service=proof_service,
    )


def _build_completion_summary(steps: list, proof: Dict) -> Dict[str, Any]:
    """Build the data for the completion card UI."""
    bundle = proof.get("bundle", {})
    return {
        "pages_created": len(bundle.get("files", [])),
        "api_routes_added": len(bundle.get("routes", [])),
        "db_tables_created": len(bundle.get("database", [])),
        "deploy_targets": len(bundle.get("deploy", [])),
        "total_steps": len(steps),
        "steps_completed": sum(1 for s in steps if s["status"] == "completed"),
        "quality_score": proof.get("quality_score", 0),
    }


# ── Checkpoint resume ─────────────────────────────────────────────────────────

async def resume_job(job_id: str, workspace_path: str = "",
                      db_pool=None) -> Dict[str, Any]:
    """Resume a job that was interrupted. Picks up from incomplete nodes."""
    job = await get_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}

    if db_pool:
        proof_service.set_pool(db_pool)

    # Reset any 'running' steps back to 'pending' (they were interrupted)
    steps = await get_steps(job_id)
    from .runtime_state import update_step_state
    for step in steps:
        if step["status"] == "running":
            await update_step_state(step["id"], "pending")

    logger.info("auto_runner: resuming job %s from checkpoint", job_id)
    await publish(job_id, "job_resumed", {"job_id": job_id})
    return await run_job_to_completion(job_id, workspace_path, db_pool)
