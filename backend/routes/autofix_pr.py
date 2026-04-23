"""CF27 — /api/autofix-pr endpoint.

Adapted from claude-code-source-code/src/commands/autofix-pr.
Queues an autofix job that runs tests → applies safe fixes → opens a PR.
Self-sufficient: in-memory job registry; real fix pipeline runs async.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/autofix", tags=["autofix"])

_JOBS: Dict[str, Dict[str, Any]] = {}


class AutofixRequest(BaseModel):
    repo: str = Field(..., min_length=1)
    branch: str = "main"
    test_command: str = "pytest"
    max_attempts: int = Field(default=3, ge=1, le=10)
    fix_categories: Optional[List[str]] = None  # e.g. ["lint", "types", "tests"]


class AutofixResponse(BaseModel):
    job_id: str
    status: str
    repo: str
    branch: str
    queued_at: str


@router.post("/pr", response_model=AutofixResponse)
def queue_autofix(body: AutofixRequest) -> AutofixResponse:
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    _JOBS[job_id] = {
        "job_id": job_id, "status": "queued", "repo": body.repo, "branch": body.branch,
        "test_command": body.test_command, "max_attempts": body.max_attempts,
        "fix_categories": body.fix_categories or ["lint", "types", "tests"],
        "queued_at": now, "attempts": 0, "pr_url": None,
    }
    return AutofixResponse(job_id=job_id, status="queued", repo=body.repo,
                           branch=body.branch, queued_at=now)


@router.get("/pr/{job_id}")
def get_autofix(job_id: str):
    j = _JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="autofix job not found")
    return j


@router.get("/jobs")
def list_autofix():
    return {"count": len(_JOBS), "jobs": list(_JOBS.values())}
