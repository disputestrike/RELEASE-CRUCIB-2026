"""Admin routes — extracted from server.py.

Registers an ``admin_router`` (prefix ``/api``) that server.py includes via
``app.include_router(admin_router)``.

All DB access goes through ``deps.get_db()``; all audit logging through
``deps.get_audit_logger()``.  Both are populated at startup by
``deps.init(db=..., audit_logger=...)``.
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from deps import (
    ADMIN_USER_IDS,
    get_audit_logger,
    get_current_user,
    get_db,
)
from deps import ADMIN_ROLES, get_current_admin  # noqa: F401 (re-exported)
from pricing_plans import TOKEN_BUNDLES

# ── Constants ────────────────────────────────────────────────────────────────
SUPPORT_GRANT_CAP_PER_MONTH = 50  # max credits support can grant per user per month
MAX_TOKEN_LEDGER_REVENUE = 5000
MAX_ADMIN_USER_EXPORT_PROJECTS = 1000
MAX_ADMIN_USER_LEDGER = 1000

admin_router = APIRouter(prefix="/api", tags=["admin"])


# ── Models ───────────────────────────────────────────────────────────────────

class GrantCreditsBody(BaseModel):
    credits: int = Field(gt=0, description="Credits to grant (must be positive)")
    reason: Optional[str] = "Support bonus"


class SuspendBody(BaseModel):
    reason: str


class AdminNotificationBody(BaseModel):
    target: Optional[str] = "all"
    subject: str
    body: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_credits(user: Optional[dict]) -> int:
    """Credits available: credit_balance if set, else token_balance // 1000."""
    if not user:
        return 0
    if user.get("credit_balance") is not None:
        return int(user["credit_balance"])
    return int((user.get("token_balance") or 0) // 1000)


async def _revenue_for_query(q: dict) -> float:
    db = get_db()
    rows = await db.token_ledger.find(q).to_list(MAX_TOKEN_LEDGER_REVENUE)
    total = 0.0
    for r in rows:
        p = r.get("price")
        if p is not None:
            total += float(p)
        else:
            total += float(TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0))
    return round(total, 2)


def _parse_date(s: Optional[str]):
    """Parse YYYY-MM-DD to date.  Return None if invalid."""
    if not s or len(s) < 10:
        return None
    try:
        from datetime import date as date_type
        return date_type(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None


# ── Routes ───────────────────────────────────────────────────────────────────

@admin_router.get("/admin/dashboard")
async def admin_dashboard(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    """Overview: users, revenue, signups, referral count, health."""
    db = get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()[:10]
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    total_users = await db.users.count_documents({})
    signups_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    signups_week = await db.users.count_documents({"created_at": {"$gte": week_ago}})
    referral_count = await db.referrals.count_documents({}) if hasattr(db, "referrals") else 0
    projects_today = await db.projects.count_documents({"created_at": {"$gte": today_start}})
    revenue_today = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": today_start}})
    revenue_week = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": week_ago}})
    revenue_month = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": month_ago}})
    return {
        "users_online": total_users,
        "total_users": total_users,
        "signups_today": signups_today,
        "signups_week": signups_week,
        "referral_count": referral_count,
        "projects_today": projects_today,
        "revenue_today": revenue_today,
        "revenue_week": revenue_week,
        "revenue_month": revenue_month,
        "fraud_flags_count": 0,
        "system_health": "ok",
    }


@admin_router.get("/admin/analytics/overview")
async def admin_analytics_overview(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()[:10]
    week_ago = (now - timedelta(days=7)).isoformat()
    total_users = await db.users.count_documents({})
    projects_today = await db.projects.count_documents({"created_at": {"$gte": today_start}})
    signups_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    signups_week = await db.users.count_documents({"created_at": {"$gte": week_ago}})
    return {
        "total_users": total_users,
        "projects_today": projects_today,
        "signups_today": signups_today,
        "signups_week": signups_week,
    }


@admin_router.get("/admin/analytics/daily")
async def admin_analytics_daily(
    days: int = 7,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    format: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Daily metrics. Use days (default 7) or from_date+to_date (YYYY-MM-DD).
    format=csv for CSV export."""
    db = get_db()
    now = datetime.now(timezone.utc)
    out = []
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    if start_d and end_d and start_d <= end_d:
        from datetime import date as date_type
        delta = (end_d - start_d).days
        for i in range(min(delta + 1, 365)):
            d = (start_d + timedelta(days=i)).isoformat()
            day_start = d + "T00:00:00"
            day_end = d + "T23:59:59.999999"
            signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
            paid = await db.users.count_documents({"plan": {"$nin": ["free", None, ""]}, "created_at": {"$lte": day_end}})
            rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
            out.append({"date": d, "signups": signups, "paid_users_cumulative": paid, "revenue": rev})
    else:
        for i in range(max(1, min(days, 90))):
            d = (now - timedelta(days=i)).date().isoformat()
            day_start = d + "T00:00:00"
            day_end = d + "T23:59:59.999999"
            signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
            paid = await db.users.count_documents({"plan": {"$nin": ["free", None, ""]}, "created_at": {"$lte": day_end}})
            rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
            out.append({"date": d, "signups": signups, "paid_users_cumulative": paid, "revenue": rev})
        out = list(reversed(out))
    if (format or "").lower() == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["date", "signups", "paid_users_cumulative", "revenue"])
        for row in out:
            w.writerow([row["date"], row["signups"], row["paid_users_cumulative"], row["revenue"]])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics-daily.csv"},
        )
    return {"daily": out}


@admin_router.get("/admin/analytics/weekly")
async def admin_analytics_weekly(
    weeks: int = 12,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Weekly: signups and revenue per week.
    Optional from_date/to_date (YYYY-MM-DD) to limit range."""
    db = get_db()
    now = datetime.now(timezone.utc)
    out = []
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    for i in range(max(1, min(weeks, 52))):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(days=7)
        ws, we = week_start.isoformat(), week_end.isoformat()
        ws_date, we_date = ws[:10], we[:10]
        if start_d and (week_start.date() < start_d or week_end.date() < start_d):
            continue
        if end_d and week_start.date() > end_d:
            continue
        signups = await db.users.count_documents({"created_at": {"$gte": ws, "$lt": we}})
        rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": ws, "$lt": we}})
        out.append({"week_start": ws_date, "week_end": we_date, "signups": signups, "revenue": rev})
    return {"weekly": list(reversed(out))}


@admin_router.get("/admin/analytics/report")
async def admin_analytics_report(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Summary report for date range: total signups, total revenue, daily breakdown."""
    db = get_db()
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    now = datetime.now(timezone.utc)
    if not start_d or not end_d or start_d > end_d:
        start_d = (now - timedelta(days=30)).date()
        end_d = now.date()
    delta = min((end_d - start_d).days + 1, 365)
    total_signups = 0
    total_revenue = 0.0
    daily = []
    for i in range(delta):
        d = (start_d + timedelta(days=i)).isoformat()
        day_start = d + "T00:00:00"
        day_end = d + "T23:59:59.999999"
        signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
        rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
        total_signups += signups
        total_revenue += rev
        daily.append({"date": d, "signups": signups, "revenue": rev})
    return {
        "from_date": start_d.isoformat(),
        "to_date": end_d.isoformat(),
        "total_signups": total_signups,
        "total_revenue": round(total_revenue, 2),
        "daily": daily,
        "generated_at": now.isoformat(),
    }


@admin_router.get("/admin/analytics/usage")
async def admin_analytics_usage(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    rows = await db.token_usage.find({"created_at": {"$gte": week_ago}}, {"_id": 0}).to_list(10000)
    by_model: dict = {}
    for r in rows:
        m = r.get("model") or "unknown"
        by_model[m] = by_model.get(m, 0) + int(r.get("tokens_used") or 0)
    return {"usage_by_model": by_model, "period": "last_7_days"}


@admin_router.get("/admin/analytics/revenue")
async def admin_analytics_revenue(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    now = datetime.now(timezone.utc)
    month_ago = (now - timedelta(days=30)).isoformat()
    rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": month_ago}})
    return {"revenue_last_30_days": rev}


@admin_router.get("/admin/analytics/agents")
async def admin_analytics_agents(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    rows = await db.agent_status.find({}, {"_id": 0}).to_list(5000)
    agent_counts: dict = {}
    for r in rows:
        name = r.get("agent_name") or "unknown"
        agent_counts[name] = agent_counts.get(name, 0) + 1
    return {"agent_run_counts": agent_counts}


@admin_router.get("/admin/users")
async def admin_list_users(
    email: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 50,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    db = get_db()
    q: dict = {}
    if email:
        q["email"] = {"$regex": email, "$options": "i"}
    if plan:
        q["plan"] = plan
    cursor = db.users.find(q, {"_id": 0, "password": 0}).sort("created_at", -1).limit(limit)
    users = await cursor.to_list(length=limit)
    for u in users:
        u.pop("password", None)
        u["credit_balance"] = _user_credits(u)
    return {"users": users}


@admin_router.get("/admin/users/{user_id}")
async def admin_user_profile(user_id: str, admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    user["credit_balance"] = _user_credits(user)
    projects_count = await db.projects.count_documents({"user_id": user_id})
    referrals = (
        await db.referrals.find({"referrer_id": user_id}, {"_id": 0}).to_list(100)
        if hasattr(db, "referrals")
        else []
    )
    cursor = db.token_ledger.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20)
    ledger = await cursor.to_list(20)
    purchases = await db.token_ledger.find(
        {"user_id": user_id, "type": "purchase"}, {"_id": 0}
    ).to_list(1000)
    lifetime_revenue = round(
        sum(
            float(r.get("price") or TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0))
            for r in purchases
        ),
        2,
    )
    return {
        **user,
        "projects_count": projects_count,
        "referral_count": len(referrals),
        "recent_ledger": ledger,
        "last_login": user.get("last_login"),
        "lifetime_revenue": lifetime_revenue,
    }


@admin_router.post("/admin/users/{user_id}/grant-credits")
async def admin_grant_credits(
    user_id: str,
    body: GrantCreditsBody,
    admin: dict = Depends(get_current_admin(("owner", "operations", "support"))),
):
    db = get_db()
    audit_logger = get_audit_logger()
    role = admin.get("admin_role") or ("owner" if admin["id"] in ADMIN_USER_IDS else None)
    if role == "support" and body.credits > SUPPORT_GRANT_CAP_PER_MONTH:
        raise HTTPException(
            status_code=403,
            detail=f"Support can grant at most {SUPPORT_GRANT_CAP_PER_MONTH} credits per action",
        )
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$inc": {"credit_balance": body.credits}})
    await db.token_ledger.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "credits": body.credits,
            "type": "bonus",
            "description": body.reason or "Support bonus",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "granted_by": admin["id"],
        }
    )
    if audit_logger:
        await audit_logger.log(
            admin["id"],
            "admin_grant_credits",
            resource_type="user",
            resource_id=user_id,
            details={"credits": body.credits, "reason": body.reason},
        )
    return {"ok": True, "credits_added": body.credits}


@admin_router.post("/admin/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    body: SuspendBody,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    db = get_db()
    audit_logger = get_audit_logger()
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("admin_role") and target["id"] != admin["id"]:
        raise HTTPException(status_code=403, detail="Cannot suspend another admin")
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "suspended": True,
                "suspended_at": datetime.now(timezone.utc).isoformat(),
                "suspended_reason": body.reason,
            }
        },
    )
    if audit_logger:
        await audit_logger.log(
            admin["id"],
            "admin_suspend_user",
            resource_type="user",
            resource_id=user_id,
            details={"reason": body.reason},
        )
    return {"ok": True, "suspended": True}


@admin_router.post("/admin/users/{user_id}/downgrade")
async def admin_downgrade_user(
    user_id: str,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """Set user plan to free (e.g. for chargeback)."""
    db = get_db()
    audit_logger = get_audit_logger()
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"plan": "free"}})
    if audit_logger:
        await audit_logger.log(
            admin["id"],
            "admin_downgrade_user",
            resource_type="user",
            resource_id=user_id,
            details={"plan": "free"},
        )
    return {"ok": True, "plan": "free"}


@admin_router.post("/users/me/export")
async def self_export_user_data(user: dict = Depends(get_current_user)):
    """GDPR Article 20: user self-service data export (profile + ledger + project list)."""
    db = get_db()
    user_id = user["id"]
    safe_user = {k: v for k, v in user.items() if k not in ("password", "hashed_password", "_id")}
    ledger = await db.token_ledger.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    projects = await db.projects.find(
        {"user_id": user_id}, {"id": 1, "name": 1, "status": 1, "created_at": 1}
    ).to_list(200)
    return {
        "user": safe_user,
        "ledger_entries": ledger,
        "projects": projects,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "note": "This is all data CrucibAI holds about your account.",
    }


@admin_router.get("/admin/users/{user_id}/export")
async def admin_export_user(
    user_id: str,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """GDPR: export user data (profile + ledger summary + project ids)."""
    db = get_db()
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    ledger = await db.token_ledger.find({"user_id": user_id}, {"_id": 0}).to_list(MAX_ADMIN_USER_LEDGER)
    project_ids = await db.projects.find({"user_id": user_id}, {"id": 1}).to_list(
        MAX_ADMIN_USER_EXPORT_PROJECTS
    )
    return {
        "user": {k: v for k, v in user.items() if k != "password"},
        "ledger_entries": ledger,
        "project_ids": [p["id"] for p in project_ids],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@admin_router.get("/admin/billing/transactions")
async def admin_billing_transactions(
    limit: int = 100,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """List purchases (who paid, when, amount, status) from ledger."""
    db = get_db()
    rows = await db.token_ledger.find(
        {"type": "purchase"},
        {
            "_id": 0,
            "user_id": 1,
            "bundle": 1,
            "price": 1,
            "credits": 1,
            "created_at": 1,
            "stripe_session_id": 1,
        },
    ).sort("created_at", -1).limit(limit).to_list(limit)
    for r in rows:
        if r.get("price") is None:
            r["price"] = TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0)
    return {"transactions": rows}


@admin_router.get("/admin/fraud/flags")
async def admin_fraud_flags(
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    db = get_db()
    rows = await db.blocked_requests.find({}, {"_id": 0}).sort("timestamp", -1).to_list(500)
    return {"flags": rows}


@admin_router.get("/admin/legal/blocked-requests")
async def admin_legal_blocked(
    limit: int = 100,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    db = get_db()
    rows = await db.blocked_requests.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"blocked_requests": rows, "count": len(rows)}


@admin_router.post("/admin/legal/review/{request_id}")
async def admin_legal_review(
    request_id: str,
    body: dict,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    db = get_db()
    audit_logger = get_audit_logger()
    action = (body.get("action") or "reviewed").lower()
    await db.blocked_requests.update_one(
        {"id": request_id},
        {
            "$set": {
                "status": action,
                "reviewed_by": admin["id"],
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_notes": body.get("notes") or "",
            }
        },
    )
    if audit_logger:
        await audit_logger.log(
            admin["id"],
            "admin_legal_review",
            resource_type="blocked_request",
            resource_id=request_id,
            details={"action": action},
        )
    return {"ok": True, "action": action}


@admin_router.get("/admin/referrals/links")
async def admin_referral_links(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    db = get_db()
    rows = await db.referral_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"referral_links": rows}


@admin_router.get("/admin/referrals/leaderboard")
async def admin_referrals_leaderboard(
    limit: int = 100,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$referrer_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    rows = await db.referrals.aggregate(pipeline).to_list(limit) if hasattr(db, "referrals") else []
    return {"leaderboard": [{"user_id": r["_id"], "referrals": r["count"]} for r in rows]}


@admin_router.get("/admin/segments")
async def admin_segments(
    plan: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """User segments: group by plan and return counts."""
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$plan", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    if plan:
        pipeline.insert(0, {"$match": {"plan": plan}})
    rows = await db.users.aggregate(pipeline).to_list(50)
    return {"segments": [{"plan": r["_id"], "users": r["count"]} for r in rows]}


@admin_router.post("/admin/settings/update")
async def admin_settings_update(
    body: dict,
    admin: dict = Depends(get_current_admin(("owner",))),
):
    """Update platform settings (rate limits, feature flags, etc.)."""
    db = get_db()
    audit_logger = get_audit_logger()
    allowed_keys = {"rate_limit_per_minute", "free_tier_max_projects", "feature_flags"}
    updates = {k: v for k, v in body.items() if k in allowed_keys}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid settings keys provided")
    await db.platform_settings.update_one({}, {"$set": updates}, upsert=True)
    if audit_logger:
        await audit_logger.log(
            admin["id"],
            "admin_settings_update",
            details={"keys": list(updates.keys())},
        )
    return {"ok": True, "updated": list(updates.keys())}


@admin_router.get("/admin/audit-log")
async def admin_audit_log(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, le=1000),
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    audit_logger = get_audit_logger()
    if not audit_logger:
        return {"logs": [], "note": "Audit logger not initialized"}
    q: dict = {}
    if user_id:
        q["user_id"] = user_id
    if action:
        q["action"] = action
    try:
        logs = await audit_logger.get_logs(q, limit=limit)
    except Exception:
        logs = []
    return {"logs": logs}


@admin_router.post("/admin/notifications/send")
async def admin_notifications_send(
    data: AdminNotificationBody,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """Send system notification. Stores in db.notifications."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "target": data.target or "all",
        "subject": data.subject,
        "body": data.body,
        "created_at": now,
        "created_by": admin.get("id"),
    }
    await db.notifications.insert_one(doc)
    return {"ok": True, "notification_id": doc["id"]}
