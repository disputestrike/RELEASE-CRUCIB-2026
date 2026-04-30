"""
auto_runner.py — Continuous execution engine for CrucibAI.
Runs a job to completion: plan → approve → execute all steps → verify → finalize.
Never stops unless: success, max retries, unrecoverable failure, or cancellation.

Job "completed" requires every DAG step in terminal success — not a partial % threshold.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.proof import proof_service

from .brain_repair import apply_targeted_repair, run_full_brain_repair
from .dag_engine import (
    block_dependents,
    execution_quiescent,
    get_ready_steps,
    has_blocking_failure,
    scheduler_deadlocked,
)
from .event_bus import publish
from .executor import execute_step
from .fixer import MAX_RETRIES, apply_fix, build_retry_plan, classify_failure
from .planner import generate_plan
from .runtime_health import is_infrastructure_failure
from .runtime_state import (
    append_job_event,
    create_step,
    get_job,
    get_steps,
    load_checkpoint,
    save_checkpoint,
    update_job_state,
    update_step_state,
)
from .verifier import verify_step
from .brain_narration import clear_progress_narrative_cache, maybe_emit_progress_narrative

logger = logging.getLogger(__name__)


async def _write_blueprint(
    workspace_path: str, job_id: str, reason: str, **kwargs
) -> None:
    ws = (workspace_path or "").strip()
    if not ws:
        return
    j = await get_job(job_id)
    goal = (j or {}).get("goal") or ""
    from .continuation_blueprint import write_continuation_blueprint

    write_continuation_blueprint(ws, job_id=job_id, goal=goal, reason=reason, **kwargs)


# Safety limits (global retry budget across all steps — was 10 and exhausted on ~4–5 flaky steps)
def _max_total_retries() -> int:
    try:
        return max(10, int(os.environ.get("CRUCIBAI_MAX_TOTAL_STEP_RETRIES", "40")))
    except ValueError:
        return 40


POLL_INTERVAL_SEC = 0.5


def _max_concurrent_steps(load_factor: float = 1.0) -> int:
    """Cap parallel step execution; override with CRUCIBAI_MAX_CONCURRENT_STEPS (min 1, max 32).
    load_factor can dynamically adjust the concurrency based on system load (0.1 to 2.0).
    """
    raw = (os.environ.get("CRUCIBAI_MAX_CONCURRENT_STEPS") or "").strip()
    default = 8
    base_concurrency = default
    if raw:
        try:
            base_concurrency = int(raw)
        except ValueError:
            pass
    
    # Apply load factor, ensuring it's within reasonable bounds
    adjusted_concurrency = int(base_concurrency * max(0.1, min(2.0, load_factor)))
    return max(1, min(32, adjusted_concurrency))


async def _job_with_steering_context(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Apply latest user steering to the in-memory job without erasing the original goal."""

    try:
        steering = await load_checkpoint(job_id, "steering_context") or {}
    except Exception:
        steering = {}
    active_goal = str((steering or {}).get("active_goal") or "").strip()
    if not active_goal:
        return job
    merged = dict(job or {})
    meta = dict(merged.get("metadata") or {})
    meta["original_goal"] = meta.get("original_goal") or merged.get("goal") or ""
    meta["steering_context"] = steering
    merged["metadata"] = meta
    merged["goal"] = active_goal
    return merged


def _skip_duplicate_final_preview(steps: List[Dict[str, Any]]) -> bool:
    """
    Optional local-dev escape hatch only.

    Production completion must always re-run the final preview gate against the
    final filesystem state. An earlier verification.preview step can become
    stale after later writes, repairs, or deploy packaging.
    """
    prod_markers = (
        os.environ.get("RAILWAY_ENVIRONMENT"),
        os.environ.get("CRUCIBAI_ENV"),
        os.environ.get("ENVIRONMENT"),
        os.environ.get("NODE_ENV"),
    )
    if any(str(v or "").strip().lower() == "production" for v in prod_markers):
        return False

    raw = os.environ.get("CRUCIBAI_SKIP_DUPLICATE_FINAL_PREVIEW", "0").strip().lower()
    if raw not in ("1", "true", "yes", "on"):
        return False
    return any(
        s.get("step_key") == "verification.preview" and s.get("status") == "completed"
        for s in steps
    )


def _html_has_app_root(html: str) -> bool:
    lowered = (html or "").lower()
    return (
        'id="root"' in lowered
        or "id='root'" in lowered
        or 'id="app"' in lowered
        or "id='app'" in lowered
    )


def _verify_final_preview_servability(
    job_id: str,
    workspace_path: str,
    job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Hard completion gate: preview must be statically servable.

    The browser/verifier gate proves the app can build. This gate proves the
    exact static-preview route contract has an HTML entry that can mount a
    client app before the job is marked completed.
    """
    issues: List[str] = []
    try:
        from backend.routes.preview_serve import _resolve_serve_root
        from backend.services.workspace_resolver import workspace_resolver
    except Exception as exc:
        return {
            "passed": False,
            "failure_reason": "preview_resolver_unavailable",
            "issues": [f"Preview resolver unavailable: {exc}"],
        }

    project_id = str((job or {}).get("project_id") or "").strip() or None
    resolved = workspace_resolver.workspace_for_job(job_id, project_id)
    raw_ws = Path(workspace_path).resolve() if workspace_path else resolved.workspace
    candidates = [raw_ws, resolved.workspace, *resolved.candidates]
    seen = set()
    serve_root: Optional[Path] = None
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        root = _resolve_serve_root(candidate)
        if root is not None:
            serve_root = root
            break

    if serve_root is None:
        return {
            "passed": False,
            "failure_reason": "preview_not_servable",
            "issues": ["Final preview gate could not find a servable index.html in dist/build/out/public/root."],
            "checked_roots": [str(p) for p in candidates[:8]],
        }

    index_path = serve_root / "index.html"
    if not index_path.exists() or not index_path.is_file():
        issues.append("Final preview index.html is missing.")
    else:
        html = index_path.read_text(encoding="utf-8", errors="replace")
        if not _html_has_app_root(html):
            issues.append("Final preview index.html does not contain a root/app mount element.")

    return {
        "passed": len(issues) == 0,
        "failure_reason": None if not issues else "preview_not_servable",
        "issues": issues,
        "serve_root": str(serve_root),
        "index_path": str(index_path),
        "dev_server_url": resolved.preview_url,
        "content_type": "text/html; charset=utf-8",
    }


def _step_failure_context(
    step: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract durable late-stage failure metadata from executor results."""
    vr = (
        result.get("verification")
        if isinstance(result.get("verification"), dict)
        else {}
    )
    issues = vr.get("issues") if isinstance(vr.get("issues"), list) else []
    context: Dict[str, Any] = {
        "step_key": step.get("step_key"),
        "error": result.get("error") or "",
        "failure_reason": vr.get("failure_reason")
        or result.get("reason")
        or "step_failed",
        "stage": vr.get("stage") or step.get("step_key"),
        "issues": issues[:12],
    }
    for key in (
        "failed_checks",
        "checks_passed",
        "checks_total",
        "recommendation",
        "score",
    ):
        if key in vr:
            context[key] = vr[key]
    return context


async def run_job_to_completion(
    job_id: str, workspace_path: str = "", db_pool=None
) -> Dict[str, Any]:
    """
    Main auto-runner loop.
    mode=auto: runs until done without asking user.
    mode=guided: pauses before risky actions (future: emit guided_approval_needed event).

    CRITICAL: This function MUST return a terminal state (SUCCESS, FAILED, or CANCELED).
    Never returns undefined state or background_crash.
    """
    try:
        job = await get_job(job_id)
        if not job:
            error_result = {
                "success": False,
                "error": "Job not found",
                "status": "failed",
                "reason": "job_not_found",
            }
            await _finalize_job_with_failure(job_id, "job_not_found", "Job not found")
            return error_result

        if job["status"] in ("completed", "failed", "cancelled"):
            return {"success": job["status"] == "completed", "status": job["status"]}

        if db_pool:
            proof_service.set_pool(db_pool)

        await update_job_state(job_id, "running")
        _bp_meta: dict = {}
        try:
            from .brain_policy import job_started_policy_meta

            _bp_meta = job_started_policy_meta() or {}
        except Exception:
            pass
        await publish(
            job_id,
            "job_started",
            {
                "job_id": job_id,
                "mode": job.get("mode"),
                "goal": job.get("goal", ""),
                **_bp_meta,
            },
        )
        await append_job_event(
            job_id,
            "job_started",
            {"mode": job.get("mode"), "goal": job.get("goal", ""), **_bp_meta},
        )

        # ── Pre-build intelligence briefing ────────────────────────────────────
        # Ensure brain memory tables exist
        try:
            from .brain_intelligence import (
                ensure_brain_tables,
                get_prebuild_intelligence,
            )

            await ensure_brain_tables()
            goal_text = (job.get("goal") or "").strip()
            if goal_text:
                briefing = await get_prebuild_intelligence(goal_text)
                if briefing.get("intelligence_available"):
                    await append_job_event(job_id, "brain_prebuild_briefing", briefing)
                    await publish(
                        job_id,
                        "brain_prebuild_briefing",
                        {
                            "similar_builds": briefing.get("similar_builds_found", 0),
                            "predicted_failures": len(
                                briefing.get("predicted_failures", [])
                            ),
                            "agents_to_watch": briefing.get("agents_to_watch", [])[:5],
                        },
                    )
                    import logging as _log

                    _log.getLogger(__name__).info(
                        "auto_runner: prebuild briefing — %d similar builds, %d predictions",
                        briefing.get("similar_builds_found", 0),
                        len(briefing.get("predicted_failures", [])),
                    )
        except Exception as _be:
            import logging as _log

            _log.getLogger(__name__).warning(
                "auto_runner: prebuild briefing failed: %s", _be
            )

        from .execution_authority import attach_elite_context_to_job, elite_job_metadata

        attach_elite_context_to_job(job, workspace_path or "")
        await append_job_event(
            job_id,
            "execution_authority",
            {"kind": "execution_authority.json", **elite_job_metadata(job)},
        )

        # Pre-execution THINK: user-facing brain line before any step runs (classify path + intent).
        job_for_think = await get_job(job_id)
        steps_for_think = await get_steps(job_id)
        try:
            from .brain_narration import emit_execution_think_guidance

            await emit_execution_think_guidance(
                job_id, job_for_think or job, steps_for_think
            )
        except Exception as _think_e:
            logger.warning(
                "auto_runner: execution think guidance skipped: %s", _think_e
            )

        total_retries = 0

        # MAIN EXECUTION LOOP (wrapped with exception handler below)
        # Implement watchdog for long-run stability (T39)
        watchdog_timeout = int(os.environ.get("CRUCIBAI_WATCHDOG_TIMEOUT_SEC", "1800")) # 30 minutes default
        try:
            result = await asyncio.wait_for(
                _execute_job_loop(job_id, workspace_path, db_pool, total_retries),
                timeout=watchdog_timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error("auto_runner: Job %s exceeded watchdog timeout of %d seconds. Marking as failed.", job_id, watchdog_timeout)
            await _finalize_job_with_failure(job_id, "watchdog_timeout", f"Job exceeded watchdog timeout of {watchdog_timeout} seconds")
            return {"success": False, "status": "failed", "reason": "watchdog_timeout"}

    except asyncio.TimeoutError:
        # Explicit timeout (not background_crash)
        error_msg = "Job execution exceeded 30 minute timeout"
        await _finalize_job_with_failure(job_id, "execution_timeout", error_msg)
        return {
            "success": False,
            "status": "failed",
            "reason": "execution_timeout",
            "details": error_msg,
        }

    except asyncio.CancelledError:
        # Job was canceled (not background_crash)
        await update_job_state(job_id, "cancelled")
        await publish(job_id, "job_cancelled", {"reason": "User canceled"})
        return {"success": False, "status": "cancelled", "reason": "user_canceled"}

    except Exception as e:
        # CATCH-ALL: Prevents background_crash (every exception captured)
        import traceback

        error_msg = f"{type(e).__name__}: {str(e)}"
        tb_full = traceback.format_exc()
        logger.error(
            "auto_runner: UNHANDLED EXCEPTION in job %s: %s",
            job_id,
            error_msg,
            exc_info=True,
        )
        # Persist traceback to job_events so it's queryable without Railway CLI.
        try:
            await append_job_event(
                job_id,
                "orchestrator_error_traceback",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:2000],
                    "traceback": tb_full[-6000:],
                },
            )
        except Exception:
            logger.exception("auto_runner: failed to persist orchestrator traceback")
        await _finalize_job_with_failure(job_id, "orchestrator_error", error_msg)
        return {
            "success": False,
            "status": "failed",
            "reason": "orchestrator_error",
            "details": error_msg,
            "traceback": tb_full,
        }

    finally:
        # ALWAYS finalize job state
        try:
            await _ensure_job_finalized(job_id)
        except Exception as e:
            logger.error("auto_runner: Error finalizing job %s: %s", job_id, e)


async def _execute_job_loop(
    job_id: str, workspace_path: str, db_pool, total_retries: int
) -> Dict[str, Any]:
    """Inner execution loop (wrapped by exception handlers in run_job_to_completion)."""
    while True:
        # Check cancellation
        job = await get_job(job_id)
        if job["status"] == "cancelled":
            logger.info("auto_runner: job %s cancelled", job_id)
            return {"success": False, "status": "cancelled"}
        job = await _job_with_steering_context(job_id, job)

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
                    {
                        "reason": "no_job_steps",
                        "message": "No DAG steps for this job; create a new plan.",
                    },
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
                logger.error(
                    "auto_runner: job %s scheduler deadlock (pending steps never become ready)",
                    job_id,
                )
                # Enhance deadlock diagnosis payload (T35)
                steps_snapshot = await get_steps(job_id)
                pending_steps = [s for s in steps_snapshot if s.get("status") == "pending"]
                blocked_steps = [s for s in steps_snapshot if s.get("status") == "blocked"]
                
                deadlock_details = {
                    "reason": "scheduler_deadlock",
                    "message": "Step dependencies cannot be satisfied. Possible circular dependency or unresolvable blocks.",
                    "pending_steps_count": len(pending_steps),
                    "blocked_steps_count": len(blocked_steps),
                    "pending_step_keys": [s.get("step_key") for s in pending_steps],
                    "blocked_step_keys": [s.get("step_key") for s in blocked_steps],
                }

                await update_job_state(
                    job_id, "failed", {"current_phase": "scheduler_deadlock", **deadlock_details}
                )
                await publish(
                    job_id,
                    "job_failed",
                    deadlock_details,
                )
                await append_job_event(job_id, "scheduler_deadlock_detected", deadlock_details)
                return {
                    "success": False,
                    "status": "failed",
                    "reason": "scheduler_deadlock",
                    "details": deadlock_details,
                }

            if await execution_quiescent(job_id):
                # All work finished or blocked off — finalize (blocked/failed handled below)
                break

            if await has_blocking_failure(job_id):
                await update_job_state(job_id, "failed", {"current_phase": "blocked"})
                await publish(
                    job_id,
                    "job_failed",
                    {"reason": "Blocking step failure with no retry available"},
                )
                return {
                    "success": False,
                    "status": "failed",
                    "reason": "Blocking step failure",
                }
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue

        # Execute ready steps (up to N in parallel)
        # Implement global backpressure control (T34)
        # In a real system, this would check a global counter or system metrics (CPU/Memory)
        # For now, we simulate backpressure by dynamically adjusting concurrency based on a load factor
        # A load factor < 1.0 means the system is under load and should reduce concurrency
        current_load_factor = 1.0 # This could be fetched from a system monitor
        max_conc = _max_concurrent_steps(load_factor=current_load_factor)
        
        # If max_conc is 0 (extreme backpressure), pause execution
        if max_conc <= 0:
            logger.warning("auto_runner: global backpressure active, pausing execution for job %s", job_id)
            await asyncio.sleep(POLL_INTERVAL_SEC * 2)
            continue
            
        batch = ready[:max_conc]
        if len(batch) > 1:
            logger.info(
                "auto_runner: job %s parallel batch size=%s keys=%s",
                job_id,
                len(batch),
                [s.get("step_key") for s in batch],
            )
        phases_in_batch = sorted(
            {((s.get("phase") or "") or "").strip() for s in batch if (s.get("phase") or "").strip()}
        )
        phase_label = (
            phases_in_batch[0]
            if len(phases_in_batch) == 1
            else f"parallel:{len(batch)}"
        )
        try:
            await update_job_state(
                job_id,
                "running",
                {"current_phase": phase_label or "running"},
            )
        except Exception:
            logger.exception("auto_runner: update_job_state(running) failed — continuing")
        tasks = [
            asyncio.create_task(_run_single_step(step, job, workspace_path, db_pool))
            for step in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for step, result in zip(batch, results):
          try:
            if isinstance(result, Exception):
                logger.error("auto_runner: step %s raised %s", step["step_key"], result)
                result = {"success": False, "error": str(result)}

            if not result["success"]:
                err_msg = result.get("error", "") or ""
                failure_context = _step_failure_context(step, result)
                if is_infrastructure_failure(err_msg):
                    logger.error(
                        "auto_runner: infra failure on step %s — not retrying: %s",
                        step["step_key"],
                        err_msg[:200],
                    )
                    await append_job_event(
                        job_id,
                        "step_infrastructure_failure",
                        failure_context,
                        step_id=step["id"],
                    )
                    await block_dependents(job_id, step["step_key"])
                    continue

                total_retries += 1
                max_total = _max_total_retries()
                if total_retries > max_total:
                    await update_job_state(
                        job_id,
                        "failed",
                        {
                            "current_phase": "max_retries_exceeded",
                            "failure_reason": failure_context.get("failure_reason"),
                            "failure_details": err_msg[:1000],
                        },
                    )
                    await publish(
                        job_id,
                        "job_failed",
                        {
                            "reason": "max_retries_exceeded",
                            "message": f"Max retries ({max_total}) exceeded",
                            **failure_context,
                        },
                    )
                    await append_job_event(
                        job_id,
                        "job_failed",
                        {
                            "reason": "max_retries_exceeded",
                            "max_total_retries": max_total,
                            **failure_context,
                        },
                        step_id=step["id"],
                    )
                    await _write_blueprint(
                        workspace_path,
                        job_id,
                        "max_retries_exceeded",
                        failed_step_keys=[step["step_key"]],
                        open_gates=["step_verification"],
                    )
                    return {
                        "success": False,
                        "status": "failed",
                        "reason": "max_retries_exceeded",
                    }

                retry_count = step.get("retry_count", 0)
                if retry_count >= MAX_RETRIES:
                    # Block dependents and continue
                    await append_job_event(
                        job_id,
                        "step_retry_exhausted",
                        {
                            **failure_context,
                            "retry_count": retry_count,
                            "max_retries": MAX_RETRIES,
                        },
                        step_id=step["id"],
                    )
                    await publish(
                        job_id,
                        "step_retry_exhausted",
                        {
                            "step_key": step["step_key"],
                            "retry_count": retry_count,
                            "max_retries": MAX_RETRIES,
                            "failure_reason": failure_context.get("failure_reason"),
                            "stage": failure_context.get("stage"),
                        },
                    )
                    await block_dependents(job_id, step["step_key"])
                else:
                    err_txt = result.get("error", "") or ""
                    vr = (
                        result.get("verification")
                        if isinstance(result.get("verification"), dict)
                        else {}
                    )
                    v_issues = (
                        vr.get("issues") if isinstance(vr.get("issues"), list) else None
                    )
                    vstub = {
                        "issues": (
                            v_issues if v_issues else ([err_txt] if err_txt else [])
                        )
                    }
                    ftype = classify_failure({**step, "error_message": err_txt}, vstub)
                    rplan = build_retry_plan(
                        ftype, {**step, "error_message": err_txt}, vstub
                    )

                    # ── BRAIN REPAIR: read workspace, fix code, mutate params ──
                    repair = await run_full_brain_repair(
                        workspace_path=workspace_path or "",
                        step_key=step.get("step_key", ""),
                        error_message=err_txt,
                        retry_count=retry_count,
                        job=job,
                    )
                    # Merge repair mutations into the step state so the next
                    # execution reads them and behaves differently
                    step_mutations = {
                        "retry_count": retry_count + 1,
                        "error_message": err_txt,
                        "brain_strategy": repair.get("strategy", "unknown"),
                        "brain_explanation": repair.get("explanation", ""),
                        "workspace_fixed": bool(repair.get("workspace_fixed", False)),
                        "files_repaired": repair.get("files_repaired", []),
                        "brain_mutations_json": repair.get("mutations") or {},
                    }

                    await append_job_event(
                        job_id,
                        "fixer_retry_queued",
                        {
                            "step_key": step["step_key"],
                            "failure_type": ftype,
                            "failure_reason": failure_context.get("failure_reason"),
                            "stage": failure_context.get("stage"),
                            "issues": failure_context.get("issues", []),
                            "failed_checks": failure_context.get("failed_checks", []),
                            "retry_plan_actions": rplan.get("retry_plan", []),
                            "brain_strategy": repair["strategy"],
                            "brain_explanation": repair["explanation"],
                            "brain_mutations": list(repair["mutations"].keys()),
                            "attempt_next": retry_count + 1,
                        },
                        step_id=step["id"],
                    )
                    await apply_fix({**step, "error_message": err_txt}, rplan)
                    # Queue retry with mutations applied
                    from .runtime_state import update_step_state

                    await update_step_state(step["id"], "pending", step_mutations)
                    await publish(
                        job_id,
                        "step_retrying",
                        {
                            "step_key": step["step_key"],
                            "attempt": retry_count + 1,
                            "error": err_txt,
                            "failure_reason": failure_context.get("failure_reason"),
                            "stage": failure_context.get("stage"),
                            "brain_strategy": repair["strategy"],
                            "brain_explanation": repair["explanation"],
                        },
                    )

          except Exception:
            logger.exception(
                "auto_runner: per-step result processing failed for step=%s — continuing",
                (step or {}).get("step_key") if isinstance(step, dict) else "?",
            )
        try:
            from datetime import datetime, timezone

            ok_keys: List[str] = []
            for step, result in zip(batch, results):
                if isinstance(result, Exception):
                    continue
                if isinstance(result, dict) and result.get("success"):
                    sk = step.get("step_key")
                    if sk:
                        ok_keys.append(str(sk))
            if ok_keys:
                await save_checkpoint(
                    job_id,
                    "last_milestone_batch",
                    {
                        "phase": phase_label,
                        "completed_step_keys": ok_keys[:32],
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception:
            logger.debug("auto_runner: milestone checkpoint skipped", exc_info=True)

    # Finalize job
    steps = await get_steps(job_id)
    failed_steps = [s for s in steps if s["status"] == "failed"]
    blocked_steps = [s for s in steps if s["status"] == "blocked"]
    completed_steps = [s for s in steps if s["status"] == "completed"]

    # ── Post-build learning — store outcome so future builds benefit ─────────
    try:
        from .brain_intelligence import record_build_outcome

        total = len(steps)
        completion_pct = (len(completed_steps) / max(1, total)) * 100
        goal_text = (job.get("goal") or "").strip()
        if goal_text:
            await record_build_outcome(
                goal=goal_text,
                job_id=job_id,
                step_completion_pct=completion_pct,
                quality_score=round(completion_pct),
                failed_steps=[
                    {
                        "step_key": s.get("step_key", ""),
                        "error_message": str(s.get("error_message") or "")[:300],
                        "brain_strategy": str(s.get("brain_strategy") or ""),
                        "brain_explanation": str(s.get("brain_explanation") or ""),
                        "files_repaired": s.get("files_repaired") or [],
                        "retry_count": s.get("retry_count") or 0,
                        "was_eventually_fixed": False,
                    }
                    for s in failed_steps
                ],
                completed_steps=[s.get("step_key", "") for s in completed_steps],
                repairs_applied=[
                    {
                        "step_key": s.get("step_key", ""),
                        "strategy": str(s.get("brain_strategy") or ""),
                    }
                    for s in steps
                    if s.get("brain_strategy")
                ],
            )
    except Exception as _le:
        import logging as _log

        _log.getLogger(__name__).warning(
            "auto_runner: post-build learning failed: %s", _le
        )
    failed_step_details = [
        {
            "step_key": s.get("step_key"),
            "status": s.get("status"),
            "retry_count": s.get("retry_count") or 0,
            "error_message": str(s.get("error_message") or "")[:500],
        }
        for s in failed_steps
    ]
    blocked_step_details = [
        {
            "step_key": s.get("step_key"),
            "status": s.get("status"),
            "retry_count": s.get("retry_count") or 0,
            "error_message": str(s.get("error_message") or "")[:500],
        }
        for s in blocked_steps
    ]

    # Quality score = % of steps that passed verification
    total = len(steps)
    quality_score = round((len(completed_steps) / max(1, total)) * 100)

    if blocked_steps:
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "dependency_blocked",
                "quality_score": quality_score,
                "blocked_steps": [s["step_key"] for s in blocked_steps],
                "failure_reason": "dependency_blocked",
                "failure_details": json.dumps(
                    {
                        "blocked_steps": blocked_step_details,
                        "failed_steps": failed_step_details,
                    }
                )[:2000],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "dependency_blocked",
                "quality_score": quality_score,
                "blocked_steps": [s["step_key"] for s in blocked_steps],
                "blocked_step_details": blocked_step_details,
                "failed_step_details": failed_step_details,
            },
        )
        await append_job_event(
            job_id,
            "job_failed",
            {
                "reason": "dependency_blocked",
                "blocked_step_keys": [s["step_key"] for s in blocked_steps],
                "blocked_step_details": blocked_step_details,
                "failed_step_details": failed_step_details,
            },
        )
        await _write_blueprint(
            workspace_path,
            job_id,
            "dependency_blocked",
            failed_step_keys=[s["step_key"] for s in blocked_steps],
            open_gates=["downstream_steps"],
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "dependency_blocked",
        }

    # Strict: any failed step means the plan did not complete (no "60% is good enough").
    if failed_steps:
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "steps_failed",
                "quality_score": quality_score,
                "failed_step_keys": [s["step_key"] for s in failed_steps],
                "failure_reason": "steps_failed",
                "failure_details": json.dumps({"failed_steps": failed_step_details})[
                    :2000
                ],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "one_or_more_steps_failed",
                "quality_score": quality_score,
                "failed_steps": [s["step_key"] for s in failed_steps],
                "failed_step_details": failed_step_details,
            },
        )
        await append_job_event(
            job_id,
            "job_failed",
            {
                "reason": "steps_failed",
                "failed_step_keys": [s["step_key"] for s in failed_steps],
                "failed_step_details": failed_step_details,
                "quality_score": quality_score,
            },
        )
        await _write_blueprint(
            workspace_path,
            job_id,
            "one_or_more_steps_failed",
            failed_step_keys=[s["step_key"] for s in failed_steps],
            open_gates=["failed_step_verification"],
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "steps_failed",
            "failed_steps": [s["step_key"] for s in failed_steps],
        }

    # Every node must be completed — not left pending/skipped (should not happen if scheduler is sound).
    if len(completed_steps) != total:
        bad = [s for s in steps if s["status"] != "completed"]
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "incomplete_dag",
                "quality_score": quality_score,
                "non_completed": [
                    {"key": s["step_key"], "status": s["status"]} for s in bad
                ],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "incomplete_dag",
                "non_completed": [s["step_key"] for s in bad],
            },
        )
        return {
            "success": False,
            "status": "failed",
            "reason": "incomplete_dag",
            "quality_score": quality_score,
        }

    ws = (workspace_path or "").strip()
    if not ws:
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "no_workspace_for_preview",
                "quality_score": quality_score,
            },
        )
        await append_job_event(
            job_id,
            "job_preview_failed",
            {
                "issues": ["No workspace_path — cannot verify preview bundle."],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "no_workspace",
                "quality_score": quality_score,
            },
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "no_workspace",
        }

    from .preview_gate import verify_preview_workspace

    if _skip_duplicate_final_preview(steps):
        pv = {"passed": True, "issues": [], "score": 100, "proof": []}
        await append_job_event(
            job_id,
            "job_completion_gate",
            {
                "mode": "skipped_duplicate_full_preview",
                "reason": "verification.preview already passed; set CRUCIBAI_SKIP_DUPLICATE_FINAL_PREVIEW=0 to re-run",
            },
        )
    else:
        pv = await verify_preview_workspace(
            ws,
            goal=(job or {}).get("goal") or "",
            build_profile=(job or {}).get("build_kind") or (job or {}).get("build_profile") or "",
        )

    if not pv["passed"]:
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "preview_gate_failed",
                "quality_score": quality_score,
            },
        )
        await append_job_event(
            job_id,
            "job_preview_failed",
            {
                "issues": pv["issues"],
                "score": pv["score"],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "preview_gate",
                "issues": pv["issues"],
                "quality_score": quality_score,
            },
        )
        await _write_blueprint(
            workspace_path,
            job_id,
            "preview_gate_failed",
            open_gates=["verification.preview", "preview_bundle"],
            notes="; ".join(str(x) for x in (pv.get("issues") or [])[:12]),
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "preview_gate",
        }

    job_latest = await get_job(job_id)
    final_preview = _verify_final_preview_servability(job_id, ws, job_latest)
    if not final_preview.get("passed"):
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "preview_not_servable",
                "quality_score": quality_score,
                "failure_reason": final_preview.get("failure_reason") or "preview_not_servable",
                "failure_details": json.dumps(final_preview.get("issues") or [])[:1000],
            },
        )
        await append_job_event(
            job_id,
            "job_preview_failed",
            {
                "failure_reason": final_preview.get("failure_reason") or "preview_not_servable",
                "issues": final_preview.get("issues") or [],
                "checked_roots": final_preview.get("checked_roots") or [],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": final_preview.get("failure_reason") or "preview_not_servable",
                "issues": final_preview.get("issues") or [],
                "quality_score": quality_score,
            },
        )
        await _write_blueprint(
            ws,
            job_id,
            final_preview.get("failure_reason") or "preview_not_servable",
            open_gates=["final_preview_serve", "preview_bundle"],
            notes="; ".join(str(x) for x in (final_preview.get("issues") or [])[:12]),
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": final_preview.get("failure_reason") or "preview_not_servable",
        }
    await append_job_event(
        job_id,
        "final_preview_ready",
        {
            "dev_server_url": final_preview.get("dev_server_url"),
            "serve_root": final_preview.get("serve_root"),
            "content_type": final_preview.get("content_type"),
        },
    )

    goal_text = (job_latest or {}).get("goal") or ""
    contract_artifacts = None
    try:
        from .contract_artifacts import persist_contract_artifacts

        contract_artifacts = persist_contract_artifacts(ws, job_latest or job or {})
        contract_dict = contract_artifacts.get("contract_dict") or {}
        await append_job_event(
            job_id,
            "build_contract_reconciled",
            {
                "build_class": contract_dict.get("build_class"),
                "satisfied": bool(contract_artifacts.get("satisfied")),
                "missing": contract_artifacts.get("missing") or {},
                "route_map": contract_artifacts.get("route_map") or {},
                "dependency_edge_count": sum(
                    len(v) for v in (contract_artifacts.get("dependency_graph") or {}).values()
                ),
            },
        )
        if contract_dict.get("build_class") == "web_marketing_site" and not contract_artifacts.get("satisfied"):
            missing = contract_artifacts.get("missing") or {}
            await update_job_state(
                job_id,
                "failed",
                {
                    "current_phase": "contract_coverage_failed",
                    "quality_score": min(quality_score, 40),
                    "failure_reason": "contract_coverage_failed",
                    "failure_details": json.dumps(missing)[:1000],
                },
            )
            await append_job_event(
                job_id,
                "job_failed",
                {
                    "reason": "contract_coverage_failed",
                    "build_class": contract_dict.get("build_class"),
                    "missing": missing,
                },
            )
            await publish(
                job_id,
                "job_failed",
                {
                    "reason": "contract_coverage_failed",
                    "quality_score": min(quality_score, 40),
                    "missing": missing,
                },
            )
            await _write_blueprint(
                ws,
                job_id,
                "contract_coverage_failed",
                open_gates=["build_contract", "final_assembly", "route_map"],
                notes=json.dumps(missing)[:1000],
            )
            return {
                "success": False,
                "status": "failed",
                "quality_score": min(quality_score, 40),
                "reason": "contract_coverage_failed",
                "missing": missing,
            }
    except Exception as contract_exc:
        logger.warning("build contract reconciliation skipped: %s", contract_exc)

    from .build_integrity_validator import validate_workspace_integrity

    biv = validate_workspace_integrity(
        ws,
        goal=goal_text,
        phase="final",
        build_target=(job_latest or {}).get("build_target")
        or (job_latest or {}).get("crucib_build_target"),
    )
    await append_job_event(
        job_id,
        "build_integrity_validator_result",
        {
            "attempt": 0,
            "score": biv.get("score"),
            "profile": biv.get("profile"),
            "phase": biv.get("phase"),
            "recommendation": biv.get("recommendation"),
            "retry_targets": biv.get("retry_targets") or [],
            "retry_route": biv.get("retry_route") or {},
            "issues": (biv.get("issues") or [])[:20],
        },
    )
    if not biv.get("passed"):
        try:
            requested_biv_repairs = int(os.environ.get("CRUCIBAI_BIV_REPAIR_ATTEMPTS", "1") or "1")
        except Exception:
            requested_biv_repairs = 1
        max_biv_repairs = max(0, min(2, requested_biv_repairs))
        for attempt in range(1, max_biv_repairs + 1):
            from .targeted_dag_retry import run_targeted_biv_retry

            repair = await run_targeted_biv_retry(
                workspace_path=ws or "",
                biv_result=biv,
                retry_count=attempt - 1,
                job=job_latest or job,
            )
            await append_job_event(
                job_id,
                "build_integrity_validator_repair_attempt",
                {
                    "attempt": attempt,
                    "retry_targets": biv.get("retry_targets") or [],
                    "retry_route": biv.get("retry_route") or {},
                    "strategy": repair.get("strategy", "unknown"),
                    "targeted_retry_plan": repair.get("plan") or {},
                    "targeted_attempts": repair.get("attempts") or [],
                    "workspace_fixed": bool(repair.get("workspace_fixed")),
                    "files_repaired": repair.get("files_repaired") or [],
                },
            )
            if not repair.get("workspace_fixed") and not repair.get("files_repaired"):
                break
            biv = validate_workspace_integrity(
                ws,
                goal=goal_text,
                phase="final",
                build_target=(job_latest or {}).get("build_target")
                or (job_latest or {}).get("crucib_build_target"),
            )
            await append_job_event(
                job_id,
                "build_integrity_validator_result",
                {
                    "attempt": attempt,
                    "score": biv.get("score"),
                    "profile": biv.get("profile"),
                    "phase": biv.get("phase"),
                    "recommendation": biv.get("recommendation"),
                    "retry_targets": biv.get("retry_targets") or [],
                    "retry_route": biv.get("retry_route") or {},
                    "issues": (biv.get("issues") or [])[:20],
                },
            )
            if biv.get("passed"):
                break
    if not biv.get("passed"):
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "build_integrity_validator_failed",
                "quality_score": quality_score,
                "failure_reason": "build_integrity_validator",
                "failure_details": json.dumps(biv.get("issues") or [])[:1000],
            },
        )
        await append_job_event(
            job_id,
            "job_failed",
            {
                "reason": "build_integrity_validator",
                "score": biv.get("score"),
                "profile": biv.get("profile"),
                "retry_targets": biv.get("retry_targets") or [],
                "retry_route": biv.get("retry_route") or {},
                "issues": (biv.get("issues") or [])[:50],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "build_integrity_validator",
                "quality_score": quality_score,
                "integrity_score": biv.get("score"),
                "retry_route": biv.get("retry_route") or {},
                "issues": (biv.get("issues") or [])[:20],
            },
        )
        await _write_blueprint(
            ws,
            job_id,
            "build_integrity_validator",
            open_gates=["build_integrity_validator", *list(biv.get("retry_targets") or [])],
            notes="; ".join(str(x) for x in (biv.get("issues") or [])[:12]),
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "integrity_score": biv.get("score"),
            "reason": "build_integrity_validator",
            "retry_route": biv.get("retry_route") or {},
        }

    from .delivery_gate import write_biv_marker

    write_biv_marker(ws or "", biv)

    from .enforcement.enforcement_engine import run_completion_enforcement_gate

    egr = await run_completion_enforcement_gate(
        job_id=job_id,
        workspace_path=ws,
        goal=goal_text,
        db_pool=db_pool,
        job_dict=job_latest,
    )
    await append_job_event(
        job_id,
        "enforcement_result",
        {"kind": "enforcement_result.json", **(egr.get("metadata") or {})},
    )
    if egr.get("blocked"):
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": "critical_enforcement_block",
                "quality_score": quality_score,
            },
        )
        await append_job_event(
            job_id,
            "job_failed",
            {
                "reason": "critical_enforcement_block",
                "issues": (egr.get("issues") or [])[:50],
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": "critical_enforcement_block",
                "quality_score": quality_score,
            },
        )
        await _write_blueprint(
            ws,
            job_id,
            "critical_enforcement_block",
            open_gates=["enforcement", "proof_bundle"],
            notes="; ".join(str(x) for x in (egr.get("issues") or [])[:12]),
        )
        return {
            "success": False,
            "status": "failed",
            "quality_score": quality_score,
            "reason": "critical_enforcement_block",
        }

    # Optional: headless browser QA + visual gate (set CRUCIBAI_BROWSER_QA_BLOCK=1 to fail job)
    try:
        from .browser_qa import run_browser_qa
        from .delivery_gate import check_visual_qa_gate

        bqa = await run_browser_qa(ws or "")
        issues = bqa.get("issues") or []
        orphan_count = sum(1 for x in issues if "orphan" in str(x).lower())
        vqa = check_visual_qa_gate(
            {"score": int(bqa.get("score") or 0), "orphan_count": orphan_count}
        )
        await append_job_event(
            job_id,
            "browser_qa_result",
            {
                "passed": bool(bqa.get("passed")),
                "score": bqa.get("score"),
                "skipped": bool(bqa.get("skipped")),
                "visual_qa_passed": bool(vqa.get("passed")),
            },
        )
        _block = os.environ.get("CRUCIBAI_BROWSER_QA_BLOCK", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if _block and not bqa.get("skipped") and not vqa.get("passed"):
            await update_job_state(
                job_id,
                "failed",
                {
                    "current_phase": "browser_qa_block",
                    "quality_score": quality_score,
                    "failure_reason": "browser_qa",
                },
            )
            await append_job_event(
                job_id,
                "job_failed",
                {"reason": "browser_qa", "issues": vqa.get("issues") or []},
            )
            await publish(
                job_id,
                "job_failed",
                {"reason": "browser_qa", "quality_score": quality_score},
            )
            await _write_blueprint(
                ws,
                job_id,
                "browser_qa",
                open_gates=["browser_qa", "visual_qa"],
                notes="; ".join(str(x) for x in (vqa.get("issues") or [])[:12]),
            )
            return {
                "success": False,
                "status": "failed",
                "quality_score": quality_score,
                "reason": "browser_qa",
            }
    except Exception as _bqa_exc:
        logger.warning("browser_qa pipeline skipped: %s", _bqa_exc)

    try:
        from .workspace_assembly import seal_completed_job_workspace

        seal = await seal_completed_job_workspace(job_id, workspace_path, steps)
        if seal:
            await append_job_event(
                job_id,
                "workspace_sealed",
                {
                    "kind": "seal.json",
                    "artifact_file_count": seal.get("artifact_file_count"),
                    "manifest_sha256": seal.get("manifest_sha256"),
                },
            )
    except Exception as _seal_e:
        logger.warning("workspace seal skipped: %s", _seal_e)

    await update_job_state(
        job_id,
        "completed",
        {
            "current_phase": "completed",
            "quality_score": quality_score,
        },
    )
    proof = await proof_service.get_proof(job_id)
    summary = _build_completion_summary(steps, proof)
    await publish(
        job_id,
        "job_completed",
        {
            "quality_score": quality_score,
            "summary": summary,
            "proof": proof,
        },
    )
    await append_job_event(
        job_id,
        "job_completed",
        {
            "quality_score": quality_score,
            "summary": summary,
            "enforcement_advisory": bool(egr.get("advisory_would_block")),
        },
    )
    return {
        "success": True,
        "status": "completed",
        "quality_score": quality_score,
        "summary": summary,
    }


async def _run_single_step(
    step: Dict, job: Dict, workspace_path: str, db_pool
) -> Dict[str, Any]:
    """Execute one step with retry-aware error handling."""
    return await execute_step(
        step,
        job,
        workspace_path,
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


async def prepare_failed_job_for_rerun(job_id: str) -> int:
    """
    User continued after a terminal failure: re-open the job so the runner loop runs again.

    Resets failed/blocked steps to pending and moves job status back to running.
    Returns number of steps reset (0 if job was not failed).
    """
    job = await get_job(job_id)
    if not job or job.get("status") not in {"failed", "blocked", "cancelled"}:
        return 0
    steps = await get_steps(job_id)
    n = 0
    for step in steps:
        st = step.get("status")
        if st in ("failed", "blocked"):
            await update_step_state(
                step["id"],
                "pending",
                {
                    "error_message": "",
                    "verifier_status": "",
                },
            )
            n += 1
    await update_job_state(
        job_id,
        "running",
        {"current_phase": "resuming_after_failure"},
    )
    await append_job_event(
        job_id,
        "job_reactivated",
        {"reason": "failed_job_rerun", "steps_reset": n},
    )
    await publish(
        job_id,
        "job_reactivated",
        {"reason": "failed_job_rerun", "steps_reset": n},
    )
    logger.info("auto_runner: reactivated job %s (%d steps reset)", job_id, n)
    return n


async def resume_job(
    job_id: str, workspace_path: str = "", db_pool=None
) -> Dict[str, Any]:
    """Resume a job that was interrupted. Picks up from incomplete nodes."""
    job = await get_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}

    if db_pool:
        proof_service.set_pool(db_pool)

    await prepare_failed_job_for_rerun(job_id)

    # Reset any 'running' steps back to 'pending' (they were interrupted)
    steps = await get_steps(job_id)
    for step in steps:
        if step["status"] == "running":
            await update_step_state(step["id"], "pending")

    logger.info("auto_runner: resuming job %s from checkpoint", job_id)
    await publish(job_id, "job_resumed", {"job_id": job_id})
    return await run_job_to_completion(job_id, workspace_path, db_pool)


# ============================================================================
# FIX #1: DETERMINISTIC JOB LIFECYCLE HANDLERS
# Prevents background_crash by ensuring explicit terminal states
# ============================================================================


async def _finalize_job_with_failure(job_id: str, reason: str, details: str) -> None:
    """Finalize job with explicit failure reason (never background_crash)."""
    try:
        await update_job_state(
            job_id,
            "failed",
            {
                "current_phase": reason,
                "failure_reason": reason,
                "failure_details": details,
            },
        )
        await publish(
            job_id,
            "job_failed",
            {
                "reason": reason,
                "details": details,
            },
        )
        await append_job_event(
            job_id,
            "job_failed",
            {
                "reason": reason,
                "details": details,
            },
        )
    except Exception as e:
        logger.error("auto_runner: Error finalizing job %s with failure: %s", job_id, e)


async def _ensure_job_finalized(job_id: str) -> None:
    """Ensure job has a terminal state (SUCCESS, FAILED, or CANCELED)."""
    try:
        clear_progress_narrative_cache(job_id)
        job = await get_job(job_id)
        if not job:
            return

        # If job is still in "running" state, mark as failed
        if job.get("status") == "running":
            logger.warning(
                "auto_runner: Job %s still in running state at finalization — marking as failed",
                job_id,
            )
            await _finalize_job_with_failure(
                job_id,
                "incomplete_at_finalization",
                "Job reached finalization without terminal state",
            )
    except Exception as e:
        logger.error("auto_runner: Error ensuring job finalized: %s", e)
