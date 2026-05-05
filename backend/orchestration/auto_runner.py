"""Single-runtime job runner for CrucibAI.

The old multi-agent DAG executor is intentionally gone from this entry point.
Every build now enters the supplied-code style tool runtime and all panes read
from the same persisted job/events/workspace contract.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.proof import proof_service

from .event_bus import publish
from .runtime_state import (
    append_job_event,
    clear_steps,
    get_job,
    get_steps,
    update_job_state,
    update_step_state,
)

logger = logging.getLogger(__name__)


def _skip_duplicate_final_preview(steps: List[Dict[str, Any]]) -> bool:
    """Compatibility hook retained for older tests; production never skips proof."""
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
    """Return whether the exact preview route has a mountable HTML entry."""
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


async def _persist_preview_gate_proof_rows(job_id: str, pv: Dict[str, Any]) -> None:
    """Store preview-gate proof rows for failed runs."""
    for item in pv.get("proof") or []:
        if not isinstance(item, dict):
            continue
        try:
            await proof_service.store_proof(
                job_id,
                "preview_gate",
                str(item.get("proof_type") or "verification")[:64],
                str(item.get("title") or "preview_gate")[:500],
                item.get("payload") if isinstance(item.get("payload"), dict) else {},
            )
        except Exception:
            logger.exception("store_proof preview item failed job=%s", job_id)


async def prepare_failed_job_for_rerun(job_id: str) -> int:
    """Prepare a job for another runtime pass without reviving legacy steps."""
    job = await get_job(job_id)
    if not job:
        return 0

    steps = await get_steps(job_id)
    reset_count = 0
    legacy_count = 0
    for step in steps:
        key = str(step.get("step_key") or "").lower()
        agent = str(step.get("agent_name") or "").lower()
        if key.startswith("agents.") or agent.startswith("agents."):
            legacy_count += 1
            continue
        if step.get("status") in {"running", "failed", "blocked", "retrying", "verifying"}:
            await update_step_state(step["id"], "pending")
            reset_count += 1

    if legacy_count:
        await clear_steps(job_id, reason="single_runtime_resume")

    await update_job_state(
        job_id,
        "running",
        {
            "current_phase": "runtime_resume",
            "engine": "single_tool_runtime",
            "resume_requested": True,
        },
    )
    await append_job_event(
        job_id,
        "runtime_resume_prepared",
        {
            "reset_steps": reset_count,
            "removed_legacy_steps": legacy_count,
        },
    )
    try:
        await publish(
            job_id,
            "runtime_resume_prepared",
            {"reset_steps": reset_count, "removed_legacy_steps": legacy_count},
        )
    except Exception:
        logger.debug("runtime resume publish skipped", exc_info=True)
    return reset_count + legacy_count


async def run_job_to_completion(
    job_id: str,
    workspace_path: str = "",
    db_pool=None,
) -> Dict[str, Any]:
    """Run one job through the supplied-code style runtime only."""
    from .pipeline_orchestrator import run_pipeline_job

    job = await get_job(job_id)
    if not job:
        return {"success": False, "status": "failed", "error": "Job not found"}

    if db_pool:
        try:
            proof_service.set_pool(db_pool)
        except Exception:
            logger.debug("proof pool setup skipped", exc_info=True)

    await clear_steps(job_id, reason="single_tool_runtime")
    await append_job_event(
        job_id,
        "runtime_backend_selected",
        {"engine": "single_tool_runtime", "legacy_job_steps": False},
    )
    await publish(
        job_id,
        "runtime_backend_selected",
        {"engine": "single_tool_runtime", "legacy_job_steps": False},
    )

    result = await run_pipeline_job(
        job_id=job_id,
        workspace_path=workspace_path or "",
        goal=(job.get("goal") or "").strip(),
        db_pool=db_pool,
        proof_service=proof_service,
    )
    status = str((result or {}).get("status") or "").lower()
    return {
        "success": status in {"completed", "success"},
        **(result or {}),
    }


async def resume_job(
    job_id: str,
    workspace_path: str = "",
    db_pool=None,
) -> Dict[str, Any]:
    """Resume by starting a new runtime pass against the same workspace."""
    job = await get_job(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}
    await prepare_failed_job_for_rerun(job_id)
    await publish(job_id, "job_resumed", {"job_id": job_id})
    return await run_job_to_completion(job_id, workspace_path, db_pool)
