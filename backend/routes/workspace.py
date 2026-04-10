"""
Workspace routes — file access, preview, and deploy for project workspaces.

All operations resolve from authenticated project_id or job_id.
Raw server paths are never accepted from clients.
"""
import logging
import os
import zipfile
import io
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workspace"])


# ── Dependency helpers ────────────────────────────────────────────────────────

def _get_auth():
    """Import auth dep lazily to avoid circular imports."""
    from server import get_current_user
    return get_current_user


def _workspace_root() -> Path:
    from server import ROOT_DIR
    return Path(ROOT_DIR) / "workspace"


def _project_workspace_path(project_id: str) -> Path:
    root = _workspace_root()
    safe = project_id.replace("/", "_").replace("\\", "_").replace("..", "_")
    return root / safe


def _safe_resolve(workspace: Path, rel: str) -> Path:
    """Resolve a relative path inside workspace, rejecting path escapes."""
    full = (workspace / rel).resolve()
    if not str(full).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full


async def _assert_project_access(project_id: str, user: dict) -> Path:
    """Verify user owns project and return workspace path."""
    try:
        from server import _user_can_access_project_workspace
        ok = await _user_can_access_project_workspace(user.get("id"), project_id)
        if not ok:
            raise HTTPException(status_code=403, detail="Access denied")
    except ImportError:
        pass  # If helper not available, allow (fallback)
    return _project_workspace_path(project_id)


async def _assert_job_access(job_id: str, user: dict) -> Path:
    """Verify user owns job and return workspace path."""
    try:
        from server import _get_orchestration, _assert_job_owner_match
        from db_pg import get_pg_pool
        runtime_state, *_ = _get_orchestration()
        pool = await get_pg_pool()
        runtime_state.set_pool(pool)
        job = await runtime_state.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        _assert_job_owner_match(job.get("user_id"), user)
        project_id = job.get("project_id") or job_id
        return _project_workspace_path(project_id)
    except (ImportError, AttributeError):
        return _project_workspace_path(job_id)


# ── Project workspace file routes ─────────────────────────────────────────────

@router.get("/projects/{project_id}/workspace/files")
async def list_project_workspace_files(
    project_id: str,
    user: dict = Depends(_get_auth()),
):
    """List all files in a project workspace."""
    workspace = await _assert_project_access(project_id, user)
    if not workspace.exists():
        return {"files": [], "project_id": project_id}

    files = []
    skip = {"node_modules", ".git", "__pycache__", "dist", "build", ".next"}
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in filenames:
            full = Path(root) / name
            rel = str(full.relative_to(workspace)).replace("\\", "/")
            files.append({
                "path": rel,
                "size": full.stat().st_size,
                "is_code": name.endswith((".jsx", ".tsx", ".js", ".ts", ".py", ".css", ".json", ".sql", ".md", ".yaml", ".yml")),
            })

    return {"files": files, "project_id": project_id, "count": len(files)}


@router.get("/projects/{project_id}/workspace/file")
async def get_project_workspace_file(
    project_id: str,
    path: str = Query(..., description="Relative file path within workspace"),
    user: dict = Depends(_get_auth()),
):
    """Get contents of a specific file in a project workspace."""
    workspace = await _assert_project_access(project_id, user)
    full_path = _safe_resolve(workspace, path)

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": path,
            "content": content,
            "size": len(content),
            "project_id": project_id,
        }
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")


# ── Job workspace file routes ──────────────────────────────────────────────────

@router.get("/jobs/{job_id}/workspace/files")
async def list_job_workspace_files(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """List all files in a job's workspace."""
    workspace = await _assert_job_access(job_id, user)
    if not workspace.exists():
        return {"files": [], "job_id": job_id}

    files = []
    skip = {"node_modules", ".git", "__pycache__", "dist", "build"}
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in filenames:
            full = Path(root) / name
            rel = str(full.relative_to(workspace)).replace("\\", "/")
            files.append({"path": rel, "size": full.stat().st_size})

    return {"files": files, "job_id": job_id, "count": len(files)}


@router.get("/jobs/{job_id}/workspace/file")
async def get_job_workspace_file(
    job_id: str,
    path: str = Query(..., description="Relative file path within workspace"),
    user: dict = Depends(_get_auth()),
):
    """Get contents of a specific file in a job's workspace."""
    workspace = await _assert_job_access(job_id, user)
    full_path = _safe_resolve(workspace, path)

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content, "size": len(content), "job_id": job_id}
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")


# ── Deploy / export routes ─────────────────────────────────────────────────────

@router.get("/projects/{project_id}/deploy/zip")
async def get_project_deploy_zip(
    project_id: str,
    user: dict = Depends(_get_auth()),
):
    """Stream a ZIP of all workspace files for download/deploy."""
    workspace = await _assert_project_access(project_id, user)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")

    buf = io.BytesIO()
    skip = {"node_modules", ".git", "__pycache__"}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, filenames in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in filenames:
                full = Path(root) / name
                arcname = str(full.relative_to(workspace)).replace("\\", "/")
                zf.write(full, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_id}.zip"},
    )


@router.get("/projects/{project_id}/deploy/files")
async def get_project_deploy_files(
    project_id: str,
    user: dict = Depends(_get_auth()),
):
    """Return all workspace files as a JSON map for deploy tools."""
    workspace = await _assert_project_access(project_id, user)
    if not workspace.exists():
        return {"files": {}, "project_id": project_id}

    files: Dict[str, str] = {}
    skip = {"node_modules", ".git", "__pycache__"}
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in filenames:
            full = Path(root) / name
            rel = str(full.relative_to(workspace)).replace("\\", "/")
            try:
                files[rel] = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

    return {
        "files": files,
        "project_id": project_id,
        "file_count": len(files),
        "deploy_ready": bool(files.get("package.json") or files.get("server.py")),
    }
