"""
Worktree routes — filesystem isolation for parallel spawn agents.
Each spawned agent gets its own isolated directory.
Git worktree-style isolation without requiring git.
"""
import os
import shutil
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

WORKTREE_BASE = "/tmp/crucibai_worktrees"
os.makedirs(WORKTREE_BASE, exist_ok=True)


class WorktreeCreateRequest(BaseModel):
    id: str
    base_files: dict = {}  # path -> content for initial state


class WorktreeMergeRequest(BaseModel):
    id: str
    target_job_id: str = ""


class WorktreeWriteRequest(BaseModel):
    id: str
    path: str
    content: str


class WorktreeDeleteRequest(BaseModel):
    id: str


@router.post("/api/worktrees/create")
async def create_worktree(req: WorktreeCreateRequest):
    """Create isolated workspace for a spawn agent."""
    path = os.path.join(WORKTREE_BASE, req.id)
    if os.path.exists(path):
        # Idempotent — return existing
        return {"path": path, "created": False}
    os.makedirs(path)
    # Seed with base files
    for file_path, content in req.base_files.items():
        full = os.path.join(path, file_path.lstrip("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        try:
            with open(full, 'w') as f:
                f.write(content)
        except Exception:
            pass
    logger.info("worktree created: %s", req.id)
    return {"path": path, "created": True, "fileCount": len(req.base_files)}


@router.post("/api/worktrees/write")
async def write_to_worktree(req: WorktreeWriteRequest):
    """Write a file into a worktree layer."""
    path = os.path.join(WORKTREE_BASE, req.id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Worktree not found")
    full = os.path.join(path, req.path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as f:
        f.write(req.content)
    return {"written": req.path}


@router.get("/api/worktrees/{worktree_id}/files")
async def list_worktree_files(worktree_id: str):
    """List files in a worktree."""
    path = os.path.join(WORKTREE_BASE, worktree_id)
    if not os.path.exists(path):
        return {"files": []}
    files = []
    for root, dirs, filenames in os.walk(path):
        for fname in filenames:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, path).replace("\\", "/")
            files.append({"path": rel, "size": os.path.getsize(full)})
    return {"files": files, "count": len(files)}


@router.post("/api/worktrees/merge")
async def merge_worktree(req: WorktreeMergeRequest):
    """
    Copy files from worktree back to main job workspace.
    In production this would do a 3-way merge; here we copy-on-top.
    """
    src = os.path.join(WORKTREE_BASE, req.id)
    if not os.path.exists(src):
        raise HTTPException(status_code=404, detail="Worktree not found")
    
    merged_files = []
    conflicts = []
    
    if req.target_job_id:
        try:
            from backend.server import WORKSPACE_ROOT
            dst = os.path.join(str(WORKSPACE_ROOT), req.target_job_id)
            os.makedirs(dst, exist_ok=True)
            for root, dirs, filenames in os.walk(src):
                for fname in filenames:
                    full_src = os.path.join(root, fname)
                    rel = os.path.relpath(full_src, src)
                    full_dst = os.path.join(dst, rel)
                    if os.path.exists(full_dst):
                        conflicts.append(rel.replace("\\", "/"))
                    os.makedirs(os.path.dirname(full_dst), exist_ok=True)
                    shutil.copy2(full_src, full_dst)
                    merged_files.append(rel.replace("\\", "/"))
        except Exception as e:
            logger.warning("worktree merge: %s", e)

    return {
        "status": "merged",
        "mergedFiles": merged_files,
        "conflicts": conflicts,
        "worktreeId": req.id,
    }


@router.post("/api/worktrees/delete")
async def delete_worktree(req: WorktreeDeleteRequest):
    """Clean up a worktree after merge or failure."""
    path = os.path.join(WORKTREE_BASE, req.id)
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    return {"status": "deleted", "id": req.id}


@router.get("/api/worktrees")
async def list_worktrees():
    """List all active worktrees."""
    if not os.path.exists(WORKTREE_BASE):
        return {"worktrees": []}
    items = []
    for name in os.listdir(WORKTREE_BASE):
        p = os.path.join(WORKTREE_BASE, name)
        if os.path.isdir(p):
            items.append({
                "id": name,
                "path": p,
                "fileCount": sum(len(f) for _, _, f in os.walk(p)),
            })
    return {"worktrees": items}
