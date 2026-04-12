"""
Authentication routes — real implementation extracted from server.py.
Handles user registration, login, guest access, MFA, OAuth (Google + GitHub),
audit logs, account management and user profile settings.
"""

import os
import logging
import uuid
import re
import json
import base64
import hashlib
import random
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from urllib.parse import quote, urlencode

import httpx
import jwt
import bcrypt
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from deps import (
    get_db,
    get_audit_logger,
    JWT_SECRET,
    JWT_ALGORITHM,
    get_current_user,
    get_optional_user,
    ADMIN_USER_IDS,
)

logger = logging.getLogger(__name__)

# auth_router uses prefix "/api"; route decorators already include "/auth/..." paths
auth_router = APIRouter(prefix="/api", tags=["auth"])

# ---------------------------------------------------------------------------
# Credit / tier constants (kept local to avoid circular imports)
# ---------------------------------------------------------------------------
try:
    from pricing_plans import CREDITS_PER_TOKEN
except ImportError:
    CREDITS_PER_TOKEN = 1000

FREE_TIER_CREDITS = 100
GUEST_TIER_CREDITS = 200

# ---------------------------------------------------------------------------
# Disposable-email block
# ---------------------------------------------------------------------------
DISPOSABLE_EMAIL_DOMAINS = frozenset([
    "10minutemail.com", "guerrillamail.com", "tempmail.com", "mailinator.com",
    "throwaway.email", "temp-mail.org", "fakeinbox.com", "trashmail.com", "yopmail.com",
])

def _is_disposable_email(email: str) -> bool:
    domain = (email or "").strip().split("@")[-1].lower()
    return domain in DISPOSABLE_EMAIL_DOMAINS

# ---------------------------------------------------------------------------
# Referral constants & helper
# ---------------------------------------------------------------------------
REFERRAL_CREDITS = 100
REFERRAL_CAP_PER_MONTH = 10
REFERRAL_EXPIRY_DAYS = 30

def _generate_referral_code() -> str:
    return "".join(random.choices("abcdefghjkmnpqrstuvwxyz23456789", k=8))

async def _apply_referral_on_signup(referee_id: str, ref_code: Optional[str] = None) -> None:
    """Grant 100 credits each when referee completes sign-up. Referrer reward only if on free plan. Cap 10/month."""
    db = get_db()
    if not ref_code or not ref_code.strip():
        return
    ref_code = ref_code.strip().lower()
    ref_row = await db.referral_codes.find_one({"code": ref_code})
    if not ref_row:
        return
    referrer_id = ref_row.get("user_id")
    if not referrer_id or referrer_id == referee_id:
        return
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.referrals.count_documents({"referrer_id": referrer_id, "signup_completed_at": {"$gte": month_start.isoformat()}})
    if count >= REFERRAL_CAP_PER_MONTH:
        return
    referrer_doc = await db.users.find_one({"id": referrer_id}, {"plan": 1})
    referrer_plan = (referrer_doc or {}).get("plan") or "free"
    reward_referrer = referrer_plan == "free"
    expiry_at = (now + timedelta(days=REFERRAL_EXPIRY_DAYS)).isoformat()
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()),
        "referrer_id": referrer_id,
        "referee_id": referee_id,
        "status": "completed",
        "signup_completed_at": now.isoformat(),
        "referrer_rewarded_at": now.isoformat(),
        "created_at": now.isoformat(),
    })
    to_grant = [(referee_id, "Referral (referee)")]
    if reward_referrer:
        to_grant.append((referrer_id, "Referral (referrer)"))
    for uid, desc in to_grant:
        await db.users.update_one({"id": uid}, {"$inc": {"credit_balance": REFERRAL_CREDITS}})
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "credits": REFERRAL_CREDITS,
            "type": "referral",
            "description": desc,
            "credit_expires_at": expiry_at,
            "created_at": now.isoformat(),
        })
    logger.info(
        "Referral: granted %d to referee %s%s",
        REFERRAL_CREDITS, referee_id,
        f" and referrer {referrer_id} (free tier)" if reward_referrer else " (referrer not on free tier, no referrer reward)",
    )

# ---------------------------------------------------------------------------
# Password / token helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        if bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8")):
            return True
    except (ValueError, TypeError) as e:
        logger.debug(f"Bcrypt verification failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during password verification: {e}")
    # Legacy: SHA-256 hashes (64-char hex) — DEPRECATED
    if len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed.lower()):
        logger.warning("SECURITY: SHA-256 password hash detected. Please migrate to bcrypt by 2026-06-01.")
        return hashlib.sha256(plain.encode()).hexdigest() == hashed
    return False

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _mfa_temp_token_payload(user_id: str) -> dict:
    return {"user_id": user_id, "purpose": "mfa_verification", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}

def create_mfa_temp_token(user_id: str) -> str:
    return jwt.encode(_mfa_temp_token_payload(user_id), JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_mfa_temp_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "mfa_verification":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload

# ---------------------------------------------------------------------------
# Credit helpers
# ---------------------------------------------------------------------------

def _user_credits(user: Optional[dict]) -> int:
    if not user:
        return 0
    if user.get("credit_balance") is not None:
        return int(user["credit_balance"])
    return int((user.get("token_balance") or 0) // CREDITS_PER_TOKEN)

async def _ensure_credit_balance(user_id: str) -> None:
    db = get_db()
    doc = await db.users.find_one({"id": user_id}, {"credit_balance": 1, "token_balance": 1})
    if not doc or doc.get("credit_balance") is not None:
        return
    cred = (doc.get("token_balance") or 0) // CREDITS_PER_TOKEN
    await db.users.update_one({"id": user_id}, {"$set": {"credit_balance": cred}})

# ---------------------------------------------------------------------------
# OAuth constants
# ---------------------------------------------------------------------------
# Google OAuth: CrucibAI's own flow only (docs/GOOGLE_AUTH_SETUP.md).
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

_raw_frontend_url = os.environ.get("FRONTEND_URL", "").strip()
if _raw_frontend_url and not _raw_frontend_url.startswith("http://localhost"):
    if not _raw_frontend_url.startswith(("http://", "https://")):
        _raw_frontend_url = f"https://{_raw_frontend_url}"
    if _raw_frontend_url.startswith("http://") and ("railway" in _raw_frontend_url or "up.railway" in _raw_frontend_url):
        _raw_frontend_url = _raw_frontend_url.replace("http://", "https://", 1)
    FRONTEND_URL = _raw_frontend_url
else:
    FRONTEND_URL = ""

GOOGLE_REDIRECT_URI = (os.environ.get("GOOGLE_REDIRECT_URI") or "").strip().rstrip("/")

logger.info("Google OAuth Config - FRONTEND_URL: %s", FRONTEND_URL or "(use request host at redirect)")
logger.info("Google OAuth Config - GOOGLE_CLIENT_ID: %s", (GOOGLE_CLIENT_ID[:20] + "...") if GOOGLE_CLIENT_ID else "GOOGLE_CLIENT_ID not set")
logger.info("Google OAuth Config - GOOGLE_CLIENT_SECRET: %s", "SET" if GOOGLE_CLIENT_SECRET else "NOT SET")
logger.info("Google OAuth Config - GOOGLE_REDIRECT_URI: %s", GOOGLE_REDIRECT_URI or "(derive from BACKEND_PUBLIC_URL or request)")

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_REDIRECT_URI = (os.environ.get("GITHUB_REDIRECT_URI") or "").strip().rstrip("/")
logger.info("GitHub OAuth Config - GITHUB_CLIENT_ID: %s", (GITHUB_CLIENT_ID[:16] + "...") if GITHUB_CLIENT_ID else "not set")
logger.info("GitHub OAuth Config - GITHUB_CLIENT_SECRET: %s", "SET" if GITHUB_CLIENT_SECRET else "NOT SET")

# ---------------------------------------------------------------------------
# OAuth helper functions
# ---------------------------------------------------------------------------

def _backend_base_for_oauth(request: Request) -> str:
    """Prefer HTTPS for OAuth callback when behind a TLS proxy (e.g. Railway)."""
    base = os.environ.get("BACKEND_PUBLIC_URL", "").strip().rstrip("/")
    if base:
        return base
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").strip().lower()
    host = request.headers.get("x-forwarded-host") or request.url.netloc or "localhost:8000"
    return f"{proto}://{host}".rstrip("/")

def _oauth_callback_url(request: Request) -> str:
    """Exact redirect_uri to send to Google. Use GOOGLE_REDIRECT_URI if set, else derive from backend base."""
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    base = _backend_base_for_oauth(request)
    return f"{base}/api/auth/google/callback"

def _github_oauth_callback_url(request: Request) -> str:
    if GITHUB_REDIRECT_URI:
        return GITHUB_REDIRECT_URI
    base = _backend_base_for_oauth(request)
    return f"{base}/api/auth/github/callback"

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    ref: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MFAVerifyLogin(BaseModel):
    code: str
    mfa_token: str

class WorkspaceModeBody(BaseModel):
    mode: str  # "simple" or "developer"

class MFAVerifyBody(BaseModel):
    token: str  # 6-digit code

class MFADisableBody(BaseModel):
    password: str

class BackupCodeBody(BaseModel):
    code: str

class DeleteAccountBody(BaseModel):
    password: str

class ChangePasswordBody(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

class NotificationPrefs(BaseModel):
    email_builds: Optional[bool] = None
    email_billing: Optional[bool] = None
    email_marketing: Optional[bool] = None
    in_app_builds: Optional[bool] = None
    in_app_tips: Optional[bool] = None

class PrivacyPrefs(BaseModel):
    allow_analytics: Optional[bool] = None
    allow_training: Optional[bool] = None
    public_profile: Optional[bool] = None

class UpdateProfileBody(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=2048)

# ---------------------------------------------------------------------------
# Routes: register / login / guest / MFA login
# ---------------------------------------------------------------------------

@auth_router.post("/auth/register")
@auth_router.post("/auth/signup")  # Alias for compatibility
async def register(data: UserRegister, request: Request):
    db = get_db()
    audit_logger = get_audit_logger()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready. Set DATABASE_URL in environment.")
    if _is_disposable_email(data.email):
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
    await _apply_referral_on_signup(user_id, getattr(data, "ref", None))
    if audit_logger:
        await audit_logger.log(user_id, "signup", ip_address=getattr(request.client, "host", None))
    token = create_token(user_id)
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "_id")}}


@auth_router.post("/auth/login")
async def login(data: UserLogin, request: Request):
    db = get_db()
    audit_logger = get_audit_logger()
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
        mfa_token = create_mfa_temp_token(user["id"])
        return {
            "status": "mfa_required",
            "mfa_required": True,
            "mfa_token": mfa_token,
            "message": "Enter 6-digit code from your authenticator app",
        }
    token = create_token(user["id"])
    if audit_logger:
        await audit_logger.log(user["id"], "login", ip_address=ip)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


@auth_router.post("/auth/guest")
async def auth_guest(request: Request):
    """Create a guest user and return token so the app can be used without sign-up."""
    db = get_db()
    if db is None:
        logger.warning("POST /auth/guest called but db not initialized (DATABASE_URL or startup failed)")
        raise HTTPException(status_code=503, detail="Database not ready")
    user_id = str(uuid.uuid4())
    email = f"guest-{user_id[:8]}@crucibai.guest"
    guest_credits = GUEST_TIER_CREDITS
    user = {
        "id": user_id,
        "email": email,
        "password": "",
        "name": "Guest",
        "token_balance": guest_credits * CREDITS_PER_TOKEN,
        "credit_balance": guest_credits,
        "plan": "free",
        "auth_provider": "guest",
        "workspace_mode": "simple",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tokens": guest_credits * CREDITS_PER_TOKEN,
        "credits": guest_credits,
        "type": "bonus",
        "description": "Guest session",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = create_token(user["id"])
    u = {k: v for k, v in user.items() if k not in ("password", "_id")}
    return {"token": token, "user": u}


@auth_router.post("/auth/verify-mfa")
async def verify_mfa_login(body: MFAVerifyLogin, request: Request):
    db = get_db()
    audit_logger = get_audit_logger()
    try:
        payload = decode_mfa_temp_token(body.mfa_token)
        user_id = payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("mfa_enabled") or not user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    code = (body.code or "").strip().replace(" ", "")
    verified = False
    if pyotp.TOTP(user["mfa_secret"]).verify(code, valid_window=1):
        verified = True
    if not verified:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup = await db.backup_codes.find_one({"user_id": user_id, "code_hash": code_hash, "used": False})
        if backup:
            await db.backup_codes.update_one({"_id": backup["_id"]}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
            verified = True
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid code")
    token = create_token(user_id)
    if audit_logger:
        await audit_logger.log(user_id, "login_mfa_verified", ip_address=getattr(request.client, "host", None))
    u = {k: v for k, v in user.items() if k not in ("password", "mfa_secret", "_id")}
    return {"token": token, "user": u}


@auth_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    db = get_db()
    await _ensure_credit_balance(user["id"])
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    guest_credits_low = (u.get("credit_balance") or 0) < 100
    if u.get("auth_provider") == "guest" and guest_credits_low:
        await db.users.update_one(
            {"id": u["id"]},
            {"$set": {"credit_balance": GUEST_TIER_CREDITS, "token_balance": GUEST_TIER_CREDITS * CREDITS_PER_TOKEN}},
        )
        u["credit_balance"] = GUEST_TIER_CREDITS
        u["token_balance"] = GUEST_TIER_CREDITS * CREDITS_PER_TOKEN
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}})
    u["credit_balance"] = _user_credits(u)
    if u["id"] in ADMIN_USER_IDS and not u.get("admin_role"):
        u["admin_role"] = "owner"
    u.pop("password", None)
    u.pop("mfa_secret", None)
    u.pop("deploy_tokens", None)
    u.setdefault("workspace_mode", None)
    return u


@auth_router.post("/user/workspace-mode")
@auth_router.post("/users/me/workspace-mode")  # alias for compatibility
async def set_workspace_mode(body: WorkspaceModeBody, user: dict = Depends(get_current_user)):
    db = get_db()
    if body.mode not in ("simple", "developer"):
        raise HTTPException(status_code=400, detail="mode must be 'simple' or 'developer'")
    await db.users.update_one({"id": user["id"]}, {"$set": {"workspace_mode": body.mode}})
    return {"status": "success", "workspace_mode": body.mode}


# ---------------------------------------------------------------------------
# MFA routes
# ---------------------------------------------------------------------------

@auth_router.post("/mfa/setup")
async def mfa_setup(request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    audit_logger = get_audit_logger()
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1, "mfa_secret": 1})
    if u and u.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.get("email") or user["id"], issuer_name="CrucibAI")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    await db.mfa_setup_temp.insert_one({
        "user_id": user["id"],
        "secret": secret,
        "created_at": datetime.now(timezone.utc),
        "verified": False,
    })
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_setup_started", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "qr_code": f"data:image/png;base64,{qr_b64}", "secret": secret}


@auth_router.post("/mfa/verify")
async def mfa_verify(body: MFAVerifyBody, request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    audit_logger = get_audit_logger()
    temp = await db.mfa_setup_temp.find_one({"user_id": user["id"], "verified": False})
    if not temp:
        raise HTTPException(status_code=400, detail="No MFA setup in progress")
    code = (body.token or "").strip().replace(" ", "")
    if not pyotp.TOTP(temp["secret"]).verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code. Try again.")
    backup_codes = ["".join(random.choices("0123456789abcdef", k=8)) for _ in range(10)]
    for bc in backup_codes:
        await db.backup_codes.insert_one({
            "user_id": user["id"],
            "code_hash": hashlib.sha256(bc.encode()).hexdigest(),
            "used": False,
            "created_at": datetime.now(timezone.utc),
        })
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"mfa_enabled": True, "mfa_secret": temp["secret"], "mfa_enabled_at": datetime.now(timezone.utc)}},
    )
    await db.mfa_setup_temp.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_enabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA enabled", "backup_codes": backup_codes}


@auth_router.post("/mfa/disable")
async def mfa_disable(body: MFADisableBody, request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    audit_logger = get_audit_logger()
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u or not verify_password(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": False, "mfa_secret": None}})
    await db.backup_codes.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_disabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA disabled"}


@auth_router.get("/mfa/status")
async def mfa_status(user: dict = Depends(get_current_user)):
    db = get_db()
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1})
    return {"mfa_enabled": u.get("mfa_enabled", False), "status": "enabled" if u.get("mfa_enabled") else "disabled"}


@auth_router.post("/mfa/backup-code/use")
async def mfa_backup_code_use(body: BackupCodeBody, request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    audit_logger = get_audit_logger()
    code_hash = hashlib.sha256((body.code or "").strip().encode()).hexdigest()
    backup = await db.backup_codes.find_one({"user_id": user["id"], "code_hash": code_hash, "used": False})
    if not backup:
        raise HTTPException(status_code=400, detail="Invalid backup code")
    await db.backup_codes.update_one({"_id": backup["_id"]}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
    if audit_logger:
        await audit_logger.log(user["id"], "backup_code_used", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "Backup code accepted"}


# ---------------------------------------------------------------------------
# Audit log routes
# ---------------------------------------------------------------------------

@auth_router.get("/audit/logs")
async def get_audit_logs(
    user: dict = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    action: Optional[str] = None,
):
    """Get current user's audit logs."""
    audit_logger = get_audit_logger()
    if not audit_logger:
        return {"logs": [], "total": 0, "limit": limit, "skip": skip}
    return await audit_logger.get_user_logs(user["id"], limit=limit, skip=skip, action_filter=action)


@auth_router.get("/audit/logs/export")
async def export_audit_logs(
    user: dict = Depends(get_current_user),
    start_date: str = Query(...),
    end_date: str = Query(...),
    format: str = Query("json", enum=["json", "csv"]),
):
    """Export audit logs for compliance (date format YYYY-MM-DD)."""
    audit_logger = get_audit_logger()
    if not audit_logger:
        raise HTTPException(status_code=503, detail="Audit log not available")
    try:
        start = datetime.strptime(start_date.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date.strip()[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    result = await audit_logger.export_logs(user["id"], start, end, format=format)
    if format == "json":
        return Response(content=result, media_type="application/json")
    return Response(
        content=result,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit-log-{start_date}-{end_date}.csv"},
    )


# ---------------------------------------------------------------------------
# Account management routes
# ---------------------------------------------------------------------------

@auth_router.post("/users/me/delete")
async def delete_account(body: DeleteAccountBody, user: dict = Depends(get_current_user)):
    """Permanently delete the current user's account and all associated data. Requires password confirmation."""
    db = get_db()
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
    await db.workspace_env.delete_many({"user_id": uid})
    await db.chat_history.delete_many({"user_id": uid})
    await db.token_ledger.delete_many({"user_id": uid})
    await db.shares.delete_many({"user_id": uid})
    await db.user_agents.delete_many({"user_id": uid})
    await db.backup_codes.delete_many({"user_id": uid})
    await db.mfa_setup_temp.delete_many({"user_id": uid})
    await db.users.delete_one({"id": uid})
    return Response(status_code=204)


@auth_router.post("/users/me/change-password")
async def change_password(body: ChangePasswordBody, user: dict = Depends(get_current_user)):
    """Change the current user's password. Requires current password for verification."""
    db = get_db()
    audit_logger = get_audit_logger()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not u.get("password"):
        raise HTTPException(status_code=400, detail="Cannot change password for social/guest accounts")
    if not verify_password(body.current_password, u["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    pw = body.new_password
    if not any(c.isupper() for c in pw):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.islower() for c in pw):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in pw):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in pw):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")
    hashed = hash_password(pw)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password": hashed, "password_changed_at": datetime.now(timezone.utc).isoformat()}},
    )
    if audit_logger:
        await audit_logger.log(user["id"], "password_changed")
    return {"status": "success", "message": "Password changed successfully"}


@auth_router.patch("/users/me")
@auth_router.patch("/user/me")
async def update_profile(body: UpdateProfileBody, user: dict = Depends(get_current_user)):
    """Update user profile (name, email, bio, avatar_url)."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
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


@auth_router.patch("/users/me/notifications")
async def update_notification_prefs(body: NotificationPrefs, user: dict = Depends(get_current_user)):
    """Save notification preferences for the current user."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    updates = {f"notifications.{k}": v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"status": "success", "message": "Notification preferences saved"}


@auth_router.patch("/users/me/privacy")
async def update_privacy_prefs(body: PrivacyPrefs, user: dict = Depends(get_current_user)):
    """Save privacy preferences for the current user."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    updates = {f"privacy.{k}": v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"status": "success", "message": "Privacy preferences saved"}


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------

@auth_router.get("/auth/google")
async def auth_google_redirect(request: Request, redirect: Optional[str] = None):
    """Redirect user to Google OAuth consent screen."""
    callback = _oauth_callback_url(request)
    if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID.startswith("123456"):
        state = json.dumps({"redirect": redirect or ""}) if redirect else ""
        import base64 as b64
        state_param = b64.urlsafe_b64encode(state.encode()).decode() if state else ""
        mock_consent_url = f"{callback}?code=mock_auth_code_test&state={state_param}"
        return RedirectResponse(url=mock_consent_url)
    state = json.dumps({"redirect": redirect or ""}) if redirect else ""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": callback,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        import base64 as b64
        params["state"] = b64.urlsafe_b64encode(state.encode()).decode()
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@auth_router.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """Exchange Google code for tokens, create or find user, redirect to frontend with JWT.
    Uses only CrucibAI flow per docs/GOOGLE_AUTH_SETUP.md: one token exchange, verify with google-auth, redirect to FRONTEND_URL."""
    db = get_db()
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost"):
        frontend_base = FRONTEND_URL.rstrip("/")
    else:
        frontend_base = _backend_base_for_oauth(request).rstrip("/")
    if not code:
        logger.info("Google callback: no code, redirecting to auth?error=no_code")
        return RedirectResponse(url=f"{frontend_base}/auth?error=no_code")

    if code == "mock_auth_code_test":
        import time
        email = f"test.user.{int(time.time())}@crucibai.test"
        name = "Test User (Mock OAuth)"
        payload = {"email": email, "name": name}
    else:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="Google sign-in is not configured")
        callback = _oauth_callback_url(request)
        logger.info(
            "Google callback: exchanging code (redirect_uri=%s). Add this exact URL to Google Cloud Console > Credentials > Authorized redirect URIs if you see redirect_uri_mismatch.",
            callback,
        )
        async with __import__("httpx").AsyncClient() as client:
            r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if r.status_code != 200:
            try:
                err_body = r.json()
                err_code = err_body.get("error", "")
                err_desc = err_body.get("error_description", r.text[:300])
            except Exception:
                err_code = ""
                err_desc = r.text[:300]
            logger.warning(
                "Google token exchange failed: status=%s error=%s description=%s. Callback used: %s",
                r.status_code, err_code, err_desc, callback,
            )
            return RedirectResponse(url=f"{frontend_base}/auth?error=google_failed")
        data = r.json()
        id_token = data.get("id_token") or data.get("access_token")
        if not id_token:
            logger.info("Google callback: no id_token in response, redirecting to auth?error=no_token")
            return RedirectResponse(url=f"{frontend_base}/auth?error=no_token")
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            payload = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), GOOGLE_CLIENT_ID
            )
        except Exception as e:
            logger.warning(f"Google ID token verification failed: {e}")
            return RedirectResponse(url=f"{frontend_base}/auth?error=google_verify_failed")
        email = (payload.get("email") or "").strip()
    name = (payload.get("name") or payload.get("given_name") or email.split("@")[0] or "User").strip()
    if not email:
        logger.info("Google callback: no email in payload, redirecting to auth?error=no_email")
        return RedirectResponse(url=f"{frontend_base}/auth?error=no_email")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password": "",
            "name": name,
            "token_balance": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credit_balance": FREE_TIER_CREDITS,
            "plan": "free",
            "auth_provider": "google",
            "workspace_mode": "simple",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tokens": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credits": FREE_TIER_CREDITS,
            "type": "bonus",
            "description": "Welcome (Free tier)",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        if not user.get("workspace_mode"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"workspace_mode": "simple"}})
            user["workspace_mode"] = "simple"
    token = create_token(user["id"])
    redirect_path = ""
    if state:
        try:
            import base64 as b64
            decoded = b64.urlsafe_b64decode(state.encode()).decode()
            obj = json.loads(decoded)
            redirect_path = obj.get("redirect") or ""
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError) as e:
            logger.debug(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
    target = f"{frontend_base}/auth?token={token}"
    if redirect_path and redirect_path.startswith("/"):
        target += f"&redirect={quote(redirect_path)}"
    logger.info("Google callback: success, redirecting to frontend with token (user_id=%s)", user.get("id", ""))
    return RedirectResponse(url=target)


# ---------------------------------------------------------------------------
# GitHub OAuth routes
# ---------------------------------------------------------------------------

@auth_router.get("/auth/github")
async def auth_github_redirect(request: Request, redirect: Optional[str] = None):
    """GitHub OAuth: authorize URL; callback must match GitHub OAuth App settings."""
    callback = _github_oauth_callback_url(request)
    if not GITHUB_CLIENT_ID or GITHUB_CLIENT_ID.lower().startswith("mock"):
        import base64 as b64
        state_raw = json.dumps({"redirect": redirect or ""}) if redirect else ""
        state_param = b64.urlsafe_b64encode(state_raw.encode()).decode() if state_raw else ""
        return RedirectResponse(url=f"{callback}?code=mock_github_auth_test&state={state_param}")
    import base64 as b64
    state_raw = json.dumps({"redirect": redirect or ""}) if redirect else ""
    state_param = b64.urlsafe_b64encode(state_raw.encode()).decode() if state_raw else ""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": callback,
        "scope": "read:user user:email",
        "allow_signup": "true",
    }
    if state_param:
        params["state"] = state_param
    return RedirectResponse(url=f"https://github.com/login/oauth/authorize?{urlencode(params)}")


@auth_router.get("/auth/github/callback")
async def auth_github_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Exchange GitHub OAuth code, create/find user, redirect to frontend with JWT."""
    db = get_db()
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost"):
        frontend_base = FRONTEND_URL.rstrip("/")
    else:
        frontend_base = _backend_base_for_oauth(request).rstrip("/")
    if error:
        logger.info("GitHub callback error=%s desc=%s", error, (error_description or "")[:200])
        return RedirectResponse(url=f"{frontend_base}/auth?error=github_{error}")
    if not code:
        return RedirectResponse(url=f"{frontend_base}/auth?error=no_code")
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")

    if code == "mock_github_auth_test":
        import time
        email = f"github.test.{int(time.time())}@crucibai.test"
        name = "Test User (GitHub Mock)"
    else:
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            return RedirectResponse(url=f"{frontend_base}/auth?error=github_not_configured")
        cb = _github_oauth_callback_url(request)
        async with httpx.AsyncClient(timeout=30.0) as client:
            tr = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": cb,
                },
                headers={"Accept": "application/json"},
            )
        if tr.status_code != 200:
            logger.warning("GitHub token exchange failed: %s %s", tr.status_code, tr.text[:300])
            return RedirectResponse(url=f"{frontend_base}/auth?error=github_token_failed")
        tok = tr.json()
        access_token = tok.get("access_token")
        if not access_token:
            return RedirectResponse(url=f"{frontend_base}/auth?error=github_no_access_token")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            ur = await client.get("https://api.github.com/user", headers=headers)
        if ur.status_code != 200:
            logger.warning("GitHub user fetch failed: %s", ur.text[:300])
            return RedirectResponse(url=f"{frontend_base}/auth?error=github_user_failed")
        gh = ur.json()
        name = (gh.get("name") or gh.get("login") or "GitHub User").strip()
        email = (gh.get("email") or "").strip()
        if not email:
            async with httpx.AsyncClient(timeout=30.0) as client:
                er = await client.get("https://api.github.com/user/emails", headers=headers)
            if er.status_code == 200:
                for row in er.json():
                    if row.get("primary") and row.get("email"):
                        email = row["email"].strip()
                        break
                    if row.get("verified") and row.get("email"):
                        email = row["email"].strip()
                        break
        if not email:
            return RedirectResponse(url=f"{frontend_base}/auth?error=github_no_email")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password": "",
            "name": name,
            "token_balance": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credit_balance": FREE_TIER_CREDITS,
            "plan": "free",
            "auth_provider": "github",
            "workspace_mode": "simple",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tokens": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credits": FREE_TIER_CREDITS,
            "type": "bonus",
            "description": "Welcome (Free tier)",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        if not user.get("workspace_mode"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"workspace_mode": "simple"}})
            user["workspace_mode"] = "simple"
        await db.users.update_one({"id": user["id"]}, {"$set": {"auth_provider": "github"}})

    token = create_token(user["id"])
    redirect_path = ""
    if state:
        try:
            import base64 as b64
            decoded = b64.urlsafe_b64decode(state.encode()).decode()
            obj = json.loads(decoded)
            redirect_path = obj.get("redirect") or ""
        except Exception as e:
            logger.debug("GitHub callback state decode: %s", e)
    target = f"{frontend_base}/auth?token={token}"
    if redirect_path and redirect_path.startswith("/"):
        target += f"&redirect={quote(redirect_path)}"
    logger.info("GitHub callback: success redirect (user_id=%s)", user.get("id", ""))
    return RedirectResponse(url=target)


__all__ = ["auth_router"]
