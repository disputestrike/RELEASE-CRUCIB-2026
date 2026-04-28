"""
Admin dashboard and operator APIs — require ``admin_role`` (see deps.ADMIN_ROLES).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_admin, get_documents_db_async

router = APIRouter(prefix="/api/admin", tags=["admin"])
_require_admin = get_current_admin()


def _parse_created_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _aggregate_user_metrics(db) -> dict[str, Any]:
    users_cursor = db.users.find({})
    rows = await users_cursor.to_list(100000)
    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_today - timedelta(days=7)

    signups_today = 0
    signups_week = 0
    for row in rows:
        dt = _parse_created_at(row.get("created_at"))
        if not dt:
            continue
        if dt >= start_today:
            signups_today += 1
        if dt >= start_week:
            signups_week += 1

    return {
        "total_users": len(rows),
        "signups_today": signups_today,
        "signups_week": signups_week,
        "revenue_today": 0.0,
        "revenue_week": 0.0,
        "revenue_month": 0.0,
    }


@router.get("/dashboard")
async def admin_dashboard(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    db = await get_documents_db_async()
    data = await _aggregate_user_metrics(db)
    return data


@router.get("/analytics/overview")
async def admin_analytics_overview(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    db = await get_documents_db_async()
    agg = await _aggregate_user_metrics(db)
    return {
        "total_users": agg["total_users"],
        "signups_today": agg["signups_today"],
        "signups_week": agg["signups_week"],
    }


@router.get("/users")
async def admin_users(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    db = await get_documents_db_async()
    cursor = db.users.find({})
    rows = await cursor.to_list(10_000)
    out = []
    for u in rows:
        if not isinstance(u, dict):
            continue
        out.append({k: v for k, v in u.items() if k not in ("password", "mfa_secret")})
    return {"users": out}


def _sanitize_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("password", "mfa_secret")}


@router.get("/users/{user_id}")
async def admin_user_profile(user_id: str, admin: dict = Depends(_require_admin)):  # noqa: ARG001
    db = await get_documents_db_async()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _sanitize_user(user)


@router.get("/billing/transactions")
async def admin_billing_transactions(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"transactions": []}


@router.get("/fraud/flags")
async def admin_fraud_flags(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"flags": []}


@router.get("/legal/blocked-requests")
async def admin_legal_blocked(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"blocked_requests": []}


@router.get("/referrals/links")
async def admin_referrals_links(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"links": []}


@router.get("/referrals/leaderboard")
async def admin_referrals_leaderboard(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"leaderboard": []}


@router.get("/segments")
async def admin_segments(admin: dict = Depends(_require_admin)):  # noqa: ARG001
    return {"segments": []}
