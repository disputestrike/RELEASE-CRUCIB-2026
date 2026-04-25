"""Preview serve route — static file serving of a job's built app workspace.

Exposes:
    GET /api/preview/{job_id}/serve/{path:path}
    GET /api/preview/{job_id}/serve            (index.html alias)
    GET /api/jobs/{job_id}/dev-preview         (returns serve URL for PreviewPanel)

Resolves the job's workspace directory via the job's project_id
(``WORKSPACE_ROOT/projects/{project_id}``), then prefers build/ or dist/
subdirectories if they exist, else the workspace root.
"""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["preview-serve"])


# Extensions that text/binary MIME lookup commonly misses.
_MIME_OVERRIDES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".cjs": "application/javascript",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".map": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml",
}


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[ext]
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def _workspace_root() -> Path:
    """Return the configured WORKSPACE_ROOT."""
    try:
        from backend.config import WORKSPACE_ROOT
        return Path(WORKSPACE_ROOT)
    except Exception:
        try:
            from backend.project_state import WORKSPACE_ROOT
            return Path(WORKSPACE_ROOT)
        except Exception:
            return Path("/tmp/workspaces")


async def _get_project_id_for_job(job_id: str) -> Optional[str]:
    """Look up the project_id for a job from runtime_state."""
    try:
        from backend.orchestration.runtime_state import get_job
        job = await get_job(job_id)
        if job:
            return job.get("project_id") or job.get("id")
    except Exception as exc:
        logger.debug("preview_serve: could not look up job %s: %s", job_id, exc)
    return None


def _job_workspace_root(job_id: str, project_id: Optional[str] = None) -> Path:
    """Resolve the workspace directory for a job.

    Priority:
    1. WORKSPACE_ROOT/projects/{project_id}  (canonical — matches executor.py)
    2. WORKSPACE_ROOT/projects/{job_id}      (fallback when project_id == job_id)
    3. WORKSPACE_ROOT/{job_id}               (legacy path)
    4. /tmp/workspaces/{job_id}              (last resort)
    """
    root = _workspace_root()
    pid = project_id or job_id

    candidates = [
        root / "projects" / pid,
        root / "projects" / job_id,
        root / job_id,
        Path(f"/tmp/workspaces/{job_id}"),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # Return the canonical path even if it doesn't exist yet
    return root / "projects" / pid


def _resolve_serve_root(workspace: Path) -> Optional[Path]:
    """Pick the best serve root — prefer build/ or dist/ if present.

    Returns ``None`` if the workspace doesn't exist yet.
    """
    if not workspace.exists() or not workspace.is_dir():
        return None
    # Prefer conventional output directories. Order matters — first hit wins.
    for sub in ("build", "dist", "out", "public"):
        candidate = workspace / sub
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return workspace.resolve()


def _preview_readiness_snapshot(workspace: Path, serve_root: Optional[Path]) -> Dict[str, Any]:
    """Return a compact preview state descriptor for UI and support."""
    checked_roots = [str(workspace / sub) for sub in ("build", "dist", "out", "public")]
    if serve_root is None:
        return {
            "workspace_exists": workspace.exists(),
            "serve_root": None,
            "has_index": False,
            "file_count": 0,
            "checked_roots": checked_roots,
            "state": "waiting_for_workspace",
            "reason": "workspace_not_found" if not workspace.exists() else "no_serve_root",
        }
    try:
        files = [p for p in serve_root.rglob("*") if p.is_file()]
    except Exception:
        files = []
    has_index = (serve_root / "index.html").exists()
    return {
        "workspace_exists": workspace.exists(),
        "serve_root": str(serve_root),
        "has_index": has_index,
        "file_count": len(files),
        "checked_roots": checked_roots,
        "state": "ready" if has_index else "waiting_for_index",
        "reason": None if has_index else "index_html_missing",
        "sample_files": [str(p.relative_to(serve_root)).replace("\\", "/") for p in files[:12]],
    }


async def _resolve_root_for_job(job_id: str) -> Optional[Path]:
    """Async helper: look up project_id, then resolve serve root."""
    project_id = await _get_project_id_for_job(job_id)
    workspace = _job_workspace_root(job_id, project_id)
    return _resolve_serve_root(workspace)


def _safe_join(root: Path, rel: str) -> Optional[Path]:
    """Safely join ``rel`` onto ``root`` guarding against path traversal."""
    cleaned = (rel or "").strip().lstrip("/").replace("\\", "/")
    if ".." in cleaned.split("/"):
        return None
    try:
        full = (root / cleaned).resolve()
    except Exception:
        return None
    try:
        full.relative_to(root)
    except ValueError:
        return None
    return full


@router.get("/api/preview/{job_id}/serve/{path:path}")
async def serve_preview(job_id: str, path: str):
    """Serve a static file from the job's workspace, falling back to
    ``index.html`` for SPA client-side routes."""
    root = await _resolve_root_for_job(job_id)
    if root is None:
        raise HTTPException(status_code=404, detail="No workspace yet — build may still be running")

    target = _safe_join(root, path)
    if target is None:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Directory → look for index.html inside it.
    if target.exists() and target.is_dir():
        idx = target / "index.html"
        if idx.exists() and idx.is_file():
            return FileResponse(str(idx), media_type=_guess_mime(idx))
        target = None  # fall through to SPA fallback

    if target is not None and target.exists() and target.is_file():
        return FileResponse(str(target), media_type=_guess_mime(target))

    # SPA fallback — serve root index.html so client-side routes work.
    fallback = root / "index.html"
    if fallback.exists() and fallback.is_file():
        return FileResponse(str(fallback), media_type="text/html; charset=utf-8")

    raise HTTPException(status_code=404, detail="File not found")


@router.get("/api/preview/{job_id}/serve")
async def serve_preview_root(job_id: str):
    """Convenience alias: ``/api/preview/{job_id}/serve`` → index.html."""
    return await serve_preview(job_id, "index.html")


@router.get("/api/jobs/{job_id}/dev-preview")
async def dev_preview(job_id: str, request: Request):
    """Return a serve URL for the PreviewPanel iframe.

    Called by the frontend PreviewPanel when no remote preview_url is set.
    Returns the /api/preview/{job_id}/serve URL so the iframe can load the
    built workspace files directly from the backend.
    """
    project_id = await _get_project_id_for_job(job_id)
    workspace = _job_workspace_root(job_id, project_id)
    serve_root = _resolve_serve_root(workspace)
    readiness = _preview_readiness_snapshot(workspace, serve_root)

    if serve_root is None:
        return JSONResponse(
            status_code=202,
            content={
                "dev_server_url": None,
                "status": "pending",
                "preview_state": "waiting_for_workspace",
                "readiness": readiness,
                "detail": "Workspace not ready yet — build may still be running",
            },
        )

    has_index = (serve_root / "index.html").exists()
    if not has_index:
        return JSONResponse(
            status_code=202,
            content={
                "dev_server_url": None,
                "status": "building",
                "preview_state": "waiting_for_index",
                "readiness": readiness,
                "detail": "Build in progress — no index.html yet",
            },
        )

    base = (
        os.environ.get("CRUCIBAI_PUBLIC_BASE_URL", "").rstrip("/")
        or os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
        or ""
    )
    if not base:
        # Same-origin and split frontend/API: relative "/api/..." in an iframe src resolves to the
        # *page* host, not the API. Prefer request base URL (honors X-Forwarded-* on Railway) so
        # dev-preview returns a URL the iframe can load.
        try:
            bu = str(request.base_url)
            if bu:
                base = bu.rstrip("/")
        except Exception:
            base = ""
    serve_url = f"{base}/api/preview/{job_id}/serve" if base else f"/api/preview/{job_id}/serve"

    return {
        "dev_server_url": serve_url,
        "status": "ready",
        "job_id": job_id,
        "project_id": project_id,
        "workspace_path": str(workspace),
        "serve_root": str(serve_root),
        "preview_state": "ready",
        "readiness": readiness,
    }
