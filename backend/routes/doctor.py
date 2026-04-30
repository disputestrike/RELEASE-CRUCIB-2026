"""CF27 — /api/doctor diagnostic endpoint.

Adapted from claude-code-source-code/src/commands/doctor.
Reports environment health: Python version, Node version, key env vars
presence (not values), DB pool status, and LLM provider registration.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials

from ....deps import get_current_user, security
router = APIRouter(prefix="/api/doctor", tags=["doctor"])

CRITICAL_ROUTE_MODULES = {
    "backend.routes.auth",
    "backend.routes.runtime",
    "backend.routes.simulations",
    "backend.routes.projects",
    "backend.routes.voice_input",
    "backend.routes.orchestrator",
    "backend.routes.jobs",
    "backend.routes.workspace",
    "backend.routes.preview_serve",
    "backend.routes.approvals",
}


async def _optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except Exception:
        return None


def _cmd_version(cmd: List[str]) -> str:
    try:
        exe = shutil.which(cmd[0])
        if not exe:
            return "not installed"
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5)
        return out.decode("utf-8", errors="replace").strip().splitlines()[0]
    except Exception as exc:
        return f"error: {exc}"


@router.get("")
def doctor() -> Dict[str, Any]:
    env_present = {
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
        "REDIS_URL": bool(os.environ.get("REDIS_URL")),
        "JWT_SECRET": bool(os.environ.get("JWT_SECRET")),
    }
    checks = [
        {"name": "python", "status": "ok", "detail": sys.version.split()[0]},
        {"name": "platform", "status": "ok", "detail": f"{platform.system()} {platform.release()}"},
        {"name": "node", "status": "ok" if shutil.which("node") else "missing",
         "detail": _cmd_version(["node", "--version"])},
        {"name": "git", "status": "ok" if shutil.which("git") else "missing",
         "detail": _cmd_version(["git", "--version"])},
    ]
    warnings: List[str] = []
    if not env_present.get("ANTHROPIC_API_KEY") and not env_present.get("OPENAI_API_KEY"):
        warnings.append("No LLM provider key present (ANTHROPIC_API_KEY or OPENAI_API_KEY).")
    if not env_present.get("DATABASE_URL"):
        warnings.append("DATABASE_URL not set — running in fallback/sqlite mode.")
    status = "ok" if not warnings else "degraded"
    return {"status": status, "checks": checks, "env_present": env_present, "warnings": warnings}


@router.get("/routes")
def route_doctor() -> Dict[str, Any]:
    """Startup route audit: critical route failures must be visible."""
    try:
        from ....server import ROUTE_REGISTRATION_REPORT    except Exception as exc:
        return {
            "status": "failed",
            "loaded": [],
            "failed": [{"module": "backend.server", "error": str(exc)}],
            "critical_missing": sorted(CRITICAL_ROUTE_MODULES),
        }

    loaded = [r for r in ROUTE_REGISTRATION_REPORT if r.get("status") == "loaded"]
    failed = [r for r in ROUTE_REGISTRATION_REPORT if r.get("status") != "loaded"]
    loaded_modules = {r.get("module") for r in loaded}
    failed_modules = {r.get("module") for r in failed}
    critical_missing = sorted(
        module for module in CRITICAL_ROUTE_MODULES if module not in loaded_modules or module in failed_modules
    )
    optional_failed = [r for r in failed if r.get("module") not in CRITICAL_ROUTE_MODULES]
    return {
        "status": "ok" if not critical_missing else "failed",
        "route_count": len(loaded),
        "loaded": loaded,
        "failed": failed,
        "critical_missing": critical_missing,
        "optional_failed": optional_failed,
    }


@router.get("/preview")
async def preview_doctor(
    jobId: Optional[str] = Query(None, description="Optional authenticated job id to diagnose"),
    current_user: Optional[Dict[str, Any]] = Depends(_optional_current_user),
) -> Dict[str, Any]:
    """Preview diagnostics without triggering npm/build side effects."""
    out: Dict[str, Any] = {
        "status": "ok",
        "static_strategy": "npm run build -> backend static serve",
        "serve_route": "/api/preview/{job_id}/serve",
        "dev_preview_route": "/api/jobs/{job_id}/dev-preview",
        "required_artifact": "dist/index.html",
        "node_available": bool(shutil.which("node")),
        "npm_available": bool(shutil.which("npm")),
    }
    if not jobId:
        return out
    if not current_user:
        out.update({"status": "auth_required", "job": None})
        return out

    try:
        from ....routes.workspace import _assert_job_access, _collect_job_workspace_files, _workspace_manifest_payload        from ....routes.preview_serve import _resolve_serve_root
        workspace = await _assert_job_access(jobId, current_user)
        files = _collect_job_workspace_files(workspace, jobId)
        manifest = _workspace_manifest_payload(workspace, jobId, files)
        serve_root = _resolve_serve_root(Path(workspace))
        out["job"] = {
            "job_id": jobId,
            "workspace_exists": manifest.get("workspace_exists"),
            "has_package_json": manifest.get("has_package_json"),
            "has_app_entry": manifest.get("has_app_entry"),
            "has_dist_index": manifest.get("has_dist_index"),
            "preview_status": "ready" if serve_root else "not_ready",
        }
        out["status"] = "ok" if serve_root else "degraded"
    except Exception as exc:
        out.update({"status": "failed", "job": {"job_id": jobId, "error": str(exc)[:300]}})
    return out
