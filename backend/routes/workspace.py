"""
Workspace routes — file access, preview, and deploy for project workspaces.

All operations resolve from authenticated project_id or job_id.
Raw server paths are never accepted from clients.
"""

import io
import logging
import mimetypes
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workspace"])


# ── Dependency helpers ────────────────────────────────────────────────────────


def _get_auth():
    """Import auth dep lazily to avoid circular imports."""
    from server import get_current_user

    return get_current_user


def _workspace_root() -> Path:
    try:
        from server import WORKSPACE_ROOT
        return Path(WORKSPACE_ROOT) / "projects"
    except ImportError:
        from server import ROOT_DIR
        return Path(ROOT_DIR) / "workspace"


def _project_workspace_path(project_id: str) -> Path:
    try:
        from server import _project_workspace_path as _srv_wp
        return _srv_wp(project_id)
    except (ImportError, Exception):
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
        from db_pg import get_pg_pool
        from server import _assert_job_owner_match, _get_orchestration

        runtime_state = None
        try:
            orchestration_obj = _get_orchestration()
            if isinstance(orchestration_obj, tuple):
                runtime_state = orchestration_obj[0] if orchestration_obj else None
            elif orchestration_obj is not None:
                runtime_state = orchestration_obj
        except Exception:
            runtime_state = None

        if runtime_state is None:
            from orchestration import runtime_state as _runtime_state

            runtime_state = _runtime_state

        try:
            pool = await get_pg_pool()
        except Exception as exc:
            logger.warning("workspace: continuing without DB pool for job %s: %s", job_id, exc)
            pool = None
        if pool is not None:
            runtime_state.set_pool(pool)
        job = await runtime_state.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        _assert_job_owner_match(job.get("user_id"), user)
        project_id = job.get("project_id") or job_id
        return _project_workspace_path(project_id)
    except (ImportError, AttributeError):
        return _project_workspace_path(job_id)


def _collect_job_workspace_files(workspace: Path) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    if not workspace.exists():
        return files
    skip = {"node_modules", ".git", "__pycache__", "dist", "build"}
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in filenames:
            full = Path(root) / name
            rel = str(full.relative_to(workspace)).replace("\\", "/")
            files.append({"path": rel, "size": full.stat().st_size})
    files.sort(key=lambda x: x["path"])
    return files


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
            files.append(
                {
                    "path": rel,
                    "size": full.stat().st_size,
                    "is_code": name.endswith(
                        (
                            ".jsx",
                            ".tsx",
                            ".js",
                            ".ts",
                            ".py",
                            ".css",
                            ".json",
                            ".sql",
                            ".md",
                            ".yaml",
                            ".yml",
                        )
                    ),
                }
            )

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
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    user: dict = Depends(_get_auth()),
):
    """List files in a job's workspace (paginated; same shape as orchestration job workspace tests)."""
    workspace = await _assert_job_access(job_id, user)
    all_files = _collect_job_workspace_files(workspace) if workspace.exists() else []
    total = len(all_files)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 1000))
    page = all_files[off : off + lim]
    has_more = off + lim < total
    return {
        "files": page,
        "job_id": job_id,
        "count": total,
        "total_count": total,
        "offset": off,
        "limit": lim,
        "has_more": has_more,
        "next_offset": off + lim if has_more else None,
    }


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
        return {
            "path": path,
            "content": content,
            "size": len(content),
            "job_id": job_id,
        }
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")


@router.get("/jobs/{job_id}/workspace/file/raw")
async def get_job_workspace_file_raw(
    job_id: str,
    path: str = Query(..., description="Relative file path within workspace"),
    user: dict = Depends(_get_auth()),
):
    """Stream raw bytes for a file in the job workspace (images, binaries)."""
    workspace = await _assert_job_access(job_id, user)
    full_path = _safe_resolve(workspace, path)
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media = mimetypes.guess_type(full_path.name)[0] or "application/octet-stream"
    return FileResponse(path=str(full_path), media_type=media, filename=full_path.name)


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


@router.get("/jobs/{job_id}/workspace/download")
async def download_job_workspace_zip(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """
    Download the complete job workspace as a ZIP file.
    This is the proof/handoff bundle — everything the AI built.
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    workspace = await _assert_job_access(job_id, user)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace not found or empty")

    # Build ZIP in memory
    buf = io.BytesIO()
    skip_dirs = {"node_modules", ".git", "__pycache__", ".pytest_cache"}
    skip_exts = {".pyc", ".pyo"}
    file_count = 0

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                if any(fname.endswith(ext) for ext in skip_exts):
                    continue
                full = Path(root) / fname
                rel = str(full.relative_to(workspace)).replace("\\", "/")
                try:
                    zf.write(full, rel)
                    file_count += 1
                except Exception:
                    pass

    if file_count == 0:
        raise HTTPException(status_code=404, detail="No files in workspace")

    buf.seek(0)
    filename = f"crucibai-build-{job_id[:8]}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
