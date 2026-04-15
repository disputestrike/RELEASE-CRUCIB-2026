"""Files routes — workspace file tree and content."""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
router = APIRouter()

def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous"}
        return noop


@router.get("/api/builds/{job_id}/files")
async def get_files(job_id: str, user: dict = Depends(_get_auth())):
    """Return file tree for a job workspace."""
    try:
        from server import WORKSPACE_ROOT
        workspace = Path(WORKSPACE_ROOT) / job_id
    except Exception:
        workspace = Path(f"/tmp/workspaces/{job_id}")

    if not workspace.exists():
        return []

    skip = {"node_modules", ".git", "__pycache__", "dist", "build", ".next"}

    def build_tree(path: Path) -> dict:
        node = {"name": path.name, "path": str(path.relative_to(workspace)).replace("\\", "/"),
                "type": "directory" if path.is_dir() else "file"}
        if path.is_dir():
            children = []
            for child in sorted(path.iterdir()):
                if child.name not in skip:
                    children.append(build_tree(child))
            node["children"] = children
        else:
            node["size"] = path.stat().st_size
            ext = path.suffix.lstrip(".")
            node["language"] = ext or "plaintext"
        return node

    try:
        root = build_tree(workspace)
        return root.get("children", [])
    except Exception:
        return []


@router.get("/api/builds/{job_id}/file")
async def get_file_content(
    job_id: str,
    path: str = Query(...),
    user: dict = Depends(_get_auth()),
):
    """Return content of a specific file."""
    try:
        from server import WORKSPACE_ROOT
        workspace = Path(WORKSPACE_ROOT) / job_id
    except Exception:
        workspace = Path(f"/tmp/workspaces/{job_id}")

    # Security: prevent path traversal
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
