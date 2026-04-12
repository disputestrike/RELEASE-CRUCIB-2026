"""SSO routes — WorkOS/SAML single sign-on login, callback, and organization listing."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sso"])


def _get_auth():
    from server import get_current_user

    return get_current_user


def _get_optional_user():
    from server import get_optional_user

    return get_optional_user


def _get_db():
    import server

    return server.db


def _jwt_secret():
    import server

    return server.JWT_SECRET


def _jwt_algorithm():
    import server

    return server.JWT_ALGORITHM


@router.get("/sso/login")
async def sso_login(
    organization_id: Optional[str] = Query(None), email: Optional[str] = Query(None)
):
    """
    Initiate WorkOS/SAML SSO login. Redirects to IdP.
    Set WORKOS_API_KEY and WORKOS_CLIENT_ID env vars to enable real SSO.
    """
    workos_api_key = os.environ.get("WORKOS_API_KEY", "")
    workos_client_id = os.environ.get("WORKOS_CLIENT_ID", "")
    if not workos_api_key or not workos_client_id:
        # Return a helpful error — SSO not configured yet
        raise HTTPException(
            status_code=501,
            detail={
                "error": "SSO_NOT_CONFIGURED",
                "message": "SAML SSO is available on the Enterprise plan. Contact support@crucibai.com to set up SSO for your organization.",
                "setup_url": "/enterprise",
            },
        )
    # Build WorkOS authorization URL
    import httpx, urllib.parse

    params = {
        "client_id": workos_client_id,
        "redirect_uri": f"{os.environ.get('BACKEND_PUBLIC_URL', 'https://crucibai-production.up.railway.app')}/api/sso/callback",
        "response_type": "code",
    }
    if organization_id:
        params["organization"] = organization_id
    if email:
        params["login_hint"] = email
    auth_url = f"https://api.workos.com/sso/authorize?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url, "redirect": True}


@router.get("/sso/callback")
async def sso_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    """
    WorkOS SSO callback. Exchanges code for profile, creates/upserts user, returns JWT.
    """
    workos_api_key = os.environ.get("WORKOS_API_KEY", "")
    workos_client_id = os.environ.get("WORKOS_CLIENT_ID", "")
    workos_client_secret = os.environ.get("WORKOS_CLIENT_SECRET", "")
    if not workos_api_key:
        raise HTTPException(status_code=501, detail="SSO not configured")

    import httpx

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://api.workos.com/sso/token",
            headers={"Authorization": f"Bearer {workos_api_key}"},
            json={
                "client_id": workos_client_id,
                "client_secret": workos_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=502, detail=f"WorkOS SSO error: {r.text[:200]}"
            )
        token_data = r.json()
        access_token = token_data.get("access_token")

        # Get profile
        profile_r = await client.get(
            "https://api.workos.com/sso/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_r.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch SSO profile")
        profile = profile_r.json()

    email = profile.get("email", "").lower().strip()
    first = profile.get("first_name") or ""
    last = profile.get("last_name") or ""
    org_id = profile.get("organization_id", "")

    if not email:
        raise HTTPException(status_code=400, detail="SSO profile missing email")

    db = _get_db()
    # Upsert user in DB
    user_doc = None
    if db is not None:
        user_doc = await db.users.find_one({"email": email})
        now = datetime.now(timezone.utc).isoformat()
        if not user_doc:
            user_id = str(uuid.uuid4())
            user_doc = {
                "id": user_id,
                "email": email,
                "name": f"{first} {last}".strip() or email.split("@")[0],
                "plan": "enterprise",
                "sso_provider": "workos",
                "sso_organization_id": org_id,
                "created_at": now,
                "last_login": now,
            }
            await db.users.insert_one(user_doc)
        else:
            await db.users.update_one(
                {"email": email},
                {
                    "$set": {
                        "last_login": now,
                        "sso_provider": "workos",
                        "sso_organization_id": org_id,
                    }
                },
            )

    if not user_doc:
        raise HTTPException(status_code=500, detail="DB not available for SSO")

    # Issue JWT
    token_payload = {
        "user_id": user_doc["id"],
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    token = jwt.encode(token_payload, _jwt_secret(), algorithm=_jwt_algorithm())
    # Redirect to frontend with token (or return JSON)
    frontend_url = os.environ.get(
        "FRONTEND_URL", "https://crucibai-production.up.railway.app"
    )
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=f"{frontend_url}/app?sso_token={token}&email={email}", status_code=302
    )


@router.get("/sso/organizations")
async def sso_list_organizations(user: dict = Depends(_get_auth())):
    """List SSO organizations (enterprise admins only)."""
    workos_api_key = os.environ.get("WORKOS_API_KEY", "")
    if not workos_api_key:
        return {"organizations": [], "sso_configured": False}
    import httpx

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            "https://api.workos.com/organizations",
            headers={"Authorization": f"Bearer {workos_api_key}"},
        )
        if r.status_code != 200:
            return {"organizations": [], "error": r.text[:100]}
        return {"organizations": r.json().get("data", []), "sso_configured": True}
