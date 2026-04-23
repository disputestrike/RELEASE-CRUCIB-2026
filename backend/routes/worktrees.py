"""
Isolated worktree directories for parallel sub-agent filesystem experiments.
Paths are always scoped under the authenticated user's WORKSPACE_ROOT/_worktrees/<user_id>/.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/worktrees", tags=["worktrees"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _user_wt_root(user: dict) -> Path:
    from ..project_state import WORKSPACE_ROOT

    uid = str(user.get("id") or "guest")
    base = (WORKSPACE_ROOT / "_worktrees" / uid).resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_id(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (raw or "").strip())[:160]
    return s or "worktree"


class WorktreeCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=160)


class WorktreeMergeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., min_length=1, max_length=160)
    job_id: str = Field(..., min_length=4, max_length=120, alias="jobId")


class WorktreeDeleteRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=160)


@router.post("/create")
async def create_worktree(req: WorktreeCreateRequest, user: dict = Depends(_get_auth())):
    wid = _safe_id(req.id)
    base = _user_wt_root(user)
    path = (base / wid).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid worktree id") from exc
    if path.exists():
        raise HTTPException(status_code=400, detail="Worktree already exists")
    path.mkdir(parents=True, exist_ok=False)
    logger.info("worktree created user=%s id=%s", user.get("id"), wid)
    return {"path": str(path), "id": wid}


@router.post("/merge")
async def merge_worktree(req: WorktreeMergeRequest, user: dict = Depends(_get_auth())):
    """Copy all files from the worktree into the job's canonical workspace directory."""
    from ..routes.workspace import _assert_job_access

    wid = _safe_id(req.id)
    base = _user_wt_root(user)
    src = (base / wid).resolve()
    try:
        src.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid worktree id") from exc
    if not src.is_dir():
        raise HTTPException(status_code=404, detail="Worktree not found")

    dst = await _assert_job_access(req.job_id, user)
    dst.mkdir(parents=True, exist_ok=True)

    copied = 0
    for root, _dirs, files in os.walk(src):
        for fname in files:
            sf = Path(root) / fname
            rel = sf.relative_to(src)
            df = dst / rel
            df.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sf, df)
            copied += 1

    logger.info("worktree merged user=%s id=%s job=%s files=%d", user.get("id"), wid, req.job_id, copied)
    return {"status": "merged", "files_copied": copied, "destination": str(dst)}


@router.post("/delete")
async def delete_worktree(req: WorktreeDeleteRequest, user: dict = Depends(_get_auth())):
    wid = _safe_id(req.id)
    base = _user_wt_root(user)
    path = (base / wid).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid worktree id") from exc
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    return {"status": "deleted", "id": wid}
