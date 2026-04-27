from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import HTTPException
from fastapi.responses import Response


async def get_me_service(*, user: dict, db: Any, ensure_credit_balance, user_credits, admin_user_ids, guest_tier_credits: int, credits_per_token: int) -> dict:
    if db is None:
        if os.environ.get("CRUCIBAI_DEV") == "1":
            from backend.services.dev_guest import get_user as _dev_get_user

            u = _dev_get_user(user["id"])
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            u = dict(u)
            u["credit_balance"] = user_credits(u)
            if u["id"] in admin_user_ids and not u.get("admin_role"):
                u["admin_role"] = "owner"
            for key in ("password", "mfa_secret", "deploy_tokens"):
                u.pop(key, None)
            u.setdefault("workspace_mode", None)
            return u
        raise HTTPException(status_code=503, detail="Database not ready")
    await ensure_credit_balance(user["id"])
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    guest_credits_low = (u.get("credit_balance") or 0) < 100
    if u.get("auth_provider") == "guest" and guest_credits_low:
        await db.users.update_one({"id": u["id"]}, {"$set": {"credit_balance": guest_tier_credits, "token_balance": guest_tier_credits * credits_per_token}})
        u["credit_balance"] = guest_tier_credits
        u["token_balance"] = guest_tier_credits * credits_per_token
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}})
    u["credit_balance"] = user_credits(u)
    if u["id"] in admin_user_ids and not u.get("admin_role"):
        u["admin_role"] = "owner"
    for key in ("password", "mfa_secret", "deploy_tokens"):
        u.pop(key, None)
    u.setdefault("workspace_mode", None)
    return u


async def set_workspace_mode_service(*, body: Any, user: dict, db: Any) -> dict:
    if body.mode not in ("simple", "developer"):
        raise HTTPException(status_code=400, detail="mode must be 'simple' or 'developer'")
    if db is None:
        if os.environ.get("CRUCIBAI_DEV") == "1":
            from backend.services.dev_guest import update_user as _dev_update_user

            if not _dev_update_user(user["id"], {"workspace_mode": body.mode}):
                raise HTTPException(status_code=404, detail="User not found")
            return {"status": "success", "workspace_mode": body.mode}
        raise HTTPException(status_code=503, detail="Database not ready")
    await db.users.update_one({"id": user["id"]}, {"$set": {"workspace_mode": body.mode}})
    return {"status": "success", "workspace_mode": body.mode}


async def delete_account_service(*, body: Any, user: dict, db: Any, verify_password: Callable[[str, str], bool]) -> Response:
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u or not verify_password(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    uid = user["id"]
    projects = await db.projects.find({"user_id": uid}, {"id": 1}).to_list(500)
    for p in projects:
        pid = p["id"]
        await db.project_logs.delete_many({"project_id": pid})
        await db.agent_status.delete_many({"project_id": pid})
        await db.shares.delete_many({"project_id": pid})
    await db.projects.delete_many({"user_id": uid})
    for coll in [db.workspace_env, db.chat_history, db.token_ledger, db.shares, db.user_agents, db.backup_codes, db.mfa_setup_temp]:
        await coll.delete_many({"user_id": uid})
    await db.users.delete_one({"id": uid})
    return Response(status_code=204)


async def change_password_service(*, body: Any, user: dict, db: Any, audit_logger: Any, verify_password: Callable[[str, str], bool], hash_password: Callable[[str], str]) -> dict:
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not u.get("password"):
        raise HTTPException(status_code=400, detail="Cannot change password for social/guest accounts")
    if not verify_password(body.current_password, u["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    pw = body.new_password
    checks = [
        (any(c.isupper() for c in pw), "Password must contain at least one uppercase letter"),
        (any(c.islower() for c in pw), "Password must contain at least one lowercase letter"),
        (any(c.isdigit() for c in pw), "Password must contain at least one number"),
        (any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw), "Password must contain at least one special character"),
    ]
    for ok, detail in checks:
        if not ok:
            raise HTTPException(status_code=400, detail=detail)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password": hash_password(pw), "password_changed_at": datetime.now(timezone.utc).isoformat()}})
    if audit_logger:
        await audit_logger.log(user["id"], "password_changed")
    return {"status": "success", "message": "Password changed successfully"}


async def update_profile_service(*, body: Any, user: dict, db: Any) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    if "email" in updates:
        existing = await db.users.find_one({"email": updates["email"]})
        if existing and existing["id"] != user["id"]:
            raise HTTPException(status_code=400, detail="Email already in use")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    u.pop("password", None)
    u.pop("mfa_secret", None)
    return {"status": "success", "user": u}


async def update_notification_prefs_service(*, body: Any, user: dict, db: Any) -> dict:
    updates = {f"notifications.{k}": v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"status": "success", "message": "Notification preferences saved"}


async def update_privacy_prefs_service(*, body: Any, user: dict, db: Any) -> dict:
    updates = {f"privacy.{k}": v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"status": "success", "message": "Privacy preferences saved"}
