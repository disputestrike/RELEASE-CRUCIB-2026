"""CF18 — Phase H closeout: unified preview-loop route.

Composes the three existing Phase H services — preview_session,
operator_runner, ui_feedback_mapper — into a single thread-run workflow so
the Workspace-V3 Preview tab can trigger an end-to-end preview + operator
+ visual-diff loop with one request.

Endpoints
---------
POST /api/runs/{thread_id}/preview-loop
    Body: { url, operator_steps?, take_before_shot?, take_after_shot?,
            diff_threshold?, dry_run? }
    Returns a single JSON envelope containing:
        preview:  opened PreviewSession info
        operator: per-step results from operator_runner.run_flow
        feedback: UiFeedbackReport (verdict + diff_ratio)
        artifacts: references to screenshots/comments recorded during the loop
        status:   overall "pass" | "regression" | "degraded"

GET /api/runs/preview-loop/capabilities
    Discovery: which sub-services are available (useful for the UI to
    conditionally enable the button).

GET /api/runs/{thread_id}/preview-loop/last
    Return the last preview-loop result for a thread (in-memory cache).
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/runs", tags=["preview-loop"])


def _get_auth():
    try:
        from ....server import get_current_user        return get_current_user
    except Exception:
        async def _anon():
            return {"id": "anonymous"}
        return _anon


class OperatorStep(BaseModel):
    action: str = Field(..., description="navigate | screenshot | click | type_text")
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    approval_required: Optional[bool] = False


class PreviewLoopRequest(BaseModel):
    url: str = Field(..., min_length=3)
    operator_steps: Optional[List[OperatorStep]] = None
    take_before_shot: bool = True
    take_after_shot: bool = True
    diff_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
    dry_run: bool = True
    project_id: Optional[str] = None


# in-memory cache of the last result per thread (Phase H is instrumentation,
# durable storage lives in artifacts/screenshots tables already)
_LAST_RESULT: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE = 200


def _trim_cache() -> None:
    if len(_LAST_RESULT) > _MAX_CACHE:
        # drop oldest ~20%
        drop = int(_MAX_CACHE * 0.2)
        for k in list(_LAST_RESULT.keys())[:drop]:
            _LAST_RESULT.pop(k, None)


@router.get("/preview-loop/capabilities")
async def preview_loop_capabilities():
    """Discovery: report which sub-services are importable right now."""
    caps: Dict[str, Any] = {
        "preview_session": False,
        "operator_runner": False,
        "ui_feedback_mapper": False,
    }
    try:
        try:
            from services.preview_session import preview_session_service  # noqa: F401
        except ImportError:
            from ....services.preview_session import preview_session_service  # noqa: F401        caps["preview_session"] = True
    except Exception as exc:
        caps["preview_session_error"] = str(exc)
    try:
        from ....services.operator_runner import operator_runner  # noqa        caps["operator_runner"] = True
    except Exception as exc:
        caps["operator_runner_error"] = str(exc)
    try:
        from ....services.ui_feedback_mapper import ui_feedback_mapper  # noqa        caps["ui_feedback_mapper"] = True
    except Exception as exc:
        caps["ui_feedback_mapper_error"] = str(exc)

    caps["ready"] = all([caps["preview_session"], caps["operator_runner"],
                         caps["ui_feedback_mapper"]])
    return {"status": "ready" if caps["ready"] else "degraded", **caps}


@router.post("/{thread_id}/preview-loop")
async def run_preview_loop(
    thread_id: str,
    body: PreviewLoopRequest,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Compose preview+operator+feedback into one thread-run workflow."""
    run_id = f"pl_{uuid.uuid4().hex[:12]}"
    started = time.time()

    try:
        try:
            from services.preview_session import preview_session_service
            from services.operator_runner import operator_runner
            from services.ui_feedback_mapper import ui_feedback_mapper
        except ImportError:
            from ....services.preview_session import preview_session_service            from ....services.operator_runner import operator_runner            from ....services.ui_feedback_mapper import ui_feedback_mapper    except Exception as exc:
        raise HTTPException(status_code=503,
                            detail=f"preview-loop subservice import failed: {exc}")

    # 1) Open preview session
    session_info: Dict[str, Any] = {}
    try:
        sess = await preview_session_service.open(url=body.url, thread_id=thread_id)
        session_info = {
            "session_id": getattr(sess, "session_id", None),
            "url": getattr(sess, "url", body.url),
        }
    except Exception as exc:
        logger.warning("preview_session.open failed: %s", exc)
        session_info = {"error": str(exc)}

    # 2) Take the "before" screenshot if requested
    before_shot_b64: Optional[str] = None
    if body.take_before_shot:
        try:
            before_shot_b64 = await operator_runner.screenshot(body.url)
        except Exception as exc:
            logger.warning("before screenshot failed: %s", exc)

    # 3) Run operator flow
    default_steps: List[Dict[str, Any]] = [
        {"action": "navigate", "url": body.url},
        {"action": "screenshot", "url": body.url},
    ]
    steps = [s.model_dump() if hasattr(s, "model_dump") else s.dict()
             for s in (body.operator_steps or [])] or default_steps

    operator_results: List[Dict[str, Any]] = []
    try:
        operator_results = await operator_runner.run_flow(
            steps=steps,
            dry_run=body.dry_run,
            thread_id=thread_id,
        )
    except Exception as exc:
        logger.warning("operator_runner.run_flow failed: %s", exc)
        operator_results = [{"action": "_error", "status": "error", "detail": str(exc)}]

    # 4) Take the "after" screenshot if requested
    after_shot_b64: Optional[str] = None
    if body.take_after_shot:
        try:
            after_shot_b64 = await operator_runner.screenshot(body.url)
        except Exception as exc:
            logger.warning("after screenshot failed: %s", exc)

    # 5) Run UI feedback diff
    feedback: Dict[str, Any] = {"verdict": "unknown", "diff_ratio": None}
    try:
        report = await ui_feedback_mapper.diff(
            before_url=body.url if before_shot_b64 else None,
            after_url=body.url if after_shot_b64 else None,
            threshold=body.diff_threshold,
        )
        feedback = {
            "verdict": getattr(report, "verdict", "unknown"),
            "diff_ratio": getattr(report, "diff_ratio", None),
            "threshold": body.diff_threshold,
            "notes": getattr(report, "notes", None),
        }
    except Exception as exc:
        logger.warning("ui_feedback_mapper.diff failed: %s", exc)
        feedback = {"verdict": "degraded", "detail": str(exc)}

    # overall status
    operator_ok = all(
        r.get("status") in (None, "ok", "success", "dry-run")
        for r in operator_results
    )
    verdict = feedback.get("verdict") or "unknown"
    if verdict in ("pass", "identical", "unchanged"):
        overall = "pass" if operator_ok else "regression"
    elif verdict in ("regression", "changed", "fail"):
        overall = "regression"
    else:
        overall = "degraded" if not operator_ok else "pass"

    elapsed = round(time.time() - started, 3)
    result = {
        "run_id": run_id,
        "thread_id": thread_id,
        "status": overall,
        "elapsed_seconds": elapsed,
        "preview": session_info,
        "operator": operator_results,
        "feedback": feedback,
        "artifacts": {
            "before_shot_b64_len": len(before_shot_b64) if before_shot_b64 else 0,
            "after_shot_b64_len": len(after_shot_b64) if after_shot_b64 else 0,
        },
        "user_id": (user or {}).get("id"),
    }

    _LAST_RESULT[thread_id] = result
    _trim_cache()
    return result


@router.get("/{thread_id}/preview-loop/last")
async def get_last_preview_loop(thread_id: str):
    """Return the last cached preview-loop result for a thread."""
    hit = _LAST_RESULT.get(thread_id)
    if hit is None:
        return {"status": "empty", "thread_id": thread_id}
    return hit
