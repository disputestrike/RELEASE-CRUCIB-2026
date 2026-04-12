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
    from server import get_current_user

    return get_current_user


def _get_db():
    from server import db

    return db


# ── Deploy token management ───────────────────────────────────────────────────


@router.get("/users/me/deploy-tokens")
async def get_deploy_tokens_status(user: dict = Depends(_get_auth())):
    """Return whether user has each deploy token set (no secret values returned)."""
    db = _get_db()
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
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
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    return {"ok": True}


# ── Deploy validation ─────────────────────────────────────────────────────────


@router.post("/deploy/validate")
async def deploy_validate(body: DeployValidateRequest):
    """Validate a set of project files against platform-specific deploy rules."""
    from validate_deployment import validate_deployment

    result = validate_deployment(body.platform, body.files, body.config)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "platform": result.platform,
    }
