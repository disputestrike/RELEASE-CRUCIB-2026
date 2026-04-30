"""CF26 — Mobile build API route.

POST /api/mobile/build — queues a mobile build job.
Returns a stub job_id; real build pipeline runs out-of-process.
Self-sufficient: no database writes, no external deps.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# In-memory job registry (resets on process restart; durable backend lives in
# backend/services/mobile/ which will be wired later)
_JOBS: Dict[str, Dict[str, Any]] = {}


def _get_auth() -> Optional[Dict[str, Any]]:
    """Optional auth — falls back to anonymous for local/dev."""
    try:
        from ....routes.auth import get_current_user  # type: ignore        return None  # caller wires via Depends below when available
    except Exception:
        return None


class MobileBuildRequest(BaseModel):
    platform: str = Field(..., pattern="^(ios|android)$")
    project_id: str
    target: Optional[str] = None  # e.g. "debug" | "release"


class MobileBuildResponse(BaseModel):
    job_id: str
    status: str
    platform: str
    project_id: str
    queued_at: str


@router.post("/build", response_model=MobileBuildResponse)
def queue_mobile_build(req: MobileBuildRequest) -> MobileBuildResponse:
    if req.platform not in ("ios", "android"):
        raise HTTPException(status_code=400, detail="platform must be ios or android")
    job_id = uuid.uuid4().hex
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "job_id": job_id,
        "status": "queued",
        "platform": req.platform,
        "project_id": req.project_id,
        "target": req.target or "debug",
        "queued_at": now_iso,
    }
    _JOBS[job_id] = record
    logger.info("mobile_build.queued", extra={"job_id": job_id, "platform": req.platform})
    return MobileBuildResponse(**{k: record[k] for k in ("job_id", "status", "platform", "project_id", "queued_at")})


@router.get("/build/{job_id}")
def get_mobile_build(job_id: str):
    rec = _JOBS.get(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="job not found")
    return rec


@router.get("/jobs")
def list_mobile_jobs():
    return {"count": len(_JOBS), "jobs": list(_JOBS.values())}
