"""Shared FastAPI dependencies: database handle, audit logger, JWT auth.

Usage pattern
-------------
In *server.py* startup event::

    import deps
    deps.init(db=db_instance, audit_logger=audit_instance)

In route modules::

    from deps import get_db, get_audit_logger, get_current_user, get_current_admin

The ``init()`` call **must** happen before the first authenticated request arrives;
it is safe to call repeatedly (later calls overwrite the state).
"""

from __future__ import annotations

import os
import secrets
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# FIX: deps.get_db() always returned None (init() never called in production).
# _get_real_db() fetches a live PostgreSQL connection for every auth check.
async def _get_real_db():
    """Always returns a real PG-backed DB handle, or None on error."""
    try:
        from .db_pg import get_db as _pg
        return await _pg()
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Mutable shared state
# ---------------------------------------------------------------------------

_state: dict = {"db": None, "audit_logger": None}


def init(*, db=None, audit_logger=None) -> None:
    """Initialise shared state from server startup.  Called once per process."""
    if db is not None:
        _state["db"] = db
    if audit_logger is not None:
        _state["audit_logger"] = audit_logger


def get_db():
    """Return the live DB instance (None when DATABASE_URL is not configured)."""
    return _state["db"]


def get_audit_logger():
    """Return the audit-logger instance (may be None)."""
    return _state["audit_logger"]


# ---------------------------------------------------------------------------
# JWT / security constants
# ---------------------------------------------------------------------------

_raw_secret = os.environ.get("JWT_SECRET")
JWT_SECRET: str = _raw_secret if _raw_secret else secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)

# Admin user IDs granted owner-level access regardless of admin_role field.
ADMIN_USER_IDS: list[str] = [
    x.strip() for x in (os.environ.get("ADMIN_USER_IDS") or "").split(",") if x.strip()
]

# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = await _get_real_db()
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        uid = payload["user_id"]
        if db is None:
            if os.environ.get("CRUCIBAI_DEV") == "1":
                from services.dev_guest import get_user as _dev_get_user

                user = _dev_get_user(uid)
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                if user.get("suspended"):
                    raise HTTPException(status_code=403, detail="Account suspended")
                return user
            raise HTTPException(status_code=503, detail="Database not ready")
        user = await db.users.find_one({"id": uid}, {"_id": 0})
        if not user:
            # Stateless guest token — DB write failed silently at issue time.
            # Synthesize a minimal guest profile so the session stays alive.
            import re as _re
            if _re.match(r"^[0-9a-f-]{36}$", uid):
                user = {
                    "id": uid,
                    "email": f"guest-{uid[:8]}@crucibai.guest",
                    "name": "Guest",
                    "plan": "free",
                    "token_balance": 50_000,
                    "credit_balance": 50,
                    "auth_provider": "guest",
                    "workspace_mode": "simple",
                }
            else:
                raise HTTPException(status_code=401, detail="User not found")
        if user.get("suspended"):
            raise HTTPException(status_code=403, detail="Account suspended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_sse(
    access_token: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Same as ``get_current_user``; also accepts ``?access_token=`` for SSE
    clients that cannot set an Authorization header."""
    raw = None
    if credentials and credentials.credentials:
        raw = credentials.credentials
    elif access_token and str(access_token).strip():
        raw = str(access_token).strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = await _get_real_db()
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        uid = payload["user_id"]
        if db is None:
            if os.environ.get("CRUCIBAI_DEV") == "1":
                from services.dev_guest import get_user as _dev_get_user

                user = _dev_get_user(uid)
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                if user.get("suspended"):
                    raise HTTPException(status_code=403, detail="Account suspended")
                return user
            raise HTTPException(status_code=503, detail="Database not ready")
        user = await db.users.find_one({"id": uid}, {"_id": 0})
        if not user:
            import re as _re
            if _re.match(r"^[0-9a-f-]{36}$", uid):
                user = {
                    "id": uid,
                    "email": f"guest-{uid[:8]}@crucibai.guest",
                    "name": "Guest",
                    "plan": "free",
                    "token_balance": 50_000,
                    "credit_balance": 50,
                    "auth_provider": "guest",
                    "workspace_mode": "simple",
                }
            else:
                raise HTTPException(status_code=401, detail="User not found")
        if user.get("suspended"):
            raise HTTPException(status_code=403, detail="Account suspended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request=None,
) -> Optional[dict]:
    """Return the authenticated user, or ``None`` for public/unauthenticated access."""
    if credentials:
        db = await _get_real_db()
        try:
            payload = jwt.decode(
                credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
            )
            uid = payload["user_id"]
            if db is None:
                if os.environ.get("CRUCIBAI_DEV") == "1":
                    from services.dev_guest import get_user as _dev_get_user

                    user = _dev_get_user(uid)
                    if user:
                        return user
            else:
                user = await db.users.find_one({"id": uid}, {"_id": 0})
                if user:
                    return user
        except Exception:
            pass
    return None


def require_permission(permission):
    """RBAC FastAPI dependency: raise 403 if the user lacks *permission*."""

    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if permission is not None:
            try:
                from utils.rbac import has_permission

                if not has_permission(user, permission):
                    raise HTTPException(
                        status_code=403, detail="Insufficient permission"
                    )
            except ImportError:
                pass  # RBAC module absent — allow through
        return user

    return _dep


# ---------------------------------------------------------------------------
# Admin dependency
# ---------------------------------------------------------------------------

ADMIN_ROLES = ("owner", "operations", "support", "analyst")


def get_current_admin(required_roles: tuple = ADMIN_ROLES):
    """Return a FastAPI dependency that requires admin role membership."""

    async def _inner(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict:
        if not credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")
        db = await _get_real_db()
        try:
            payload = jwt.decode(
                credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
            )
            uid = payload["user_id"]
            if db is None:
                if os.environ.get("CRUCIBAI_DEV") == "1":
                    from services.dev_guest import get_user as _dev_get_user

                    user = _dev_get_user(uid)
                else:
                    user = None
            else:
                user = await db.users.find_one({"id": uid}, {"_id": 0})
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            if user.get("suspended"):
                raise HTTPException(status_code=403, detail="Account suspended")
            role = user.get("admin_role")
            if role and role in required_roles:
                return user
            if user["id"] in ADMIN_USER_IDS and "owner" in required_roles:
                return {**user, "admin_role": user.get("admin_role") or "owner"}
            raise HTTPException(status_code=403, detail="Admin access required")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")

    return _inner


async def get_user_credits(user: dict = Depends(get_current_user)) -> int:
    """Return the user's credit balance."""
    return int((user or {}).get("credit_balance", 0) or 0)


async def get_user_credits(user: dict = Depends(get_current_user)) -> int:
    """Return the user's credit balance."""
    return int((user or {}).get("credit_balance", 0) or 0)
