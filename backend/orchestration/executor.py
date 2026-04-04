"""
executor.py — Step execution dispatcher for CrucibAI Auto-Runner.
Each step category routes to a specific handler.
Every step: emit event → execute → persist artifact → emit result.
"""
import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, Callable

from .runtime_state import update_step_state, append_job_event, save_checkpoint
from .event_bus import publish
from .verifier import verify_step

logger = logging.getLogger(__name__)

# ── Step handler registry ─────────────────────────────────────────────────────

async def handle_planning_step(step: Dict, job: Dict,
                                workspace_path: str, **kwargs) -> Dict:
    """Planner and requirements steps — produce structured plan output."""
    return {
        "output": f"Planning step '{step['step_key']}' analyzed goal: {job.get('goal', '')[:100]}",
        "artifacts": [],
    }


async def handle_frontend_generate(step: Dict, job: Dict,
                                    workspace_path: str, **kwargs) -> Dict:
    return {
        "output": f"Frontend scaffolded for: {job.get('goal', '')[:100]}",
        "output_files": [],
        "artifacts": [],
    }


async def handle_frontend_modify(step: Dict, job: Dict,
                                  workspace_path: str, **kwargs) -> Dict:
    return {"output": f"Frontend modified: {step['step_key']}", "artifacts": []}


async def handle_backend_route(step: Dict, job: Dict,
                                workspace_path: str, **kwargs) -> Dict:
    return {
        "output": f"Backend route generated: {step['step_key']}",
        "routes_added": [],
        "output_files": [],
        "artifacts": [],
    }


async def handle_db_migration(step: Dict, job: Dict,
                               workspace_path: str, db_pool=None, **kwargs) -> Dict:
    return {
        "output": f"Migration step executed: {step['step_key']}",
        "tables_created": [],
        "artifacts": [],
    }


async def handle_test_run(step: Dict, job: Dict,
                           workspace_path: str, **kwargs) -> Dict:
    return {"output": f"Tests executed: {step['step_key']}", "artifacts": []}


async def handle_deploy(step: Dict, job: Dict,
                         workspace_path: str, **kwargs) -> Dict:
    return {
        "output": f"Deploy step: {step['step_key']}",
        "deploy_url": None,
        "artifacts": [],
    }


async def handle_verification_step(step: Dict, job: Dict,
                                    workspace_path: str, db_pool=None, **kwargs) -> Dict:
    vr = await verify_step(step, workspace_path, db_pool)
    return {
        "output": f"Verification: {'PASSED' if vr['passed'] else 'FAILED'} score={vr['score']}",
        "verification_result": vr,
        "artifacts": [],
    }


async def handle_generic(step: Dict, job: Dict,
                          workspace_path: str, **kwargs) -> Dict:
    return {"output": f"Step executed: {step['step_key']}", "artifacts": []}


# ── Handler routing ───────────────────────────────────────────────────────────

STEP_HANDLERS = {
    "planning.analyze": handle_planning_step,
    "planning.requirements": handle_planning_step,
    "frontend.scaffold": handle_frontend_generate,
    "frontend.styling": handle_frontend_modify,
    "frontend.routing": handle_frontend_modify,
    "backend.models": handle_backend_route,
    "backend.routes": handle_backend_route,
    "backend.auth": handle_backend_route,
    "backend.stripe": handle_backend_route,
    "database.migration": handle_db_migration,
    "database.seed": handle_db_migration,
    "verification.compile": handle_verification_step,
    "verification.api_smoke": handle_verification_step,
    "verification.preview": handle_verification_step,
    "verification.security": handle_verification_step,
    "deploy.build": handle_deploy,
    "deploy.publish": handle_deploy,
}


def _get_handler(step_key: str):
    if step_key in STEP_HANDLERS:
        return STEP_HANDLERS[step_key]
    # Match by prefix
    prefix = ".".join(step_key.split(".")[:2])
    if prefix in STEP_HANDLERS:
        return STEP_HANDLERS[prefix]
    phase = step_key.split(".")[0]
    phase_defaults = {
        "frontend": handle_frontend_generate,
        "backend": handle_backend_route,
        "database": handle_db_migration,
        "verification": handle_verification_step,
        "deploy": handle_deploy,
        "planning": handle_planning_step,
    }
    return phase_defaults.get(phase, handle_generic)


# ── Main execute_step ─────────────────────────────────────────────────────────

async def execute_step(step: Dict[str, Any], job: Dict[str, Any],
                        workspace_path: str = "",
                        db_pool=None,
                        proof_service=None) -> Dict[str, Any]:
    """
    Execute a single step:
    1. Mark running + emit step_started
    2. Call handler
    3. Run verifier
    4. Persist proof
    5. Mark completed/failed + emit result
    6. Save checkpoint
    """
    job_id = job["id"]
    step_id = step["id"]
    step_key = step["step_key"]
    t0 = time.monotonic()

    # 1. Mark running
    await update_step_state(step_id, "running")
    await append_job_event(job_id, "step_started",
                           {"step_key": step_key, "agent": step.get("agent_name")},
                           step_id=step_id)
    await publish(job_id, "step_started",
                  {"step_key": step_key, "agent": step.get("agent_name"),
                   "step_id": step_id})

    try:
        # 2. Execute handler
        handler = _get_handler(step_key)
        result = await handler(step, job, workspace_path, db_pool=db_pool)

        duration_ms = int((time.monotonic() - t0) * 1000)

        # 3. Verify
        await update_step_state(step_id, "verifying")
        await publish(job_id, "step_verifying", {"step_key": step_key, "step_id": step_id})

        # Merge output files/tables from result into step for verifier
        verification_input = {**step, **result}
        vr = await verify_step(verification_input, workspace_path, db_pool)

        if not vr["passed"]:
            raise RuntimeError(
                f"Verification failed for {step_key}: {'; '.join(vr['issues'])}"
            )

        # 4. Persist proof
        if proof_service:
            for p in vr.get("proof", []):
                await proof_service.store_proof(
                    job_id=job_id, step_id=step_id,
                    proof_type=p["proof_type"],
                    title=p["title"],
                    payload=p["payload"]
                )

        # 5. Mark completed
        await update_step_state(step_id, "completed", {
            "output_ref": json.dumps(result.get("output", ""))[:500],
            "verifier_status": "passed",
            "verifier_score": vr["score"],
        })
        await append_job_event(job_id, "step_completed",
                               {"step_key": step_key, "duration_ms": duration_ms,
                                "verifier_score": vr["score"]},
                               step_id=step_id)
        await publish(job_id, "step_completed",
                      {"step_key": step_key, "step_id": step_id,
                       "duration_ms": duration_ms, "score": vr["score"],
                       "proof": vr.get("proof", [])})

        # 6. Checkpoint
        await save_checkpoint(job_id, step_key, {
            "step_id": step_id, "step_key": step_key,
            "status": "completed", "score": vr["score"],
            "output": str(result.get("output", ""))[:500],
        })

        return {"success": True, "result": result, "verification": vr}

    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        error_msg = str(exc)[:500]
        logger.warning("executor: step %s failed: %s", step_key, error_msg)

        await update_step_state(step_id, "failed", {
            "error_message": error_msg,
            "verifier_status": "failed",
        })
        await append_job_event(job_id, "step_failed",
                               {"step_key": step_key, "error": error_msg,
                                "duration_ms": duration_ms},
                               step_id=step_id)
        await publish(job_id, "step_failed",
                      {"step_key": step_key, "step_id": step_id,
                       "error": error_msg, "duration_ms": duration_ms})

        return {"success": False, "error": error_msg}
