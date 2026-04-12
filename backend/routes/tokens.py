from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tokens"])


def _get_auth():
    from server import get_current_user

    return get_current_user


def _get_db():
    import server

    return server.db


def _get_token_constants():
    import server

    return (
        server.TOKEN_BUNDLES,
        server.ANNUAL_PRICES,
        server.STRIPE_SECRET,
        server.FRONTEND_URL,
        server.REFERRAL_CAP_PER_MONTH,
        server.CREDITS_PER_TOKEN,
        server.MAX_TOKEN_USAGE_LIST,
    )


def _get_server_helpers():
    from server import _ensure_credit_balance, _generate_referral_code, _user_credits

    return _user_credits, _ensure_credit_balance, _generate_referral_code


try:
    from server import TokenPurchase, TokenPurchaseCustom
except ImportError:
    from pydantic import BaseModel

    class TokenPurchase(BaseModel):
        bundle: str

    class TokenPurchaseCustom(BaseModel):
        credits: int


# ==================== PASSES / BUILD HISTORY ROUTES ====================


@router.get("/passes/{task_id}")
async def get_build_passes(task_id: str, user: dict = Depends(_get_auth())):
    """Return the pass history for a completed build task."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if (
        task.get("user_id") not in (user["id"], "guest")
        and task.get("user_id") != user["id"]
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    passes = task.get("passes") or []
    if not passes:
        files = task.get("files") or {}
        file_keys = list(files.keys())
        passes = [
            {
                "pass": 1,
                "label": "Static Foundation",
                "desc": "Config files: tsconfig, vite, package.json, docker-compose, CI/CD",
                "color": "#a78bfa",
                "status": "complete",
            },
            {
                "pass": 2,
                "label": "Architecture",
                "desc": "App structure, shared types, routing, contexts",
                "color": "#60a5fa",
                "status": "complete",
            },
            {
                "pass": 3,
                "label": "Frontend Generation",
                "desc": f"{sum(1 for f in file_keys if '.tsx' in f or '.jsx' in f)} React components generated",
                "color": "#34d399",
                "status": "complete",
            },
            {
                "pass": 4,
                "label": "Backend Generation",
                "desc": f"{sum(1 for f in file_keys if 'server' in f or 'routes' in f or 'api' in f)} backend files generated",
                "color": "#fb923c",
                "status": "complete",
            },
            {
                "pass": 5,
                "label": "Integration",
                "desc": "Frontend ↔ backend wiring, API client, shared types",
                "color": "#fbbf24",
                "status": "complete",
            },
            {
                "pass": 6,
                "label": "Finalization",
                "desc": f"README, deployment config, {len(file_keys)} total files",
                "color": "#f87171",
                "status": "complete",
            },
        ]
    return {
        "task_id": task_id,
        "passes": passes,
        "total_files": len(task.get("files") or {}),
        "build_kind": task.get("build_kind", "fullstack"),
        "status": task.get("status", "complete"),
        "created_at": task.get("created_at"),
    }


@router.get("/passes")
async def list_user_passes(
    user: dict = Depends(_get_auth()), limit: int = Query(10, ge=1, le=50)
):
    """List recent build pass summaries for the current user."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    tasks = (
        await db.tasks.find(
            {"user_id": user["id"], "status": "complete"},
            {
                "id": 1,
                "title": 1,
                "build_kind": 1,
                "total_files": 1,
                "updated_at": 1,
                "created_at": 1,
            },
        )
        .sort("updated_at", -1)
        .to_list(limit)
    )
    return {"passes": tasks, "count": len(tasks)}


# ==================== TOKEN ROUTES ====================


@router.get("/tokens/bundles")
async def get_bundles():
    TOKEN_BUNDLES, ANNUAL_PRICES, _, _, _, _, _ = _get_token_constants()
    return {
        "bundles": TOKEN_BUNDLES,
        "annual_prices": ANNUAL_PRICES,
        "custom_addon": {
            "min_credits": 100,
            "max_credits": 10000,
            "price_per_credit": 0.03,
        },
    }


@router.post("/tokens/purchase")
async def purchase_tokens(data: TokenPurchase, user: dict = Depends(_get_auth())):
    """Direct credit grant. In production (Stripe configured), use Stripe Checkout instead."""
    db = _get_db()
    TOKEN_BUNDLES, _, STRIPE_SECRET, _, _, CREDITS_PER_TOKEN, _ = _get_token_constants()
    _user_credits, _ensure_credit_balance, _ = _get_server_helpers()
    if STRIPE_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Use Credit Center → Pay with Stripe to purchase credits. Direct purchase is disabled when payments are enabled.",
        )
    if data.bundle not in TOKEN_BUNDLES:
        raise HTTPException(status_code=400, detail="Invalid bundle")
    bundle = TOKEN_BUNDLES[data.bundle]
    credits = bundle.get("credits", bundle["tokens"] // CREDITS_PER_TOKEN)
    await _ensure_credit_balance(user["id"])
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"token_balance": bundle["tokens"], "credit_balance": credits}},
    )
    await db.token_ledger.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "tokens": bundle["tokens"],
            "credits": credits,
            "type": "purchase",
            "bundle": data.bundle,
            "price": bundle["price"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    new_cred = _user_credits(user) + credits
    if data.bundle in ("builder", "pro", "scale", "teams"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"plan": data.bundle}})
    return {
        "message": "Purchase successful",
        "new_balance": new_cred,
        "credits_added": credits,
        "tokens_added": bundle["tokens"],
    }


@router.post("/tokens/purchase-custom")
async def purchase_tokens_custom(
    data: TokenPurchaseCustom, user: dict = Depends(_get_auth())
):
    """Custom credit purchase (slider): 100-10000 credits at $0.03/credit. When Stripe enabled, use Stripe instead."""
    db = _get_db()
    _, _, STRIPE_SECRET, _, _, CREDITS_PER_TOKEN, _ = _get_token_constants()
    _user_credits, _ensure_credit_balance, _ = _get_server_helpers()
    if STRIPE_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Use Credit Center → Pay with Stripe to purchase credits. Direct purchase is disabled when payments are enabled.",
        )
    credits = data.credits
    price = round(credits * 0.03, 2)
    tokens = credits * CREDITS_PER_TOKEN
    await _ensure_credit_balance(user["id"])
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"token_balance": tokens, "credit_balance": credits}},
    )
    await db.token_ledger.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "tokens": tokens,
            "credits": credits,
            "type": "purchase",
            "bundle": "custom",
            "price": price,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    new_cred = _user_credits(user) + credits
    return {
        "message": "Purchase successful",
        "new_balance": new_cred,
        "credits_added": credits,
        "tokens_added": tokens,
    }


@router.get("/tokens/history")
async def get_token_history(user: dict = Depends(_get_auth())):
    db = _get_db()
    _, _, _, _, _, _, _ = _get_token_constants()
    _user_credits, _ensure_credit_balance, _ = _get_server_helpers()
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    cursor = db.token_ledger.find({"user_id": user["id"]}, {"_id": 0}).sort(
        "created_at", -1
    )
    history = await cursor.to_list(100)
    return {"history": history, "current_balance": cred, "credit_balance": cred}


@router.get("/tokens/usage")
async def get_token_usage(user: dict = Depends(_get_auth())):
    db = _get_db()
    _, _, _, _, _, _, MAX_TOKEN_USAGE_LIST = _get_token_constants()
    _user_credits, _, _ = _get_server_helpers()
    usage = await db.token_usage.find({"user_id": user["id"]}, {"_id": 0}).to_list(
        MAX_TOKEN_USAGE_LIST
    )

    by_agent: Dict[str, int] = {}
    by_project: Dict[str, int] = {}
    total_used = 0

    for u in usage:
        agent = u.get("agent", "Unknown")
        project = u.get("project_id", "Unknown")
        tokens = u.get("tokens", 0)

        by_agent[agent] = by_agent.get(agent, 0) + tokens
        by_project[project] = by_project.get(project, 0) + tokens
        total_used += tokens

    by_day: Dict[str, int] = defaultdict(int)
    for u in usage:
        created = u.get("created_at")
        if created:
            day = (
                created[:10]
                if isinstance(created, str)
                else datetime.fromisoformat(created.replace("Z", "+00:00")).strftime(
                    "%Y-%m-%d"
                )
            )
            by_day[day] += u.get("tokens", 0)
    sorted_days = sorted(by_day.keys(), reverse=True)[:14]
    daily_trend = [{"date": d, "tokens": by_day[d]} for d in sorted_days]

    return {
        "total_used": total_used,
        "by_agent": by_agent,
        "by_project": by_project,
        "balance": _user_credits(user),
        "credit_balance": _user_credits(user),
        "daily_trend": daily_trend,
    }


# ==================== REFERRAL ROUTES ====================


@router.get("/referrals/code")
async def get_referral_code(user: dict = Depends(_get_auth())):
    """Return or create user's referral code. Share link: /auth?ref=CODE"""
    db = _get_db()
    _, _, _, FRONTEND_URL, _, _, _ = _get_token_constants()
    _, _, _generate_referral_code = _get_server_helpers()
    row = await db.referral_codes.find_one({"user_id": user["id"]}, {"_id": 0})
    if row:
        return {
            "code": row["code"],
            "link": f"{FRONTEND_URL or ''}/auth?ref={row['code']}",
        }
    code = _generate_referral_code()
    while await db.referral_codes.find_one({"code": code}):
        code = _generate_referral_code()
    await db.referral_codes.insert_one(
        {
            "user_id": user["id"],
            "code": code,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"code": code, "link": f"{FRONTEND_URL or ''}/auth?ref={code}"}


@router.get("/referrals/stats")
async def get_referral_stats(user: dict = Depends(_get_auth())):
    """Referrals sent this month and total."""
    db = _get_db()
    _, _, _, _, REFERRAL_CAP_PER_MONTH, _, _ = _get_token_constants()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = await db.referrals.count_documents(
        {
            "referrer_id": user["id"],
            "signup_completed_at": {"$gte": month_start.isoformat()},
        }
    )
    total = await db.referrals.count_documents({"referrer_id": user["id"]})
    return {"this_month": this_month, "total": total, "cap": REFERRAL_CAP_PER_MONTH}
