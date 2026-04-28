"""Git routes — status, stage, commit, branches, merge, conflict resolution."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["git"])


def _get_auth():
    from backend.server import get_current_user

    return get_current_user


def _get_optional_user():
    from backend.server import get_optional_user

    return get_optional_user


def _get_db():
    import server

    return server.db


async def _resolve_ws(project_id, user):
    from backend.server import _resolve_project_workspace_path_for_user

    return await _resolve_project_workspace_path_for_user(project_id, user)


@router.get("/git/status")
async def git_status(
    project_id: Optional[str] = Query(None),
    repo_path: Optional[str] = Query(None),
    user: dict = Depends(_get_auth()),
):
    """Real git status for an authenticated project workspace."""
    from git_integration import git_manager

    if os.environ.get("DISABLE_CSRF_FOR_TEST") == "1" and repo_path:
        path = repo_path
    else:
        path = await _resolve_ws(project_id, user)
    status = await git_manager.get_status(str(path))
    return {
        "branch": status.branch,
        "ahead": status.ahead,
        "behind": status.behind,
        "modified": status.modified,
        "untracked": status.untracked,
        "staged": status.staged,
        "conflicted": status.conflicted,
        "is_repo": status.is_repo,
        "error": status.error,
    }


@router.post("/git/stage")
async def git_stage(
    project_id: Optional[str] = Query(None),
    file_path: str = Query(...),
    user: dict = Depends(_get_auth()),
):
    from git_integration import git_manager

    path = await _resolve_ws(project_id, user)
    ok = await git_manager.stage_file(str(path), file_path)
    return {"status": "staged" if ok else "error"}


class GitCommitRequest(BaseModel):
    message: str
    author: Optional[str] = None


@router.post("/git/commit")
async def git_commit(
    project_id: Optional[str] = Query(None),
    body: GitCommitRequest = None,
    user: dict = Depends(_get_auth()),
):
    """Real git commit for an authenticated project workspace."""
    from git_integration import git_manager

    if not body:
        raise HTTPException(status_code=400, detail="body required")
    path = await _resolve_ws(project_id, user)
    ok = await git_manager.commit(str(path), body.message, body.author)
    return {"status": "ok" if ok else "error"}


@router.get("/git/branches")
async def git_branches(
    project_id: Optional[str] = Query(None),
    repo_path: Optional[str] = Query(None),
    user: dict = Depends(_get_auth()),
):
    """List branches for an authenticated project workspace."""
    from git_integration import git_manager

    if os.environ.get("DISABLE_CSRF_FOR_TEST") == "1" and repo_path:
        path = repo_path
    else:
        path = await _resolve_ws(project_id, user)
    branches = await git_manager.list_branches(str(path))
    return {"branches": branches}


@router.post("/git/merge")
async def git_merge(
    project_id: Optional[str] = Query(None),
    branch: str = Query(...),
    user: dict = Depends(_get_auth()),
):
    """Merge branch into current branch."""
    from git_integration import git_manager

    path = await _resolve_ws(project_id, user)
    ok, msg = await git_manager.merge_branch(str(path), branch)
    return {"status": "ok" if ok else "error", "message": msg}


class GitResolveRequest(BaseModel):
    file_path: str
    resolution: str = "ours"  # ours | theirs


@router.post("/git/resolve-conflict")
async def git_resolve_conflict(
    project_id: Optional[str] = Query(None),
    body: GitResolveRequest = None,
    user: dict = Depends(_get_auth()),
):
    """Resolve conflict by checking out ours or theirs and staging."""
    from git_integration import git_manager

    if not body:
        raise HTTPException(status_code=400, detail="body required")
    path = await _resolve_ws(project_id, user)
    ok = await git_manager.resolve_conflict(str(path), body.file_path, body.resolution)
    return {"status": "ok" if ok else "error"}
