"""CF27 — /api/commit-push-pr endpoint.

Adapted from claude-code-source-code/src/commands/commit-push-pr.ts.
One-shot: stage + commit + push + open PR. The heavy lifting runs in a
background worker; this endpoint records the intent and hands back a job id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/git", tags=["git"])

_JOBS: Dict[str, Dict[str, Any]] = {}


class CommitPushPRRequest(BaseModel):
    repo: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    base_branch: str = "main"
    commit_message: str = Field(..., min_length=1)
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    files: Optional[List[str]] = None  # explicit staging list; None = all


class CommitPushPRResponse(BaseModel):
    job_id: str
    status: str
    repo: str
    branch: str
    queued_at: str


@router.post("/commit-push-pr", response_model=CommitPushPRResponse)
def queue_commit_push_pr(body: CommitPushPRRequest) -> CommitPushPRResponse:
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    _JOBS[job_id] = {
        "job_id": job_id, "status": "queued",
        "repo": body.repo, "branch": body.branch, "base_branch": body.base_branch,
        "commit_message": body.commit_message,
        "pr_title": body.pr_title or body.commit_message.splitlines()[0][:72],
        "pr_body": body.pr_body or body.commit_message,
        "files": body.files,
        "queued_at": now,
        "commit_sha": None, "pr_url": None,
    }
    return CommitPushPRResponse(job_id=job_id, status="queued", repo=body.repo,
                                branch=body.branch, queued_at=now)


@router.get("/commit-push-pr/{job_id}")
def get_job(job_id: str):
    j = _JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="job not found")
    return j
