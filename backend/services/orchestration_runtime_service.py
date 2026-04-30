from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.domain.agent_state import AGENT_STATUS_COMPLETED, AGENT_STATUS_RUNNING, AGENT_STATUS_SKIPPED, normalize_agent_status, assert_agent_transition
from backend.domain.run_state import RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_RUNNING, assert_run_transition


async def set_project_run_status_service(*, db: Any, project_id: str, current_status: Optional[str], next_status: str, extra_fields: Optional[Dict[str, Any]] = None) -> str:
    assert_run_transition(current_status, next_status)
    payload = {"status": next_status}
    if extra_fields:
        payload.update(extra_fields)
    await db.projects.update_one({"id": project_id}, {"$set": payload})
    return next_status


async def restore_checkpoint_results_service(*, db: Any, project_id: str, emit_build_event: Callable[..., Any], logger: Any) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    try:
        checkpoint_cursor = db.agent_status.find({"project_id": project_id})
        checkpoint_count = 0
        async for row in checkpoint_cursor:
            doc = row.get("doc", {})
            agent_nm = row.get("agent_name") or doc.get("agent_name", "")
            status = doc.get("status", "")
            output = doc.get("output", "")
            if agent_nm and status in ("complete", "completed", "failed_with_fallback") and output:
                results[agent_nm] = {
                    "output": output,
                    "result": output,
                    "status": status,
                    "from_checkpoint": True,
                }
                checkpoint_count += 1
        if checkpoint_count > 0:
            logger.info(
                "Checkpoint recovery: %s agents reloaded, skipping re-execution",
                checkpoint_count,
            )
            emit_build_event(
                project_id,
                "checkpoint_restored",
                count=checkpoint_count,
                message=f"Resuming from checkpoint: {checkpoint_count} agents already complete",
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Checkpoint load skipped: %s", exc)
    return results


async def mark_phase_started_service(*, db: Any, project_id: str, phase_idx: int, phases: List[List[str]], agent_names: List[str], total_used: int, emit_build_event: Callable[..., Any]) -> int:
    emit_build_event(
        project_id,
        "phase_started",
        phase=phase_idx,
        agents=agent_names,
        message=f"Phase {phase_idx + 1}: {', '.join(agent_names)}",
    )
    progress_pct = int((phase_idx + 1) / max(len(phases), 1) * 100)
    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "current_phase": phase_idx,
                "current_agent": ",".join(agent_names),
                "progress_percent": progress_pct,
                "tokens_used": total_used,
            }
        },
    )
    return progress_pct


async def mark_agents_started_service(*, db: Any, project_id: str, agent_names: List[str], results: Dict[str, Dict[str, Any]], emit_build_event: Callable[..., Any]) -> None:
    for agent_name in agent_names:
        if agent_name in results and results[agent_name].get("from_checkpoint"):
            emit_build_event(
                project_id,
                "agent_skipped",
                agent=agent_name,
                message=f"{agent_name} skipped (checkpoint)",
            )
            continue
        emit_build_event(
            project_id,
            "agent_started",
            agent=agent_name,
            message=f"{agent_name} started",
        )
        assert_agent_transition(None, AGENT_STATUS_RUNNING)
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": agent_name},
            {
                "$set": {
                    "project_id": project_id,
                    "agent_name": agent_name,
                    "status": AGENT_STATUS_RUNNING,
                    "progress": 0,
                    "tokens_used": 0,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "agent": agent_name,
                "message": f"Starting {agent_name}...",
                "level": "info",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )


async def execute_phase_service(
    *,
    agent_names: List[str],
    timeout_sec: int,
    runner: Callable[[str], Awaitable[Dict[str, Any]]],
) -> List[Any]:
    async def run_one(name: str):
        return await asyncio.wait_for(runner(name), timeout=timeout_sec + 30)

    tasks = [run_one(name) for name in agent_names]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def process_phase_results_service(
    *,
    db: Any,
    project_id: str,
    user_id: str,
    agent_names: List[str],
    phase_results: List[Any],
    results: Dict[str, Dict[str, Any]],
    total_used: int,
    get_criticality: Callable[[str], str],
    generate_fallback: Callable[[str], str],
    coerce_text_output: Callable[..., str],
    emit_build_event: Callable[..., Any],
) -> Dict[str, Any]:
    phase_fail_count = 0
    for name, r in zip(agent_names, phase_results):
        if isinstance(r, Exception):
            phase_fail_count += 1
            crit = get_criticality(name)
            fallback = generate_fallback(name)
            if crit == "critical":
                results[name] = {
                    "output": fallback,
                    "result": fallback,
                    "status": "failed_with_fallback",
                    "reason": str(r),
                }
            else:
                results[name] = {
                    "output": fallback,
                    "result": fallback,
                    "status": "failed_with_fallback",
                }
        else:
            results[name] = r
            total_used += r.get("tokens_used", 0)
            if (r.get("status") or "").lower() in ("skipped", "failed", "failed_with_fallback"):
                phase_fail_count += 1
        final_agent_status = normalize_agent_status(results[name].get("status", "") or AGENT_STATUS_COMPLETED)
        assert_agent_transition(AGENT_STATUS_RUNNING, final_agent_status)
        emit_build_event(
            project_id,
            "agent_completed",
            agent=name,
            tokens=results[name].get("tokens_used", 0),
            status=final_agent_status,
            message=f"{name} completed",
        )
        out_snippet = coerce_text_output(
            results[name].get("output") or results[name].get("result") or "",
            limit=200,
        )
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": name},
            {
                "$set": {
                    "status": final_agent_status,
                    "progress": 100,
                    "tokens_used": results[name].get("tokens_used", 0),
                }
            },
        )
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "agent": name,
                "message": f"{name} completed. Output: {out_snippet}...",
                "level": "success",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await db.token_usage.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "user_id": user_id,
                "agent": name,
                "tokens": results[name].get("tokens_used", 0),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return {"phase_fail_count": phase_fail_count, "total_used": total_used, "results": results}


async def finalize_project_run_status_service(*, db: Any, project_id: str, current_status: Optional[str], success: bool, extra_fields: Optional[Dict[str, Any]] = None) -> str:
    next_status = RUN_STATUS_COMPLETED if success else RUN_STATUS_FAILED
    fields = {"completed_at": datetime.now(timezone.utc).isoformat()}
    if extra_fields:
        fields.update(extra_fields)
    return await set_project_run_status_service(
        db=db,
        project_id=project_id,
        current_status=current_status,
        next_status=next_status,
        extra_fields=fields,
    )
