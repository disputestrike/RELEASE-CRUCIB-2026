from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException


async def register_user_service(
    *,
    data: Any,
    request: Any,
    db: Any,
    audit_logger: Any,
    is_disposable_email: Callable[[str], bool],
    hash_password: Callable[[str], str],
    create_token: Callable[[str], str],
    apply_referral_on_signup: Callable[[str, Optional[str]], Awaitable[None]],
) -> dict:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready. Set DATABASE_URL in environment.")
    if is_disposable_email(data.email):
        raise HTTPException(status_code=400, detail="Disposable email addresses are not allowed.")
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "token_balance": 0,
        "credit_balance": 200,
        "plan": "free",
        "role": "owner",
        "mfa_enabled": False,
        "mfa_secret": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await apply_referral_on_signup(user_id, getattr(data, "ref", None))
    if audit_logger:
        await audit_logger.log(user_id, "signup", ip_address=getattr(request.client, "host", None))
    token = create_token(user_id)
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "_id")}}


async def login_user_service(
    *,
    data: Any,
    request: Any,
    db: Any,
    audit_logger: Any,
    verify_password: Callable[[str, str], bool],
    hash_password: Callable[[str], str],
    create_token: Callable[[str], str],
    create_mfa_temp_token: Callable[[str], str],
) -> dict:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready. Set DATABASE_URL in environment.")
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if len(user["password"]) == 64 and all(c in "0123456789abcdef" for c in user["password"].lower()):
        await db.users.update_one({"id": user["id"]}, {"$set": {"password": hash_password(data.password)}})
    ip = getattr(request.client, "host", None)
    if user.get("mfa_enabled") and user.get("mfa_secret"):
        if audit_logger:
            await audit_logger.log(user["id"], "login_password_verified", ip_address=ip)
        return {
            "status": "mfa_required",
            "mfa_required": True,
            "mfa_token": create_mfa_temp_token(user["id"]),
            "message": "Enter 6-digit code from your authenticator app",
        }
    token = create_token(user["id"])
    if audit_logger:
        await audit_logger.log(user["id"], "login", ip_address=ip)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


async def create_guest_user_service(
    *,
    request: Any,
    db: Any,
    create_token: Callable[[str], str],
    guest_tier_credits: int,
    credits_per_token: int,
) -> dict:
    if db is None:
        if os.environ.get("CRUCIBAI_DEV") == "1":
            from . import dev_guest

            return await dev_guest.create_guest_user(
                create_token=create_token,
                guest_tier_credits=guest_tier_credits,
                credits_per_token=credits_per_token,
            )
        raise HTTPException(status_code=503, detail="Database not ready")
    user_id = str(uuid.uuid4())
    email = f"guest-{user_id[:8]}@crucibai.guest"
    user = {
        "id": user_id,
        "email": email,
        "password": "",
        "name": "Guest",
        "token_balance": guest_tier_credits * credits_per_token,
        "credit_balance": guest_tier_credits,
        "plan": "free",
        "auth_provider": "guest",
        "workspace_mode": "simple",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.users.insert_one(user)
        await db.token_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tokens": guest_tier_credits * credits_per_token,
                "credits": guest_tier_credits,
                "type": "bonus",
                "description": "Guest session",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as _db_err:
        # Tables may not exist yet or DB is temporarily unavailable.
        # Issue a stateless guest token anyway — the user can still chat.
        import logging as _log
        _log.getLogger(__name__).warning(
            "Guest DB write failed (issuing stateless token): %s", _db_err
        )
    token = create_token(user["id"])
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "_id")}}


async def verify_mfa_login_service(
    *,
    body: Any,
    request: Any,
    db: Any,
    audit_logger: Any,
    decode_mfa_temp_token: Callable[[str], dict],
    create_token: Callable[[str], str],
    verify_totp: Callable[[str, str], bool],
) -> dict:
    try:
        payload = decode_mfa_temp_token(body.mfa_token)
        user_id = payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("mfa_enabled") or not user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    code = (body.code or "").strip().replace(" ", "")
    verified = verify_totp(user["mfa_secret"], code)
    if not verified:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup = await db.backup_codes.find_one({"user_id": user_id, "code_hash": code_hash, "used": False})
        if backup:
            lookup = {"_id": backup["_id"]} if backup.get("_id") is not None else {"user_id": user_id, "code_hash": code_hash, "used": False}
            await db.backup_codes.update_one(lookup, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
            verified = True
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid code")
    token = create_token(user_id)
    if audit_logger:
        await audit_logger.log(user_id, "login_mfa_verified", ip_address=getattr(request.client, "host", None))
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "mfa_secret", "_id")}}
