from __future__ import annotations

import base64
import hashlib
import io
import random
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import HTTPException


async def mfa_setup_service(*, request: Any, user: dict, db: Any, audit_logger: Any, random_base32: Callable[[], str], build_totp_uri: Callable[[str, str], str], qr_png_bytes: Callable[[str], bytes]) -> dict:
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1, "mfa_secret": 1})
    if u and u.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = random_base32()
    uri = build_totp_uri(secret, user.get("email") or user["id"])
    qr_b64 = base64.b64encode(qr_png_bytes(uri)).decode()
    await db.mfa_setup_temp.insert_one({"user_id": user["id"], "secret": secret, "created_at": datetime.now(timezone.utc), "verified": False})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_setup_started", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "qr_code": f"data:image/png;base64,{qr_b64}", "secret": secret}


async def mfa_verify_service(*, body: Any, request: Any, user: dict, db: Any, audit_logger: Any, verify_totp: Callable[[str, str], bool]) -> dict:
    temp = await db.mfa_setup_temp.find_one({"user_id": user["id"], "verified": False})
    if not temp:
        raise HTTPException(status_code=400, detail="No MFA setup in progress")
    code = (body.token or "").strip().replace(" ", "")
    if not verify_totp(temp["secret"], code):
        raise HTTPException(status_code=400, detail="Invalid code. Try again.")
    backup_codes = ["".join(random.choices("0123456789abcdef", k=8)) for _ in range(10)]
    for bc in backup_codes:
        await db.backup_codes.insert_one({"user_id": user["id"], "code_hash": hashlib.sha256(bc.encode()).hexdigest(), "used": False, "created_at": datetime.now(timezone.utc)})
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": True, "mfa_secret": temp["secret"], "mfa_enabled_at": datetime.now(timezone.utc)}})
    await db.mfa_setup_temp.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_enabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA enabled", "backup_codes": backup_codes}


async def mfa_disable_service(*, body: Any, request: Any, user: dict, db: Any, audit_logger: Any, verify_password: Callable[[str, str], bool]) -> dict:
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u or not verify_password(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": False, "mfa_secret": None}})
    await db.backup_codes.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_disabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA disabled"}


async def mfa_status_service(*, user: dict, db: Any) -> dict:
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1})
    enabled = bool((u or {}).get("mfa_enabled", False))
    return {"mfa_enabled": enabled, "status": "enabled" if enabled else "disabled"}


async def mfa_backup_code_use_service(*, body: Any, request: Any, user: dict, db: Any, audit_logger: Any) -> dict:
    code_hash = hashlib.sha256((body.code or "").strip().encode()).hexdigest()
    backup = await db.backup_codes.find_one({"user_id": user["id"], "code_hash": code_hash, "used": False})
    if not backup:
        raise HTTPException(status_code=400, detail="Invalid backup code")
    lookup = {"_id": backup["_id"]} if backup.get("_id") is not None else {"user_id": user["id"], "code_hash": code_hash, "used": False}
    await db.backup_codes.update_one(lookup, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
    if audit_logger:
        await audit_logger.log(user["id"], "backup_code_used", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "Backup code accepted"}
