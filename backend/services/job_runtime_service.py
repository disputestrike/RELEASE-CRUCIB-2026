from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import HTTPException


RuntimeStateGetter = Callable[[], Any]
PoolGetter = Callable[[], Awaitable[Any]]
ProofGetter = Callable[[], Any]
OwnerAssert = Callable[[Optional[str], Optional[dict]], None]
ProjectWorkspacePath = Callable[[str], Path]


async def _load_job_or_404(
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: OwnerAssert,
):
    runtime_state = runtime_state_getter()
    pool = await pool_getter()
    runtime_state.set_pool(pool)
    job = await runtime_state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assert_owner(job.get("user_id"), user)
    return runtime_state, pool, job


async def get_job_trust_report_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    proof_service_getter: ProofGetter,
    assert_owner: OwnerAssert,
    roadmap_wiring_status: Callable[[], Any],
) -> Dict[str, Any]:
    runtime_state, pool, _job = await _load_job_or_404(
        job_id, user, runtime_state_getter, pool_getter, assert_owner
    )
    ps_mod = proof_service_getter()
    ps_mod.set_pool(pool)
    proof = await ps_mod.get_proof(job_id)
    return {
        "success": True,
        "job_id": job_id,
        "roadmap_wiring": roadmap_wiring_status(),
        "trust_score": proof.get("trust_score"),
        "class_weighted_score": proof.get("class_weighted_score"),
        "verification_class_counts": proof.get("verification_class_counts"),
        "truth_status": proof.get("truth_status"),
        "total_proof_items": proof.get("total_proof_items"),
        "category_counts": proof.get("category_counts"),
        "spec_compliance_percent": proof.get("spec_compliance_percent"),
        "spec_guard": proof.get("spec_guard"),
        "production_readiness_score": proof.get("production_readiness_score"),
        "scorecard": proof.get("scorecard"),
    }


async def cancel_job_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: OwnerAssert,
    publish: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    runtime_state, _pool, _job = await _load_job_or_404(
        job_id, user, runtime_state_getter, pool_getter, assert_owner
    )
    await runtime_state.update_job_state(job_id, "cancelled")
    if publish is not None:
        await publish(job_id, "job_cancelled", {"job_id": job_id})
    return {"success": True, "job_id": job_id, "status": "cancelled"}


async def resume_job_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: OwnerAssert,
    build_preflight_report: Callable[[], Awaitable[Dict[str, Any]]],
    collect_runtime_health_sync: Callable[[], Dict[str, Any]],
    append_job_event: Callable[[str, str, Dict[str, Any]], Awaitable[None]],
    background_add_task: Callable[..., Any],
    background_resume_callable: Callable[[str, str], Awaitable[None]] | Callable[[str, str], None],
    project_workspace_path: ProjectWorkspacePath,
) -> Dict[str, Any]:
    _runtime_state, _pool, job = await _load_job_or_404(
        job_id, user, runtime_state_getter, pool_getter, assert_owner
    )

    preflight = await build_preflight_report()
    await append_job_event(
        job_id,
        "preflight_report",
        {"preflight": preflight, "kind": "preflight_report.json"},
    )
    if not preflight.get("passed"):
        sync = collect_runtime_health_sync()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "runtime_unsatisfied",
                "message": "Preflight failed — runtimes, package managers, or health checks.",
                "issues": preflight.get("issues", []),
                "runtimes": sync,
                "preflight_report": preflight,
            },
        )

    ws = ""
    pid = job.get("project_id")
    if pid:
        root = project_workspace_path(pid).resolve()
        root.mkdir(parents=True, exist_ok=True)
        ws = str(root)
    background_add_task(background_resume_callable, job_id, ws)
    return {
        "success": True,
        "job_id": job_id,
        "stream_url": f"/api/jobs/{job_id}/stream",
        "websocket_url": f"/api/job/{job_id}/progress",
    }


async def steer_job_service(
    *,
    job_id: str,
    body: Any,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: OwnerAssert,
    append_job_event: Callable[[str, str, Dict[str, Any]], Awaitable[None]],
    build_steering_guidance: Callable[..., Dict[str, Any]],
    publish: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]],
    build_preflight_report: Callable[[], Awaitable[Dict[str, Any]]],
    collect_runtime_health_sync: Callable[[], Dict[str, Any]],
    background_add_task: Callable[..., Any],
    background_resume_callable: Callable[[str, str], Awaitable[None]] | Callable[[str, str], None],
    project_workspace_path: ProjectWorkspacePath,
) -> Dict[str, Any]:
    _runtime_state, _pool, job = await _load_job_or_404(
        job_id, user, runtime_state_getter, pool_getter, assert_owner
    )

    msg = ((getattr(body, "message", None) or "")).strip()
    resume_requested = bool(getattr(body, "resume", False))
    await append_job_event(
        job_id,
        "user_steering",
        {"message": msg[:12000], "resume_requested": resume_requested},
    )
    coach = build_steering_guidance(
        msg,
        resume=resume_requested,
        job_status=str(job.get("status") or ""),
    )
    guidance_kind = "resume_coach" if resume_requested else "steering_note"
    payload = {"kind": guidance_kind, **coach}
    await append_job_event(job_id, "brain_guidance", payload)
    if publish is not None:
        await publish(job_id, "brain_guidance", payload)

    if resume_requested:
        preflight = await build_preflight_report()
        await append_job_event(
            job_id,
            "preflight_report",
            {"preflight": preflight, "kind": "preflight_report.json"},
        )
        if not preflight.get("passed"):
            sync = collect_runtime_health_sync()
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "runtime_unsatisfied",
                    "message": "Preflight failed — runtimes, package managers, or health checks.",
                    "issues": preflight.get("issues", []),
                    "runtimes": sync,
                    "preflight_report": preflight,
                },
            )
        ws = ""
        pid = job.get("project_id")
        if pid:
            root = project_workspace_path(pid).resolve()
            root.mkdir(parents=True, exist_ok=True)
            ws = str(root)
        background_add_task(background_resume_callable, job_id, ws)

    return {
        "success": True,
        "job_id": job_id,
        "recorded": True,
        "resume_started": resume_requested,
        "guidance": coach,
        "stream_url": f"/api/jobs/{job_id}/stream",
    }


async def retry_step_service(
    *,
    job_id: str,
    step_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: OwnerAssert,
) -> Dict[str, Any]:
    runtime_state = runtime_state_getter()
    pool = await pool_getter()
    runtime_state.set_pool(pool)
    step = await runtime_state.get_step(step_id)
    if not step or step.get("job_id") != job_id:
        raise HTTPException(status_code=404, detail="Step not found")
    job = await runtime_state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assert_owner(job.get("user_id"), user)
    if step.get("status") not in ("failed", "blocked"):
        raise HTTPException(
            status_code=400,
            detail=f"Step is {step.get('status')}, can only retry failed/blocked steps",
        )
    retry_number = int(step.get("retry_count") or 0) + 1
    await runtime_state.update_step_state(
        step_id,
        "pending",
        {"retry_count": retry_number, "error_message": None},
    )
    return {
        "success": True,
        "step_id": step_id,
        "status": "pending",
        "retry_number": retry_number,
    }
