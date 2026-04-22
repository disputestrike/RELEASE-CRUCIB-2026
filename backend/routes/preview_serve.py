"""Preview serve route — static file serving of a job's built app workspace.

Exposes:
    GET /api/preview/{job_id}/serve/{path:path}

Resolves the job's workspace directory (prefers ``build/`` or ``dist/``
subdirectories if they exist, else the workspace root), serves files with
appropriate MIME types, guards against path traversal, and falls back to
``index.html`` for SPA routes.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preview", tags=["preview-serve"])


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


def _job_workspace_root(job_id: str) -> Path:
    """Resolve the workspace directory for a job.

    Mirrors the pattern used in ``adapter/routes/files.py`` —
    ``WORKSPACE_ROOT / job_id`` when available, else ``/tmp/workspaces/{job_id}``.
    """
    try:
        from server import WORKSPACE_ROOT  # type: ignore
        return Path(WORKSPACE_ROOT) / job_id
    except Exception:
        return Path(f"/tmp/workspaces/{job_id}")


def _resolve_serve_root(job_id: str) -> Optional[Path]:
    """Pick the best serve root — prefer build/ or dist/ if present.

    Returns ``None`` if the workspace doesn't exist yet.
    """
    workspace = _job_workspace_root(job_id)
    if not workspace.exists() or not workspace.is_dir():
        return None
    # Prefer conventional output directories. Order matters — first hit wins.
    for sub in ("build", "dist", "out", "public"):
        candidate = workspace / sub
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return workspace.resolve()


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


@router.get("/{job_id}/serve/{path:path}")
async def serve_preview(job_id: str, path: str):
    """Serve a static file from the job's workspace, falling back to
    ``index.html`` for SPA client-side routes."""
    root = _resolve_serve_root(job_id)
    if root is None:
        raise HTTPException(status_code=404, detail="No workspace yet")

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


@router.get("/{job_id}/serve")
async def serve_preview_root(job_id: str):
    """Convenience alias: ``/api/preview/{job_id}/serve`` → index.html."""
    return await serve_preview(job_id, "index.html")
