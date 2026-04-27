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

import asyncio
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import time
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
    from backend.services.workspace_resolver import workspace_resolver

    return workspace_resolver.workspace_root()


async def _get_project_id_for_job(job_id: str) -> Optional[str]:
    """Look up the project_id for a job.

    Runtime state is in-memory and may be empty after a deploy/restart. Preview
    serving still needs to find completed workspaces, so fall back to Postgres.
    """
    try:
        from backend.orchestration.runtime_state import get_job
        job = await get_job(job_id)
        if job:
            return job.get("project_id") or job.get("id")
    except Exception as exc:
        logger.debug("preview_serve: runtime_state lookup failed for %s: %s", job_id, exc)

    try:
        from backend.db_pg import get_pg_pool

        pool = await get_pg_pool()
        if pool:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT project_id FROM jobs WHERE id = $1 LIMIT 1",
                    job_id,
                )
                if row and row.get("project_id"):
                    return str(row["project_id"])
    except Exception as exc:
        logger.debug("preview_serve: jobs.project_id lookup failed for %s: %s", job_id, exc)

    try:
        from backend.db_pg import get_pg_pool

        pool = await get_pg_pool()
        if pool:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT doc->>'project_id' AS project_id FROM jobs WHERE id = $1 LIMIT 1",
                    job_id,
                )
                if row and row.get("project_id"):
                    return str(row["project_id"])
    except Exception as exc:
        logger.debug("preview_serve: jobs.doc project_id lookup failed for %s: %s", job_id, exc)
    return None


def _job_workspace_root(job_id: str, project_id: Optional[str] = None) -> Path:
    """Resolve the workspace directory for a job.

    Priority:
    1. WORKSPACE_ROOT/projects/{project_id}  (canonical — matches executor.py)
    2. WORKSPACE_ROOT/projects/{job_id}      (fallback when project_id == job_id)
    3. WORKSPACE_ROOT/{job_id}               (legacy path)
    4. /tmp/workspaces/{job_id}              (last resort)
    """
    from backend.services.workspace_resolver import workspace_resolver

    return workspace_resolver.workspace_for_job(job_id, project_id).workspace


def _resolve_serve_root(workspace: Path) -> Optional[Path]:
    """Pick the best serve root.

    A directory is only servable when it has an index.html. Returning an
    arbitrary build/ or public/ folder without an app entry makes the UI poll
    forever and hides the generated source preview.
    """
    if not workspace.exists() or not workspace.is_dir():
        return None

    for sub in ("dist", "build", "out", "public"):
        candidate = workspace / sub
        if candidate.exists() and candidate.is_dir() and (candidate / "index.html").exists():
            return candidate.resolve()
    if (workspace / "index.html").exists():
        return workspace.resolve()
    return None


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


def _npm_bin() -> Optional[str]:
    return shutil.which("npm.cmd" if os.name == "nt" else "npm")


def _run_preview_build_sync(workspace: Path) -> Dict[str, Any]:
    """Materialize dist/index.html for preview when the job left source only."""
    meta_dir = workspace / ".crucibai"
    try:
        meta_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    fail_marker = meta_dir / "preview_build_failed.json"
    ok_marker = meta_dir / "preview_build_ok.json"

    dist_index = workspace / "dist" / "index.html"
    if dist_index.exists():
        return {
            "ok": True,
            "reason": "dist_already_exists",
            "serve_root": str(dist_index.parent.resolve()),
        }

    try:
        cooldown_sec = int(os.environ.get("CRUCIBAI_PREVIEW_BUILD_RETRY_COOLDOWN", "90"))
    except ValueError:
        cooldown_sec = 90
    if fail_marker.exists() and time.time() - fail_marker.stat().st_mtime < max(10, cooldown_sec):
        try:
            cached = json.loads(fail_marker.read_text(encoding="utf-8", errors="replace"))
            return {"ok": False, "reason": "recent_build_failure", **cached}
        except Exception:
            return {"ok": False, "reason": "recent_build_failure"}

    pkg_path = workspace / "package.json"
    if not pkg_path.exists():
        return {"ok": False, "reason": "package_json_missing"}
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "reason": "package_json_invalid", "error": str(exc)[:300]}
    if not (pkg.get("scripts") or {}).get("build"):
        return {"ok": False, "reason": "build_script_missing"}

    npm = _npm_bin()
    if not npm:
        return {"ok": False, "reason": "npm_missing"}

    try:
        install_timeout = int(os.environ.get("CRUCIBAI_NPM_INSTALL_TIMEOUT", "300"))
    except ValueError:
        install_timeout = 300
    try:
        build_timeout = int(os.environ.get("CRUCIBAI_NPM_BUILD_TIMEOUT", "180"))
    except ValueError:
        build_timeout = 180

    logs = []
    env = os.environ.copy()
    env.setdefault("CI", "true")
    commands = [
        ([npm, "install", "--include=dev", "--no-fund", "--no-audit"], install_timeout),
        ([npm, "run", "build"], build_timeout),
    ]
    for cmd, timeout in commands:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            payload = {
                "ok": False,
                "reason": "preview_build_timeout",
                "cmd": " ".join(cmd),
            }
            _write_preview_build_marker(fail_marker, payload)
            return payload
        except Exception as exc:
            payload = {
                "ok": False,
                "reason": "preview_build_exception",
                "cmd": " ".join(cmd),
                "error": str(exc)[:500],
            }
            _write_preview_build_marker(fail_marker, payload)
            return payload

        log = ((result.stdout or "") + (result.stderr or ""))[-2500:]
        logs.append({"cmd": " ".join(cmd), "exit": result.returncode, "log": log})
        if result.returncode != 0:
            payload = {"ok": False, "reason": "preview_build_failed", "logs": logs}
            _write_preview_build_marker(fail_marker, payload)
            return payload

    if dist_index.exists():
        payload = {"ok": True, "reason": "preview_build_materialized", "logs": logs[-1:]}
        _write_preview_build_marker(ok_marker, payload)
        try:
            fail_marker.unlink(missing_ok=True)
        except Exception:
            pass
        return payload

    payload = {"ok": False, "reason": "dist_index_missing_after_build", "logs": logs}
    _write_preview_build_marker(fail_marker, payload)
    return payload


def _write_preview_build_marker(path: Path, payload: Dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        logger.debug("preview_serve: could not write preview build marker %s", path)


async def _maybe_materialize_preview(workspace: Path) -> Dict[str, Any]:
    return await asyncio.to_thread(_run_preview_build_sync, workspace)


def _preview_public_base(request: Request) -> str:
    """Return the public origin that should serve preview iframe URLs."""
    try:
        headers = getattr(request, "headers", {}) or {}
        proto = (
            headers.get("x-forwarded-proto")
            or headers.get("x-forwarded-protocol")
            or ""
        ).split(",")[0].strip()
        host = (headers.get("x-forwarded-host") or headers.get("host") or "").split(",")[0].strip()
        if proto and host:
            return f"{proto}://{host}".rstrip("/")
    except Exception:
        pass
    try:
        bu = str(request.base_url)
        if bu:
            return bu.rstrip("/")
    except Exception:
        pass
    return (
        os.environ.get("CRUCIBAI_PUBLIC_BASE_URL", "").rstrip("/")
        or os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
        or ""
    )


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
    materialize = None
    if serve_root is None and workspace.exists() and (workspace / "package.json").exists():
        materialize = await _maybe_materialize_preview(workspace)
        serve_root = _resolve_serve_root(workspace)

    readiness = _preview_readiness_snapshot(workspace, serve_root)
    if materialize:
        readiness["materialize"] = materialize

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

    # The iframe URL must be loadable from the same public host that handled the
    # dev-preview request. Production can have stale/internal Railway env URLs,
    # while the public API route is exposed through www.crucibai.com.
    base = _preview_public_base(request)
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
