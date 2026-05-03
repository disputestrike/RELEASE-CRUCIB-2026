"""
Deploy routes — token management, validation, and platform helpers.

Extracted from server.py as part of the server modularisation effort.
All heavy server-state (db, auth) is imported lazily to avoid circular imports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["deploy"])


# ── Pydantic models ───────────────────────────────────────────────────────────


class DeployTokensUpdate(BaseModel):
    """Token update payload for one-click deploy integrations."""

    vercel: Optional[str] = None
    netlify: Optional[str] = None
    github: Optional[str] = None
    railway: Optional[str] = None


class DeployValidateRequest(BaseModel):
    """Payload for pre-flight deploy validation."""

    platform: str  # vercel | netlify | railway
    files: Dict[str, str] = {}
    config: Optional[Dict[str, Any]] = None


# ── Lazy-import helpers ───────────────────────────────────────────────────────


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_optional_user():
    from ..deps import get_optional_user

    return get_optional_user


def _get_db():
    try:
        from ..deps import get_db

        return get_db()
    except Exception:
        return None


def _user_id(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "guest")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "guest")


# ── Deploy token management ───────────────────────────────────────────────────


@router.get("/users/me/deploy-tokens")
async def get_deploy_tokens_status(user: dict = Depends(_get_auth())):
    """Return whether user has each deploy token set (no secret values returned)."""
    db = _get_db()
    if db is None:
        return {
            "has_vercel": False,
            "has_netlify": False,
            "has_github": False,
            "has_railway": False,
            "status": "ready_without_persistence",
        }
    u = await db.users.find_one({"id": _user_id(user)}, {"deploy_tokens": 1})
    dt = (u or {}).get("deploy_tokens") or {}
    return {
        "has_vercel": bool(dt.get("vercel")),
        "has_netlify": bool(dt.get("netlify")),
        "has_github": bool(dt.get("github")),
        "has_railway": bool(dt.get("railway")),
    }


@router.patch("/users/me/deploy-tokens")
async def update_deploy_tokens(
    data: DeployTokensUpdate, user: dict = Depends(_get_auth())
):
    """Persist deploy tokens for one-click Vercel/Netlify/Railway. Only updates provided keys."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Deploy token persistence is not ready")
    update: dict = {}
    if data.vercel is not None:
        update["deploy_tokens.vercel"] = data.vercel.strip() or None
    if data.netlify is not None:
        update["deploy_tokens.netlify"] = data.netlify.strip() or None
    if data.github is not None:
        update["deploy_tokens.github"] = data.github.strip() or None
    if data.railway is not None:
        update["deploy_tokens.railway"] = data.railway.strip() or None
    if not update:
        return {"ok": True}
    await db.users.update_one({"id": _user_id(user)}, {"$set": update})
    return {"ok": True}


@router.get("/deploy/targets")
async def deploy_targets(user: dict = Depends(_get_optional_user())):
    """List deploy target readiness honestly for the settings/deploy UI."""
    token_status = (
        await get_deploy_tokens_status(user)
        if user
        else {"has_railway": False, "has_vercel": False, "has_netlify": False, "has_github": False}
    )
    return {
        "targets": [
            {"id": "railway", "name": "Railway", "status": "requires_config", "configured": bool(token_status.get("has_railway"))},
            {"id": "vercel", "name": "Vercel", "status": "requires_config", "configured": bool(token_status.get("has_vercel"))},
            {"id": "netlify", "name": "Netlify", "status": "requires_config", "configured": bool(token_status.get("has_netlify"))},
            {"id": "github", "name": "GitHub", "status": "requires_config", "configured": bool(token_status.get("has_github"))},
            {"id": "download_zip", "name": "Download ZIP", "status": "available", "configured": True},
        ],
        "note": "Hosted deploy targets require user-provided credentials; ZIP export remains available when workspace files exist.",
    }


# ── Deploy validation ─────────────────────────────────────────────────────────


@router.post("/deploy/validate")
async def deploy_validate(body: DeployValidateRequest):
    """Validate a set of project files against platform-specific deploy rules."""
    from ..validate_deployment import validate_deployment

    result = validate_deployment(body.platform, body.files, body.config)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "platform": result.platform,
    }


# ── Manual one-click deploy for a completed job ───────────────────────────────


@router.post("/jobs/{job_id}/deploy")
async def deploy_job(job_id: str, user: dict = Depends(_get_auth())):
    """
    Trigger a Netlify deploy for a completed job's dist folder.
    Returns {"url": "https://xxx.netlify.app"} on success.
    Requires NETLIFY_TOKEN set in Railway environment variables.
    """
    from backend.services.netlify_deploy import netlify_configured, deploy_to_netlify

    if not netlify_configured():
        raise HTTPException(
            status_code=503,
            detail="NETLIFY_TOKEN is not configured. Set it in your Railway environment variables.",
        )

    # Resolve workspace path for this job
    try:
        from backend.orchestration.runtime_state import runtime_state_adapter
        job = await runtime_state_adapter.get_job(job_id)
    except Exception:
        job = None

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    workspace_path = job.get("workspace_path") or job.get("workspace") or ""
    if not workspace_path:
        raise HTTPException(status_code=422, detail="No workspace found for this job — cannot deploy")

    # Find dist dir
    import os
    dist_dir = os.path.join(workspace_path, "dist")
    if not os.path.isdir(dist_dir):
        for alt in ("build", "out", "public"):
            candidate = os.path.join(workspace_path, alt)
            if os.path.isdir(candidate):
                dist_dir = candidate
                break

    if not os.path.isdir(dist_dir):
        raise HTTPException(
            status_code=422,
            detail=f"No built dist folder found at {workspace_path} — run a build first",
        )

    try:
        site_name = f"crucibai-{job_id[:12]}"
        result = await deploy_to_netlify(dist_dir=dist_dir, site_name=site_name)
        live_url = result.get("url")

        # Persist live_url back to job
        try:
            from backend.orchestration.runtime_state import update_job_state
            await update_job_state(job_id, job.get("status", "completed"), extra={"live_url": live_url})
        except Exception:
            pass

        return {"url": live_url, "site_id": result.get("site_id"), "deploy_id": result.get("deploy_id")}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
