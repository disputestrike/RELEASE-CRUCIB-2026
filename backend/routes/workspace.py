"""
Workspace routes — file access, preview, and deploy for project workspaces.

All operations resolve from authenticated project_id or job_id.
Raw server paths are never accepted from clients.
"""

import io
import hashlib
import logging
import mimetypes
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workspace"])


class VisualEditRequest(BaseModel):
    file_path: str
    find_text: str
    replace_text: str = ""


# ── Dependency helpers ────────────────────────────────────────────────────────


def _get_auth():
    """Import auth dep lazily to avoid circular imports."""
    from ..deps import get_current_user

    return get_current_user


def _workspace_root() -> Path:
    from ..services.workspace_resolver import workspace_resolver

    return workspace_resolver.workspace_root() / "projects"


def _project_workspace_path(project_id: str) -> Path:
    from ..services.workspace_resolver import workspace_resolver

    return workspace_resolver.project_workspace_path(project_id)


def _safe_resolve(workspace: Path, rel: str) -> Path:
    """Resolve a relative path inside workspace, rejecting path escapes."""
    full = (workspace / rel).resolve()
    if not str(full).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full


async def _assert_project_access(project_id: str, user: dict) -> Path:
    """Verify user owns project and return workspace path."""
    try:
        from ..server import _user_can_access_project_workspace

        ok = await _user_can_access_project_workspace(user.get("id"), project_id)
        if not ok:
            raise HTTPException(status_code=403, detail="Access denied")
    except ImportError:
        pass  # If helper not available, allow (fallback)
    return _project_workspace_path(project_id)


async def _assert_job_access(job_id: str, user: dict) -> Path:
    """Verify user owns job and return workspace path."""
    try:
        from ..db_pg import get_pg_pool
        from ..server import _assert_job_owner_match
        from ..orchestration import runtime_state as _runtime_state

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


HEAVY_WORKSPACE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
}
PREVIEW_ARTIFACT_DIRS = {"dist", "build", "out", "public"}
INTERNAL_WORKSPACE_DIRS = {"META", "outputs", ".tmp"}
CODE_FILE_EXTS = {
    ".jsx",
    ".tsx",
    ".js",
    ".ts",
    ".py",
    ".css",
    ".html",
    ".json",
    ".sql",
    ".md",
    ".yaml",
    ".yml",
}
PREVIEW_ARTIFACT_EXTS = {
    ".html",
    ".js",
    ".mjs",
    ".css",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
}


def _workspace_candidates(primary: Path, job_id: str = "") -> List[Path]:
    """Return plausible workspace roots for a job without trusting client paths.

    Runtime task state historically lives under ``WORKSPACE_ROOT/{project_id}``,
    while app files for preview live under ``WORKSPACE_ROOT/projects/{project_id}``.
    Listing/reading must tolerate both so a completed build cannot show an empty
    file room just because one surface resolved a different workspace root.
    """
    from ..services.workspace_resolver import workspace_resolver

    return workspace_resolver.candidates_for(primary, job_id)


def _file_kind(rel: str, full: Path) -> str:
    top = rel.split("/", 1)[0]
    if top in PREVIEW_ARTIFACT_DIRS:
        return "preview_artifact"
    if top in INTERNAL_WORKSPACE_DIRS:
        return "internal"
    if full.suffix.lower() in CODE_FILE_EXTS:
        return "source"
    return "asset"


def _collect_workspace_files_from_root(workspace: Path) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    if not workspace.exists() or not workspace.is_dir():
        return files
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = [
            d
            for d in dirs
            if d not in HEAVY_WORKSPACE_DIRS and not d.startswith(".tmp")
        ]
        for name in filenames:
            full = Path(root) / name
            try:
                rel = str(full.relative_to(workspace)).replace("\\", "/")
                stat = full.stat()
            except OSError:
                continue
            kind = _file_kind(rel, full)
            if kind == "preview_artifact" and full.suffix.lower() not in PREVIEW_ARTIFACT_EXTS:
                continue
            files.append(
                {
                    "path": rel,
                    "size": stat.st_size,
                    "kind": kind,
                    "is_code": full.suffix.lower() in CODE_FILE_EXTS,
                    "is_preview_artifact": kind == "preview_artifact",
                }
            )
    return files


def _collect_job_workspace_files(workspace: Path, job_id: str = "") -> List[Dict[str, Any]]:
    by_path: Dict[str, Dict[str, Any]] = {}
    for candidate in _workspace_candidates(workspace, job_id):
        for row in _collect_workspace_files_from_root(candidate):
            path = row.get("path")
            if not path:
                continue
            existing = by_path.get(path)
            if existing is None:
                by_path[path] = row
                continue
            # Prefer source over preview artifacts over internal metadata when
            # the same relative path exists in multiple compatible roots.
            rank = {"source": 0, "asset": 1, "preview_artifact": 2, "internal": 3}
            if rank.get(row.get("kind"), 9) < rank.get(existing.get("kind"), 9):
                by_path[path] = row

    product_files = [
        row
        for row in by_path.values()
        if row.get("kind") not in {"internal"}
    ]
    internal_files = [
        row
        for row in by_path.values()
        if row.get("kind") == "internal"
    ]
    files = product_files or internal_files
    files.sort(key=lambda x: (x.get("kind") == "preview_artifact", x["path"]))
    return files


def _workspace_manifest_payload(workspace: Path, job_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    paths = {str(row.get("path") or "") for row in files}
    source_count = sum(1 for row in files if row.get("kind") == "source")
    preview_count = sum(1 for row in files if row.get("kind") == "preview_artifact")
    total_size = sum(int(row.get("size") or 0) for row in files)
    candidate_exists = any(p.exists() and p.is_dir() for p in _workspace_candidates(workspace, job_id))
    has_app_entry = any(
        path.endswith(("App.jsx", "App.js", "App.tsx", "App.ts", "main.jsx", "main.tsx", "index.jsx", "index.tsx"))
        for path in paths
    )
    digest = hashlib.sha256("\n".join(sorted(paths)[:200]).encode("utf-8")).hexdigest()[:16]
    return {
        "job_id": job_id,
        "workspace_exists": candidate_exists,
        "count": len(files),
        "total_count": len(files),
        "source_count": source_count,
        "preview_artifact_count": preview_count,
        "has_package_json": "package.json" in paths,
        "has_app_entry": has_app_entry,
        "has_dist_index": "dist/index.html" in paths,
        "fingerprint": f"{len(files)}:{total_size}:{digest}",
    }


def _stable_task_id_for_job(job_id: str) -> str:
    clean = str(job_id or "").strip()
    return f"task_job_{clean}" if clean else ""


# Durable runtime job ids from task_manager are tsk_{12 hex chars}.
_RAW_TASK_JOB_ID = re.compile(r"^tsk_[0-9a-f]{12}$", re.IGNORECASE)


def _job_id_from_task_id(task_id: Optional[str]) -> Optional[str]:
    raw = str(task_id or "").strip()
    if raw.startswith("task_job_") and len(raw) > len("task_job_"):
        return raw[len("task_job_"):]
    # URL may carry the canonical id without the task_job_ wrapper (bookmarks, API links).
    if _RAW_TASK_JOB_ID.match(raw):
        return raw
    return None


def _job_id_from_session_id(session_id: Optional[str]) -> Optional[str]:
    raw = str(session_id or "").strip()
    if raw.startswith("job:") and len(raw) > len("job:"):
        return raw[len("job:"):]
    return _job_id_from_task_id(raw)


def _project_id_from_session_id(session_id: Optional[str]) -> Optional[str]:
    raw = str(session_id or "").strip()
    if raw.startswith("project:") and len(raw) > len("project:"):
        return raw[len("project:"):]
    return None


async def _load_job_for_session(job_id: str, user: dict) -> Dict[str, Any]:
    try:
        from ..db_pg import get_pg_pool
        from ..server import _assert_job_owner_match
        from ..orchestration import runtime_state as _runtime_state

        try:
            pool = await get_pg_pool()
        except Exception as exc:
            logger.warning("workspace session: continuing without DB pool for job %s: %s", job_id, exc)
            pool = None
        if pool is not None:
            _runtime_state.set_pool(pool)
        job = await _runtime_state.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        _assert_job_owner_match(job.get("user_id"), user)
        return dict(job)
    except HTTPException:
        raise
    except (ImportError, AttributeError) as exc:
        raise HTTPException(status_code=503, detail=f"Workspace session resolver unavailable: {exc}")


async def _load_latest_job_for_project(project_id: str, user: dict) -> Optional[Dict[str, Any]]:
    """Best-effort latest job lookup for project-only workspace reopen."""
    try:
        from ..db_pg import get_pg_pool
        from ..server import _assert_job_owner_match
    except (ImportError, AttributeError):
        return None

    try:
        pool = await get_pg_pool()
    except Exception as exc:
        logger.warning("workspace session: latest-job lookup skipped for project %s: %s", project_id, exc)
        return None
    if pool is None:
        return None

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, project_id, user_id, status, goal, created_at, updated_at, started_at, completed_at
                FROM jobs
                WHERE project_id = $1
                ORDER BY
                  COALESCE(updated_at, created_at, started_at, completed_at) DESC NULLS LAST,
                  created_at DESC NULLS LAST
                LIMIT 1
                """,
                project_id,
            )
        if not row:
            return None
        job = dict(row)
        _assert_job_owner_match(job.get("user_id"), user)
        return job
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug("workspace session: latest-job query failed for %s: %s", project_id, exc)
        return None


def _preview_status_for_session(job_id: str, workspace: Path, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    manifest = _workspace_manifest_payload(workspace, job_id, files)
    serve_root: Optional[Path] = None
    try:
        from .preview_serve import _resolve_serve_root

        for candidate in _workspace_candidates(workspace, job_id):
            root = _resolve_serve_root(candidate)
            if root is not None and (root / "index.html").exists():
                serve_root = root
                break
    except Exception as exc:
        logger.debug("workspace session: preview readiness scan skipped for %s: %s", job_id, exc)

    if serve_root is not None:
        status = "ready"
        url = f"/api/preview/{job_id}/serve" if job_id else None
    elif manifest.get("has_package_json") or manifest.get("has_app_entry"):
        status = "building"
        url = None
    elif manifest.get("workspace_exists"):
        status = "preparing"
        url = None
    else:
        status = "unavailable"
        url = None

    return {
        "status": status,
        "url": url,
        "serveRoot": str(serve_root) if serve_root is not None else None,
        "manifest": manifest,
    }


def _workspace_session_payload(
    *,
    job: Optional[Dict[str, Any]],
    job_id: Optional[str],
    task_id: Optional[str],
    project_id: Optional[str],
    workspace: Path,
    files: List[Dict[str, Any]],
    resolved_from: str,
) -> Dict[str, Any]:
    durable_job_id = str((job_id or (job.get("id") if job else "")) or "").strip()
    durable_project_id = str((project_id or (job.get("project_id") if job else "")) or "").strip()
    durable_task_id = str(_stable_task_id_for_job(durable_job_id) or task_id or "").strip()
    session_id = f"job:{durable_job_id}" if durable_job_id else f"project:{durable_project_id}"
    return {
        "sessionId": session_id,
        "taskId": durable_task_id or None,
        "jobId": durable_job_id or None,
        "projectId": durable_project_id or None,
        "status": (job or {}).get("status") or ("idle" if durable_project_id else "unknown"),
        "goal": (job or {}).get("goal") or "",
        "threadId": f"job:{durable_job_id}" if durable_job_id else None,
        "workspacePath": str(workspace),
        "workspaceExists": any(p.exists() and p.is_dir() for p in _workspace_candidates(workspace, durable_job_id)),
        "previewStatus": _preview_status_for_session(durable_job_id, workspace, files),
        "resolvedFrom": resolved_from,
    }


def _resolve_job_workspace_file(workspace: Path, rel: str, job_id: str = "") -> Path:
    for candidate in _workspace_candidates(workspace, job_id):
        try:
            full = _safe_resolve(candidate, rel)
        except HTTPException:
            raise
        if full.exists() and full.is_file():
            return full
    return _safe_resolve(workspace, rel)


@router.get("/workspace/session/resolve")
async def resolve_workspace_session(
    sessionId: Optional[str] = Query(None, description="Canonical session id, e.g. job:{id}"),
    taskId: Optional[str] = Query(None, description="Frontend task id, including task_job_{jobId}"),
    jobId: Optional[str] = Query(None, description="Backend job id"),
    projectId: Optional[str] = Query(None, description="Project id fallback"),
    user: dict = Depends(_get_auth()),
):
    """Resolve scattered workspace identifiers into one canonical session.

    This is the backend contract the frontend uses before binding chat, preview,
    files, proof, timeline, and task history to a workspace. It intentionally
    does not build or mutate the workspace; preview materialization remains in
    /api/jobs/{job_id}/dev-preview and final gates.
    """
    resolved_job_id = (
        str(jobId or "").strip()
        or _job_id_from_session_id(sessionId)
        or _job_id_from_task_id(taskId)
    )
    resolved_project_id = str(projectId or "").strip() or _project_id_from_session_id(sessionId)

    if resolved_job_id:
        try:
            job = await _load_job_for_session(resolved_job_id, user)
            resolved_project_id = str(job.get("project_id") or resolved_project_id or resolved_job_id)
            workspace = _project_workspace_path(resolved_project_id)
            files = _collect_job_workspace_files(workspace, resolved_job_id)
            return {
                "success": True,
                "session": _workspace_session_payload(
                    job=job,
                    job_id=resolved_job_id,
                    task_id=taskId,
                    project_id=resolved_project_id,
                    workspace=workspace,
                    files=files,
                    resolved_from="job",
                ),
            }
        except HTTPException as exc:
            if exc.status_code != 404 or not resolved_project_id:
                raise
            logger.info(
                "workspace session: stale job %s; falling back to latest job for project %s",
                resolved_job_id,
                resolved_project_id,
            )
            latest_job = await _load_latest_job_for_project(resolved_project_id, user)
            if not latest_job or not latest_job.get("id"):
                raise
            latest_job_id = str(latest_job.get("id") or "").strip()
            workspace = _project_workspace_path(str(latest_job.get("project_id") or resolved_project_id))
            files = _collect_job_workspace_files(workspace, latest_job_id)
            return {
                "success": True,
                "session": _workspace_session_payload(
                    job=latest_job,
                    job_id=latest_job_id,
                    task_id=taskId,
                    project_id=str(latest_job.get("project_id") or resolved_project_id),
                    workspace=workspace,
                    files=files,
                    resolved_from="project_latest_job_after_stale_job",
                ),
            }

    if resolved_project_id:
        # Sidebar/project reopen often lands with only projectId. Recover latest
        # authorized job so transcript/proof/files hydrate as the same build.
        latest_job = await _load_latest_job_for_project(resolved_project_id, user)
        if latest_job and latest_job.get("id"):
            latest_job_id = str(latest_job.get("id") or "").strip()
            workspace = _project_workspace_path(str(latest_job.get("project_id") or resolved_project_id))
            files = _collect_job_workspace_files(workspace, latest_job_id)
            return {
                "success": True,
                "session": _workspace_session_payload(
                    job=latest_job,
                    job_id=latest_job_id,
                    task_id=taskId,
                    project_id=str(latest_job.get("project_id") or resolved_project_id),
                    workspace=workspace,
                    files=files,
                    resolved_from="project_latest_job",
                ),
            }

        workspace = await _assert_project_access(resolved_project_id, user)
        files = _collect_job_workspace_files(workspace, "")
        return {
            "success": True,
            "session": _workspace_session_payload(
                job=None,
                job_id=None,
                task_id=taskId,
                project_id=resolved_project_id,
                workspace=workspace,
                files=files,
                resolved_from="project",
            ),
        }

    raise HTTPException(status_code=400, detail="Provide jobId, taskId, sessionId, or projectId")


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
    all_files = _collect_job_workspace_files(workspace, job_id)
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


@router.get("/jobs/{job_id}/workspace/manifest")
async def get_job_workspace_manifest(
    job_id: str,
    user: dict = Depends(_get_auth()),
):
    """Compact workspace manifest for polling while a job is active."""
    workspace = await _assert_job_access(job_id, user)
    all_files = _collect_job_workspace_files(workspace, job_id)
    return _workspace_manifest_payload(workspace, job_id, all_files)


@router.get("/jobs/{job_id}/workspace/file")
async def get_job_workspace_file(
    job_id: str,
    path: str = Query(..., description="Relative file path within workspace"),
    user: dict = Depends(_get_auth()),
):
    """Get contents of a specific file in a job's workspace."""
    workspace = await _assert_job_access(job_id, user)
    full_path = _resolve_job_workspace_file(workspace, path, job_id)

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
    full_path = _resolve_job_workspace_file(workspace, path, job_id)
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media = mimetypes.guess_type(full_path.name)[0] or "application/octet-stream"
    return FileResponse(path=str(full_path), media_type=media, filename=full_path.name)


@router.post("/jobs/{job_id}/visual-edit")
async def visual_edit_job_workspace_file(
    job_id: str,
    body: VisualEditRequest,
    user: dict = Depends(_get_auth()),
):
    """Apply a single find/replace patch and snapshot the previous file content."""
    workspace = await _assert_job_access(job_id, user)
    rel_path = (body.file_path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel_path or not rel_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    full = _safe_resolve(workspace, rel_path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not body.find_text:
        raise HTTPException(status_code=400, detail="find_text is required")

    before = full.read_text(encoding="utf-8", errors="replace")
    if body.find_text not in before:
        raise HTTPException(status_code=400, detail="find_text not found in target file")
    after = before.replace(body.find_text, body.replace_text, 1)

    snapshot_dir = workspace / ".crucibai" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{full.name}.bak"
    snapshot_path = snapshot_dir / snapshot_name
    snapshot_path.write_text(before, encoding="utf-8")
    full.write_text(after, encoding="utf-8")

    return {
        "status": "patched",
        "job_id": job_id,
        "file_path": rel_path,
        "snapshot_path": str(snapshot_path.relative_to(workspace)).replace("\\", "/"),
        "changed": True,
        "find_text": body.find_text,
        "replace_text": body.replace_text,
    }


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
@router.get("/jobs/{job_id}/workspace-zip")
@router.get("/jobs/{job_id}/export/full.zip")
async def download_job_workspace_zip(
    job_id: str,
    draft: bool = Query(False, description="Skip integrity gates for interim exports"),
    user: dict = Depends(_get_auth()),
):
    """
    Download the complete job workspace as a ZIP file.
    This is the proof/handoff bundle — everything the AI built.

    Completed jobs must pass the same delivery gates as job completion (BIV marker,
    artifact reconciliation, live-proof separation). Use ``?draft=true`` only for
    in-progress debugging exports.
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    from ..orchestration import runtime_state as _runtime_state
    from ..orchestration.delivery_gate import assert_workspace_download_allowed

    workspace = await _assert_job_access(job_id, user)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace not found or empty")

    job_row = await _runtime_state.get_job(job_id)
    assert_workspace_download_allowed(str(workspace), job_row, draft=draft)

    # Build ZIP in memory
    buf = io.BytesIO()
    skip_dirs = {"node_modules", ".git", "__pycache__", ".pytest_cache"}
    skip_exts = {".pyc", ".pyo"}
    file_count = 0

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
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
