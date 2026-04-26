from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..services.connector_credentials import (
    decrypt_secret,
    encrypt_secret,
    hash_secret,
    public_credential_doc,
    redact,
)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

CONNECTOR_CATALOG = {
    "gmail": {
        "type": "oauth",
        "provider": "google",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.compose"],
        "validate_url": "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        "required_env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "supported_actions": ["read_messages", "draft_reply", "summarize_threads"],
    },
    "calendar": {
        "type": "oauth",
        "provider": "google",
        "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
        "validate_url": "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1",
        "required_env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "supported_actions": ["list_events", "summarize_schedule"],
    },
    "notion": {
        "type": "api_token",
        "provider": "notion",
        "validate_url": "https://api.notion.com/v1/users/me",
        "required_env": [],
        "supported_actions": ["read_pages", "read_databases", "read_tasks"],
    },
}


class CredentialBody(BaseModel):
    access_token: Optional[str] = Field(None, max_length=10000)
    refresh_token: Optional[str] = Field(None, max_length=10000)
    api_token: Optional[str] = Field(None, max_length=10000)
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_optional_user():
    from ..deps import get_optional_user

    return get_optional_user


async def _db():
    from ..db_pg import get_db

    return await get_db()


def _uid(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "anonymous")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "anonymous")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_url() -> str:
    return (
        os.environ.get("CRUCIBAI_PUBLIC_BASE_URL")
        or os.environ.get("BACKEND_PUBLIC_URL")
        or os.environ.get("FRONTEND_URL")
        or "https://www.crucibai.com"
    ).rstrip("/")


def _frontend_url() -> str:
    return (os.environ.get("FRONTEND_URL") or "https://www.crucibai.com").rstrip("/")


def _env_ready(connector: str) -> bool:
    meta = CONNECTOR_CATALOG[connector]
    return all(os.environ.get(name) for name in meta.get("required_env", []))


async def _credential_for(user_id: str, connector: str) -> Optional[Dict[str, Any]]:
    db = await _db()
    return await db.connector_credentials.find_one({"user_id": user_id, "connector": connector, "status": "connected"})


def _catalog_entry(connector: str, user_connected: bool = False) -> Dict[str, Any]:
    meta = CONNECTOR_CATALOG[connector]
    env_ready = _env_ready(connector)
    if user_connected:
        status = "available"
    elif connector in {"gmail", "calendar"} and env_ready:
        status = "requires_user_connection"
    elif connector == "notion" and os.environ.get("NOTION_API_KEY"):
        status = "available"
    else:
        status = "requires_config"
    return {
        "name": connector,
        "status": status,
        "type": meta["type"],
        "provider": meta["provider"],
        "required_env": meta["required_env"],
        "env_ready": env_ready,
        "supported_actions": meta["supported_actions"],
    }


@router.get("/catalog")
async def connector_catalog(user: dict = Depends(_get_optional_user())):
    user_id = _uid(user)
    entries = []
    for name in CONNECTOR_CATALOG:
        connected = False
        if user:
            connected = bool(await _credential_for(user_id, name))
        entries.append(_catalog_entry(name, connected))
    return {"connectors": entries}


@router.get("/status")
async def connector_status(user: dict = Depends(_get_auth())):
    user_id = _uid(user)
    db = await _db()
    creds = await db.connector_credentials.find({"user_id": user_id}).to_list(100)
    connected = {c.get("connector"): public_credential_doc(c) for c in creds if c.get("status") == "connected"}
    entries = []
    for name in CONNECTOR_CATALOG:
        entries.append({**_catalog_entry(name, name in connected), "credential": connected.get(name)})
    return {"connectors": entries}


@router.get("/google/oauth-url")
async def google_oauth_url(connector: str = Query(...), user: dict = Depends(_get_auth())):
    if connector not in {"gmail", "calendar"}:
        raise HTTPException(status_code=400, detail="connector must be gmail or calendar")
    if not _env_ready(connector):
        raise HTTPException(status_code=503, detail="Google OAuth client is not configured")
    state_id = f"oauth_{uuid.uuid4().hex}"
    state_payload = {
        "id": state_id,
        "user_id": _uid(user),
        "connector": connector,
        "created_at": _now(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        "status": "pending",
    }
    db = await _db()
    await db.connector_oauth_states.insert_one(state_payload)
    state = base64.urlsafe_b64encode(json.dumps({"id": state_id}).encode("utf-8")).decode("utf-8")
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": f"{_base_url()}/api/connectors/google/callback",
        "response_type": "code",
        "scope": " ".join(CONNECTOR_CATALOG[connector]["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}", "state_id": state_id, "connector": connector}


@router.get("/google/callback")
async def google_oauth_callback(code: str = Query(...), state: str = Query(...)):
    try:
        payload = json.loads(base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8"))
        state_id = payload["id"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    db = await _db()
    state_doc = await db.connector_oauth_states.find_one({"id": state_id, "status": "pending"})
    if not state_doc:
        raise HTTPException(status_code=400, detail="OAuth state not found or already used")
    connector = state_doc["connector"]
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{_base_url()}/api/connectors/google/callback",
            },
        )
    if res.status_code >= 400:
        await db.connector_oauth_states.update_one({"id": state_id}, {"$set": {"status": "failed", "updated_at": _now()}})
        raise HTTPException(status_code=400, detail="Google token exchange failed")
    token = res.json()
    await _store_credential(
        state_doc["user_id"],
        connector,
        access_token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        expires_at=(datetime.now(timezone.utc) + timedelta(seconds=int(token.get("expires_in") or 3600))).isoformat(),
        metadata={"scope": token.get("scope"), "token_type": token.get("token_type"), "source": "google_oauth"},
    )
    await db.connector_oauth_states.update_one({"id": state_id}, {"$set": {"status": "completed", "updated_at": _now()}})
    return RedirectResponse(f"{_frontend_url()}/app/settings?connector={connector}&status=connected")


async def _store_credential(
    user_id: str,
    connector: str,
    *,
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_token: str | None = None,
    expires_at: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    db = await _db()
    existing = await db.connector_credentials.find_one({"user_id": user_id, "connector": connector})
    doc_id = existing.get("id") if existing else f"cred_{uuid.uuid4().hex}"
    now = _now()
    doc = {
        "id": doc_id,
        "user_id": user_id,
        "connector": connector,
        "status": "connected",
        "provider": CONNECTOR_CATALOG[connector]["provider"],
        "credential_type": CONNECTOR_CATALOG[connector]["type"],
        "token_hash": hash_secret(access_token or api_token or refresh_token),
        "redacted_token": redact(access_token or api_token or refresh_token),
        "expires_at": expires_at,
        "metadata": metadata or {},
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    if access_token:
        doc["encrypted_access_token"] = encrypt_secret(access_token)
    if refresh_token:
        doc["encrypted_refresh_token"] = encrypt_secret(refresh_token)
    if api_token:
        doc["encrypted_api_token"] = encrypt_secret(api_token)
    if existing:
        await db.connector_credentials.update_one({"id": doc_id}, {"$set": doc})
    else:
        await db.connector_credentials.insert_one(doc)
    return doc


@router.post("/{connector}/credentials")
async def save_connector_credentials(connector: str, body: CredentialBody, user: dict = Depends(_get_auth())):
    if connector not in CONNECTOR_CATALOG:
        raise HTTPException(status_code=404, detail="Unknown connector")
    if connector == "notion" and not body.api_token:
        raise HTTPException(status_code=400, detail="api_token is required for Notion")
    if connector in {"gmail", "calendar"} and not (body.access_token or body.refresh_token):
        raise HTTPException(status_code=400, detail="access_token or refresh_token is required for Google connectors")
    doc = await _store_credential(
        _uid(user),
        connector,
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        api_token=body.api_token,
        expires_at=body.expires_at,
        metadata={**body.metadata, "source": "manual"},
    )
    return {"status": "connected", "credential": public_credential_doc(doc)}


@router.post("/{connector}/validate")
async def validate_connector(connector: str, user: dict = Depends(_get_auth())):
    if connector not in CONNECTOR_CATALOG:
        raise HTTPException(status_code=404, detail="Unknown connector")
    user_id = _uid(user)
    cred = await _credential_for(user_id, connector)
    token = None
    if cred:
        if cred.get("encrypted_api_token"):
            token = decrypt_secret(cred["encrypted_api_token"])
        elif cred.get("encrypted_access_token"):
            token = decrypt_secret(cred["encrypted_access_token"])
    elif connector == "notion" and os.environ.get("NOTION_API_KEY"):
        token = os.environ.get("NOTION_API_KEY")
    if not token:
        raise HTTPException(status_code=503, detail="Connector credentials are not configured")
    meta = CONNECTOR_CATALOG[connector]
    headers = {"Authorization": f"Bearer {token}"}
    if connector == "notion":
        headers["Notion-Version"] = "2022-06-28"
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(meta["validate_url"], headers=headers)
    ok = res.status_code < 400
    return {
        "connector": connector,
        "ok": ok,
        "status_code": res.status_code,
        "status": "available" if ok else "credential_invalid",
        "details": res.json() if ok else {"error": res.text[:500]},
    }
