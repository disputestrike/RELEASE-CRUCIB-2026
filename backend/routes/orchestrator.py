from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from ..services.orchestration_service import (
    estimate_orchestration_service,
    generate_public_plan_service,
    planner_project_state_service,
    public_plan_summary_service,
    update_last_build_state_service,
)
from pydantic import BaseModel
from ..deps import get_user_credits
logger = logging.getLogger(__name__)

def _get_server_helpers():
    """Lazy wrapper to avoid circular import with server.py."""
    from ..server import _get_server_helpers as _ssh
    return _ssh()


router = APIRouter(prefix="/api", tags=["orchestrator"])


def _get_auth():
    from ..server import get_current_user

    return get_current_user


def _get_optional_user():
    from ..server import get_optional_user

    return get_optional_user


def _get_server_globals():
    # FIX: AGENT_DAG / LAST_BUILD_STATE / RECENT_AGENT_SELECTION_LOGS were
    # never module-level attributes of server.py — accessing server.AGENT_DAG
    # always raised AttributeError, crashing the workspace screen.
    # AGENT_DAG now lives in agent_dag.py; the state containers are in server.py.
    from ..agent_dag import AGENT_DAG as _dag
    from .. import server as _srv
    _last  = getattr(_srv, "LAST_BUILD_STATE", {})
    _recnt = getattr(_srv, "RECENT_AGENT_SELECTION_LOGS", [])
    return _dag, _last, _recnt







import asyncio as _asyncio
import sys as _sys

_sys.path.insert(0, os.path.dirname(__file__))


# Lazy-load orchestration modules to avoid circular imports
def _get_orchestration():
    from ..orchestration import auto_runner as ar_mod
    from ..orchestration import dag_engine
    from ..orchestration import planner as planner_mod
    from ..orchestration import runtime_state

    from ..proof import proof_service as ps_mod

    return runtime_state, dag_engine, planner_mod, ar_mod, ps_mod


class PlanRequest(BaseModel):
    project_id: Optional[str] = None  # optional — auto-assigned from user.id if missing
    goal: str
    mode: Optional[str] = "guided"
    build_target: Optional[str] = (
        None  # vite_react | next_app_router | static_site | api_backend | agent_workflow
    )


class RunAutoRequest(BaseModel):
    job_id: str
    workspace_path: Optional[str] = ""


class CreateJobRequest(BaseModel):
    project_id: str
    goal: str
    mode: Optional[str] = "guided"


class CostEstimateRequest(BaseModel):
    project_id: Optional[str] = None
    goal: str
    build_target: Optional[str] = None


try:
    from ..server import BuildGoalRequest
except ImportError:

    class BuildGoalRequest(BaseModel):
        goal: str
        mode: Optional[str] = "guided"


async def _orchestrator_planner_project_state(user: Optional[dict] = None) -> Dict[str, Any]:
    """Shared planner context used by orchestrator and job creation."""
    return await planner_project_state_service(user, user_credits=get_user_credits)


def _update_last_build_state(plan: Dict[str, Any]) -> None:
    _, LAST_BUILD_STATE, RECENT_AGENT_SELECTION_LOGS = _get_server_globals()
    return update_last_build_state_service(
        plan,
        last_build_state=LAST_BUILD_STATE,
        recent_agent_selection_logs=RECENT_AGENT_SELECTION_LOGS,
        logger=logger,
    )


def _public_plan_summary(
    plan: Dict[str, Any], *, max_agents: int = 60
) -> Dict[str, Any]:
    return public_plan_summary_service(plan, max_agents=max_agents)


# ── Build targets (execution modes — broad platform, honest per-run scope) ───


@router.get("/orchestrator/build-targets")
async def list_build_targets():
    """Catalog of Auto-Runner execution targets for the workspace UI."""
    from ..orchestration.build_targets import build_target_catalog

    return {"success": True, "targets": build_target_catalog()}


@router.get("/debug/agent-info")
async def get_agent_info():
    """Expose current DAG and last-build agent selection metrics."""
    AGENT_DAG, LAST_BUILD_STATE, RECENT_AGENT_SELECTION_LOGS = _get_server_globals()
    return {
        "total_agents_available": len(AGENT_DAG),
        "agents_in_dag": sorted(list(AGENT_DAG.keys())),
        "agent_families": {
            "3d_webgl": len(
                [a for a in AGENT_DAG if "3D" in a or "Canvas" in a or "WebGL" in a]
            ),
            "ml_ai": len(
                [a for a in AGENT_DAG if a.startswith("ML ") or "Embeddings" in a]
            ),
            "blockchain": len(
                [
                    a
                    for a in AGENT_DAG
                    if "Blockchain" in a
                    or "Smart Contract" in a
                    or "Web3" in a
                    or "DeFi" in a
                    or "Contract " in a
                ]
            ),
            "iot": len(
                [
                    a
                    for a in AGENT_DAG
                    if "IoT" in a
                    or "Microcontroller" in a
                    or "Sensor" in a
                    or "Edge Computing" in a
                ]
            ),
            "data_science": len(
                [
                    a
                    for a in AGENT_DAG
                    if "Jupyter" in a
                    or "Data " in a
                    or "Time Series" in a
                    or "Statistical" in a
                    or "Report Generation" in a
                ]
            ),
            "infrastructure": len(
                [
                    a
                    for a in AGENT_DAG
                    if "Kubernetes" in a
                    or "Serverless" in a
                    or "Edge Deployment" in a
                    or "Load Balancer" in a
                    or "DevOps" in a
                    or "Message Queue" in a
                    or "Disaster Recovery" in a
                ]
            ),
            "testing": len(
                [
                    a
                    for a in AGENT_DAG
                    if "Chaos" in a
                    or "Mutation" in a
                    or "Property-Based" in a
                    or "Smoke Test" in a
                    or "Synthetic" in a
                    or "Load Test" in a
                    or "E2E" in a
                ]
            ),
            "business_logic": len(
                [
                    a
                    for a in AGENT_DAG
                    if "Workflow" in a
                    or "Business Rules" in a
                    or "Approval" in a
                    or "Audit & Compliance" in a
                    or "Notification Rules" in a
                    or "Scheduling" in a
                    or "Multi-tenant" in a
                    or "RBAC" in a
                ]
            ),
        },
        "last_build": LAST_BUILD_STATE,
        "selection_log_tail": RECENT_AGENT_SELECTION_LOGS,
        "selection_logic_working": True,
    }


@router.get("/debug/agent-selection-logs")
async def get_agent_selection_logs():
    """Expose recent agent-selection log lines for environments without Railway CLI access."""
    _, _, RECENT_AGENT_SELECTION_LOGS = _get_server_globals()
    return {
        "logs": RECENT_AGENT_SELECTION_LOGS,
        "count": len(RECENT_AGENT_SELECTION_LOGS),
    }


@router.post("/build")
async def public_build_plan(
    body: BuildGoalRequest,
    user: Optional[dict] = Depends(_get_optional_user()),
):
    """
    Public, read-only planner alias for production routing verification.

    This endpoint does not create projects or jobs; it only returns the
    structured orchestrator plan for the supplied goal.
    """
    goal = (body.goal or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    try:
        _, _, planner_mod, _, _ = _get_orchestration()
        plan = await generate_public_plan_service(
            goal=goal,
            user=user,
            planner_mod=planner_mod,
            planner_project_state=await _orchestrator_planner_project_state(user),
            update_last_build_state=_update_last_build_state,
        )
        return {"success": True, "plan": plan}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("public /build planning error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build/summary")
async def public_build_plan_summary(
    body: BuildGoalRequest,
    user: Optional[dict] = Depends(_get_optional_user()),
):
    """
    Compact public planner response for live verification and orchestration UI probes.

    Returns the same real planner decision as /api/build, but trims the payload to the
    minimum proof surface needed for production checks.
    """
    goal = (body.goal or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    try:
        _, _, planner_mod, _, _ = _get_orchestration()
        plan = await generate_public_plan_service(
            goal=goal,
            user=user,
            planner_mod=planner_mod,
            planner_project_state=await _orchestrator_planner_project_state(user),
            update_last_build_state=_update_last_build_state,
        )
        return {"success": True, "plan": _public_plan_summary(plan)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("public /build/summary planning error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Cost estimator (pre-execution, no auth required) ──────────────────────────


@router.post("/orchestrator/estimate")
async def estimate_cost(
    body: CostEstimateRequest,
    user: Optional[dict] = Depends(_get_optional_user()),
):
    """
    Pre-execution cost estimate. Show before user approves plan.
    Returns estimated_tokens, estimated_credits, cost_range.
    """
    try:
        from ..orchestration.build_targets import normalize_build_target

        _, _, planner_mod, _, _ = _get_orchestration()
        return await estimate_orchestration_service(
            goal=body.goal,
            build_target=body.build_target,
            user=user,
            planner_mod=planner_mod,
            normalize_build_target=normalize_build_target,
            planner_project_state=await _orchestrator_planner_project_state(user),
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "estimate": {
                "estimated_credits": 5,
                "cost_range": {
                    "min_credits": 3,
                    "max_credits": 15,
                    "typical_credits": 5,
                },
            },
        }


# ── Plan generation ───────────────────────────────────────────────────────────


@router.post("/orchestrator/plan")
async def create_plan(body: PlanRequest, user: dict = Depends(_get_auth())):
    """Generate a structured build plan before execution. Returns plan JSON + estimate."""
    (
        _user_credits,
        _assert_job_owner_match,
        _resolve_job_project_id_for_user,
        _project_workspace_path,
    ) = _get_server_helpers()
    try:
        from ..orchestration.build_targets import (
            build_target_meta,
            normalize_build_target,
        )

        runtime_state, dag_engine, planner_mod, _, _ = _get_orchestration()
        try:
            from ..db_pg import get_pg_pool

            pool = await get_pg_pool()
        except Exception:
            pool = None
        if pool:
            runtime_state.set_pool(pool)

        # Resolve effective_project_id: use provided project_id, or fall back to user id, or generate one
        effective_project_id = (
            (body.project_id or "").strip()
            or str((user or {}).get("id") or "")
            or str(__import__("uuid").uuid4())
        )

        # Defensive FK guard: ensure a projects row exists before inserting into jobs.
        # This keeps plan creation stable even if runtime_state adapters drift.
        if pool:
            try:
                async with pool.acquire() as conn:
                    try:
                        await conn.execute(
                            """
                            INSERT INTO projects (id, doc)
                            VALUES ($1, $2::jsonb)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            str(effective_project_id),
                            _json.dumps({
                                "user_id": str((user or {}).get("id") or ""),
                                "created_by": "orchestrator.plan",
                            }),
                        )
                    except Exception:
                        await conn.execute(
                            """
                            INSERT INTO projects (id, user_id, name, status, created_at, updated_at)
                            VALUES ($1::uuid, $2::uuid, $3, 'active', NOW(), NOW())
                            ON CONFLICT (id) DO NOTHING
                            """,
                            str(effective_project_id),
                            str((user or {}).get("id") or effective_project_id),
                            "Auto Workspace",
                        )
            except Exception as exc:
                logger.warning("orchestrator/plan: project FK preflight skipped: %s", exc)

        # Generate plan
        plan = await planner_mod.generate_plan(
            body.goal, project_state=await _orchestrator_planner_project_state(user)
        )
        _update_last_build_state(plan)
        requested_target = (body.build_target or "").strip()
        bt = normalize_build_target(
            requested_target or plan.get("recommended_build_target")
        )
        plan["crucib_build_target"] = bt
        estimate = planner_mod.estimate_tokens(plan)

        # Resolve project_id — use provided, or fall back to user id, or generate one
        # Create job record
        job = await runtime_state.create_job(
            project_id=effective_project_id,
            mode=body.mode or "guided",
            goal=body.goal,
            user_id=user.get("id"),
        )

        # Store plan
        import uuid as _uuid

        plan_id = str(_uuid.uuid4())
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                INSERT INTO build_plans (id, job_id, project_id, goal, plan_json, status, created_at)
                VALUES ($1,$2,$3,$4,$5,'draft',NOW())
            """,
                        plan_id,
                        job["id"],
                        effective_project_id,
                        body.goal,
                        _json.dumps(plan),
                    )
            except Exception as e:
                logger.warning("Could not store build plan in DB: %s", e)

        # Persist plan steps as job_steps
        from ..orchestration.dag_engine import build_dag_from_plan

        step_defs = build_dag_from_plan(plan)
        for idx, sd in enumerate(step_defs):
            await runtime_state.create_step(
                job_id=job["id"],
                step_key=sd["step_key"],
                agent_name=sd["agent_name"],
                phase=sd["phase"],
                depends_on=sd["depends_on"],
                order_index=idx,
            )

        from ..orchestration.capability_notice import capability_notice_lines

        btm = build_target_meta(bt)
        return {
            "success": True,
            "job_id": job["id"],
            "plan": plan,
            "estimate": estimate,
            "step_count": len(step_defs),
            "missing_inputs": plan.get("missing_inputs", []),
            "risk_flags": plan.get("risk_flags", []),
            "capability_notice": capability_notice_lines(body.goal, bt),
            "build_target": bt,
            "build_target_meta": btm,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("orchestrator/plan error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Run auto ──────────────────────────────────────────────────────────────────


@router.get("/orchestrator/runtime-health")
async def orchestrator_runtime_health():
    """
    Preflight: Python + Node (and npm path) as required by the Auto-Runner verifier.
    Call before run-auto; run-auto also enforces this gate.
    """
    try:
        from ..orchestration.runtime_health import (
            collect_runtime_health,
            collect_runtime_health_sync,
            extended_autorunner_preflight_issues,
            skip_node_verify_env,
        )

        sync = collect_runtime_health_sync()
        issues = await extended_autorunner_preflight_issues()
        full = await collect_runtime_health()
        return {
            "success": True,
            "ok": len(issues) == 0,
            "issues": issues,
            "runtimes": full,
            "node_verify_enforced": not skip_node_verify_env(),
        }
    except Exception as e:
        logger.exception("orchestrator/runtime-health error")
        raise HTTPException(status_code=500, detail=str(e))


async def _background_auto_runner_job(job_id: str, workspace_path: str) -> None:
    """Runs after HTTP response so the client can open SSE; do not use ensure_future here."""
    try:
        from ..db_pg import get_pg_pool
        from ..orchestration import auto_runner as _orch_ar
        from ..orchestration import runtime_state as _orch_rs

        pool = await get_pg_pool()
        if pool is None:
            logger.error("auto_runner: no database pool for job %s", job_id)
            return
        _orch_rs.set_pool(pool)
        ws = (workspace_path or "").strip()
        if ws:
            try:
                from ..orchestration.elite_prompt_loader import (
                    elite_prompt_fingerprint,
                    load_elite_autonomous_prompt,
                    write_elite_directive_to_workspace,
                )

                _elite = load_elite_autonomous_prompt()
                if _elite and write_elite_directive_to_workspace(ws, _elite):
                    await _orch_rs.append_job_event(
                        job_id,
                        "elite_builder_prompt",
                        {
                            "kind": "elite_builder_prompt.json",
                            "sha16": elite_prompt_fingerprint(_elite),
                            "path": "proof/ELITE_EXECUTION_DIRECTIVE.md",
                        },
                    )
            except Exception:
                logger.exception("auto_runner: elite directive for job %s", job_id)
        await _orch_ar.prepare_failed_job_for_rerun(job_id)
        result = await _orch_ar.run_job_to_completion(
            job_id, workspace_path=workspace_path or "", db_pool=pool
        )
        await _orch_rs.append_job_event(
            job_id,
            "background_runner_completed",
            {
                "success": bool((result or {}).get("success")),
                "status": (result or {}).get("status"),
                "reason": (result or {}).get("reason"),
                "details": str((result or {}).get("details") or "")[:1000],
            },
        )
        if result and not result.get("success"):
            job = await _orch_rs.get_job(job_id)
            if job and job.get("status") not in {
                "failed",
                "completed",
                "cancelled",
                "canceled",
            }:
                reason = result.get("reason") or "auto_runner_failed"
                details = str(result.get("details") or result.get("error") or reason)[
                    :1000
                ]
                await _orch_rs.update_job_state(
                    job_id,
                    "failed",
                    {
                        "current_phase": reason,
                        "failure_reason": reason,
                        "failure_details": details,
                    },
                )
    except Exception as e:
        logger.exception("auto_runner: background job %s raised", job_id)
        try:
            import traceback

            from ..db_pg import get_pg_pool as _gp
            from ..orchestration import runtime_state as _ors
            from ..orchestration.event_bus import publish as _pub

            pool = await _gp()
            _ors.set_pool(pool)
            reason = "background_runner_exception"
            msg = str(e)[:500]
            payload = {
                "reason": reason,
                "exception_type": type(e).__name__,
                "error": msg,
                "traceback_tail": traceback.format_exc()[-2000:],
            }
            await _ors.update_job_state(
                job_id,
                "failed",
                {
                    "current_phase": reason,
                    "failure_reason": reason,
                    "failure_details": msg,
                    "error_message": msg,
                },
            )
            await _ors.append_job_event(job_id, "job_failed", payload)
            await _pub(
                job_id,
                "job_failed",
                {k: v for k, v in payload.items() if k != "traceback_tail"},
            )
        except Exception:
            logger.exception(
                "auto_runner: could not persist background exception for job %s", job_id
            )


async def _background_resume_auto_job(job_id: str, workspace_path: str) -> None:
    try:
        from ..db_pg import get_pg_pool
        from ..orchestration import auto_runner as _orch_ar
        from ..orchestration import runtime_state as _orch_rs

        pool = await get_pg_pool()
        if pool is None:
            logger.error("resume_job: no database pool for job %s", job_id)
            return
        _orch_rs.set_pool(pool)
        result = await _orch_ar.resume_job(
            job_id, workspace_path=workspace_path or "", db_pool=pool
        )
        await _orch_rs.append_job_event(
            job_id,
            "background_runner_completed",
            {
                "resume": True,
                "success": bool((result or {}).get("success")),
                "status": (result or {}).get("status"),
                "reason": (result or {}).get("reason"),
                "details": str((result or {}).get("details") or "")[:1000],
            },
        )
        if result and not result.get("success"):
            job = await _orch_rs.get_job(job_id)
            if job and job.get("status") not in {
                "failed",
                "completed",
                "cancelled",
                "canceled",
            }:
                reason = result.get("reason") or "auto_runner_failed"
                details = str(result.get("details") or result.get("error") or reason)[
                    :1000
                ]
                await _orch_rs.update_job_state(
                    job_id,
                    "failed",
                    {
                        "current_phase": reason,
                        "failure_reason": reason,
                        "failure_details": details,
                    },
                )
    except Exception as e:
        logger.exception("resume_job: background job %s raised", job_id)
        try:
            import traceback

            from ..db_pg import get_pg_pool as _gp
            from ..orchestration import runtime_state as _ors
            from ..orchestration.event_bus import publish as _pub

            pool = await _gp()
            _ors.set_pool(pool)
            reason = "background_runner_exception"
            msg = str(e)[:500]
            payload = {
                "reason": reason,
                "resume": True,
                "exception_type": type(e).__name__,
                "error": msg,
                "traceback_tail": traceback.format_exc()[-2000:],
            }
            await _ors.update_job_state(
                job_id,
                "failed",
                {
                    "current_phase": reason,
                    "failure_reason": reason,
                    "failure_details": msg,
                    "error_message": msg,
                },
            )
            await _ors.append_job_event(job_id, "job_failed", payload)
            await _pub(
                job_id,
                "job_failed",
                {k: v for k, v in payload.items() if k != "traceback_tail"},
            )
        except Exception:
            logger.exception(
                "resume_job: could not persist background exception for job %s", job_id
            )


@router.post("/orchestrator/run-auto")
async def run_auto(
    body: RunAutoRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(_get_auth()),
):
    """
    Start auto-runner for an existing job.
    Returns immediately with job_id; client streams progress via /api/jobs/{id}/stream.
    """
    (
        _user_credits,
        _assert_job_owner_match,
        _resolve_job_project_id_for_user,
        _project_workspace_path,
    ) = _get_server_helpers()
    try:
        from ..orchestration.preflight_report import build_preflight_report
        from ..orchestration.runtime_health import collect_runtime_health_sync
        from ..orchestration.runtime_state import append_job_event

        runtime_state, _, _, _, _ = _get_orchestration()
        from ..db_pg import get_pg_pool

        try:
            pool = await get_pg_pool()
        except Exception as exc:
            logger.warning("orchestrator/run-auto: continuing without DB pool: %s", exc)
            pool = None
        if pool is not None:
            runtime_state.set_pool(pool)

        job = await runtime_state.get_job(body.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        _assert_job_owner_match(job.get("user_id"), user)

        preflight = await build_preflight_report()
        await append_job_event(
            body.job_id,
            "preflight_report",
            {"preflight": preflight, "kind": "preflight_report.json"},
        )

        # Log preflight issues but don't block execution
        if not preflight["passed"]:
            logger.warning(f"Preflight issues: {preflight['issues']}")
            # Continue execution anyway - jobs can still run

        # Spec Guardian (Layer 1): record always; hard-block only when CRUCIBAI_SPEC_GUARD_MODE=strict
        import json as _sg_json

        from ..orchestration.spec_guardian import (
            evaluate_goal_against_runner,
            merge_plan_risk_flags_into_report,
        )

        goal_text = (job.get("goal") or "").strip()
        risk_flags = []
        plan_build_target = None
        prow = None
        if pool is not None:
            async with pool.acquire() as conn:
                prow = await conn.fetchrow(
                    "SELECT plan_json FROM build_plans WHERE job_id = $1 ORDER BY created_at DESC LIMIT 1",
                    body.job_id,
                )
        if prow and prow.get("plan_json"):
            try:
                _pj = _sg_json.loads(prow["plan_json"])
                risk_flags = _pj.get("risk_flags") or []
                plan_build_target = _pj.get("crucib_build_target")
            except Exception:
                risk_flags = []
        spec_base = evaluate_goal_against_runner(
            goal_text, build_target=plan_build_target
        )
        spec_guard = merge_plan_risk_flags_into_report(
            risk_flags,
            spec_base,
            build_target=plan_build_target,
        )
        await append_job_event(
            body.job_id,
            "spec_guardian",
            {"spec_guard": spec_guard, "kind": "spec_guardian.json"},
        )
        if spec_guard.get("blocks_run"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "spec_guard_blocked",
                    "message": (
                        "Spec Guardian blocked this run: goal asks for stacks or capabilities "
                        "this pipeline cannot produce. Set CRUCIBAI_SPEC_GUARD_MODE=advisory to allow, "
                        "or narrow the goal to match the Vite + React + Python sketch template."
                    ),
                    "spec_guard": spec_guard,
                },
            )

        ws = ""
        pid = job.get("project_id")
        if pid:
            root = _project_workspace_path(pid).resolve()
            root.mkdir(parents=True, exist_ok=True)
            ws = str(root)

        background_tasks.add_task(_background_auto_runner_job, body.job_id, ws)

        return {
            "success": True,
            "job_id": body.job_id,
            "stream_url": f"/api/jobs/{body.job_id}/stream",
            "websocket_url": f"/api/job/{body.job_id}/progress",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("orchestrator/run-auto error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestrator/build-jobs")
async def list_orchestrator_build_jobs(
    user: dict = Depends(_get_optional_user()),
    limit: int = 30,
):
    """List recent Auto-Runner jobs for the signed-in (or guest) user."""
    if not user or not user.get("id"):
        return {"success": True, "jobs": []}
    try:
        runtime_state, _, _, _, _ = _get_orchestration()
        from ..db_pg import get_pg_pool

        try:
            pool = await get_pg_pool()
        except Exception as exc:
            logger.warning("orchestrator/build-jobs: continuing without DB pool: %s", exc)
            pool = None
        if pool is not None:
            runtime_state.set_pool(pool)
        from ..orchestration import runtime_state as orch_rs

        jobs = await orch_rs.list_jobs_for_user(user["id"], min(max(1, limit), 50))
        return {"success": True, "jobs": jobs}
    except Exception as e:
        logger.exception("orchestrator/build-jobs")
        return {"success": False, "jobs": [], "error": str(e)}


@router.get("/jobs/{job_id}/plan-draft")
async def get_plan_draft(job_id: str, user: dict = Depends(_get_auth())):
    """Return the draft plan for a job in 'planned' state.
    Used by UnifiedWorkspace to show the plan before run-auto is called."""
    try:
        from ..db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            # Try build_plans table first
            row = await conn.fetchrow(
                "SELECT plan_json FROM build_plans WHERE job_id=$1 ORDER BY created_at DESC LIMIT 1",
                job_id
            )
            if row and row["plan_json"]:
                import json as _json
                plan = row["plan_json"] if isinstance(row["plan_json"], dict) else _json.loads(row["plan_json"])
                return {"plan": plan, "job_id": job_id}
            # Fallback: check jobs table
            jrow = await conn.fetchrow("SELECT plan_json FROM jobs WHERE id=$1", job_id)
            if jrow and jrow.get("plan_json"):
                plan = jrow["plan_json"] if isinstance(jrow["plan_json"], dict) else _json.loads(jrow["plan_json"])
                return {"plan": plan, "job_id": job_id}
    except Exception:
        pass
    return {"plan": None, "job_id": job_id}


# ─── Benchmark endpoint (protected, no user session required) ────────────────
BENCHMARK_SECRET = os.environ.get("BENCHMARK_SECRET", "crucibai_benchmark_2026_secret_key")


class BenchmarkRunRequest(BaseModel):
    goal: str
    secret: str


@router.post("/orchestrator/benchmark/run")
async def run_benchmark_job(
    body: BenchmarkRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Protected benchmark endpoint — runs a job without a user session.
    Requires the BENCHMARK_SECRET env var (default: crucibai_benchmark_2026_secret_key).
    """
    if body.secret != BENCHMARK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid benchmark secret")

    try:
        from ..services.job_service import create_job_service
        from ..orchestration import planner as planner_mod
        from ..orchestration import runtime_state
        from ..db_pg import get_pg_pool

        # Synthetic system user for benchmark runs
        benchmark_user = {"id": "system-benchmark-user", "email": "benchmark@crucibai.internal", "role": "admin"}

        # Build a minimal body-like object
        class _BenchmarkBody:
            goal = body.goal
            project_id = "benchmark-" + body.goal[:20].replace(' ', '-').lower().replace('/', '-')
            mode = "guided"
            priority = "normal"
            timeout = 3600

        async def _pool_getter():
            try:
                return await get_pg_pool()
            except Exception:
                return None

        result = await create_job_service(
            body=_BenchmarkBody(),
            user=benchmark_user,
            runtime_state_getter=lambda: runtime_state,
            pool_getter=_pool_getter,
            generate_plan=planner_mod.generate_plan,
        )

        job = result.get("job") or result
        job_id = job.get("id") or job.get("job_id")
        project_id = job.get("project_id")

        (_, _, _, _project_workspace_path) = _get_server_helpers()
        workspace_path = _project_workspace_path(project_id)

        background_tasks.add_task(_background_auto_runner_job, job_id, str(workspace_path))

        return {
            "success": True,
            "job_id": job_id,
            "project_id": project_id,
            "status": "started",
        }
    except Exception as e:
        logger.exception("orchestrator/benchmark/run error")
        raise HTTPException(status_code=500, detail=str(e))
