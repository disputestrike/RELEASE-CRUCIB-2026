"""PayPal payment routes — replaces braintree_payments.py"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.paypal_billing import (
    BillingConfigError,
    BillingError,
    activate_paypal_subscription,
    billing_history,
    billing_overview,
    cancel_paypal_subscription,
    capture_paypal_order,
    create_paypal_order,
    create_paypal_subscription,
    list_active_prices,
    paypal_client_id,
    paypal_configured,
    process_webhook,
    required_paypal_config,
)

router = APIRouter(tags=["billing"])


def _get_auth():
    from ..deps import get_current_user
    return get_current_user


def _get_db():
    try:
        from ..deps import get_db
        return get_db()
    except Exception:
        return None


def _http_error(exc: BillingError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail())


def _db_or_503():
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail={"error": "db_unavailable", "message": "Database not available"})
    return db


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    price_id: Optional[str] = None
    product_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class CaptureOrderRequest(BaseModel):
    paypal_order_id: str


class CreateSubscriptionRequest(BaseModel):
    price_id: Optional[str] = None
    product_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class ActivateSubscriptionRequest(BaseModel):
    paypal_subscription_id: str


class CancelSubscriptionRequest(BaseModel):
    subscription_id: str
    cancel_at_period_end: bool = True


# ---------------------------------------------------------------------------
# Public config endpoint (returns client ID for PayPal JS SDK)
# ---------------------------------------------------------------------------

@router.get("/billing/config")
async def billing_config():
    """Returns PayPal client ID for the frontend SDK loader."""
    return {
        "provider": "paypal",
        "paypal_client_id": paypal_client_id(),
        "configured": paypal_configured(),
        "required_config": [] if paypal_configured() else required_paypal_config(),
    }


# ---------------------------------------------------------------------------
# Plans / prices
# ---------------------------------------------------------------------------

@router.get("/billing/plans")
async def get_plans(db=Depends(_db_or_503)):
    try:
        prices = await list_active_prices(db)
        return {"plans": prices, "prices": prices}
    except BillingError as exc:
        raise _http_error(exc)


# ---------------------------------------------------------------------------
# Billing overview
# ---------------------------------------------------------------------------

@router.get("/billing/overview")
async def get_overview(
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await billing_overview(db, current_user)
    except BillingError as exc:
        raise _http_error(exc)


# ---------------------------------------------------------------------------
# One-time orders
# ---------------------------------------------------------------------------

@router.post("/billing/create-order")
async def post_create_order(
    body: CreateOrderRequest,
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await create_paypal_order(
            db,
            current_user,
            price_id=body.price_id,
            product_id=body.product_id,
            idempotency_key=body.idempotency_key,
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/billing/capture-order")
async def post_capture_order(
    body: CaptureOrderRequest,
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await capture_paypal_order(db, current_user, paypal_order_id=body.paypal_order_id)
    except BillingError as exc:
        raise _http_error(exc)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@router.post("/billing/create-subscription")
async def post_create_subscription(
    body: CreateSubscriptionRequest,
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await create_paypal_subscription(
            db,
            current_user,
            price_id=body.price_id,
            product_id=body.product_id,
            idempotency_key=body.idempotency_key,
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/billing/activate-subscription")
async def post_activate_subscription(
    body: ActivateSubscriptionRequest,
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await activate_paypal_subscription(
            db, current_user, paypal_subscription_id=body.paypal_subscription_id
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/billing/cancel-subscription")
async def post_cancel_subscription(
    body: CancelSubscriptionRequest,
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await cancel_paypal_subscription(
            db,
            current_user,
            subscription_id=body.subscription_id,
            cancel_at_period_end=body.cancel_at_period_end,
        )
    except BillingError as exc:
        raise _http_error(exc)


# ---------------------------------------------------------------------------
# Billing history
# ---------------------------------------------------------------------------

@router.get("/billing/history")
async def get_billing_history(
    db=Depends(_db_or_503),
    current_user=Depends(_get_auth()),
):
    try:
        return await billing_history(db, current_user)
    except BillingError as exc:
        raise _http_error(exc)


# ---------------------------------------------------------------------------
# PayPal Webhooks
# ---------------------------------------------------------------------------

@router.post("/billing/webhook/paypal")
async def paypal_webhook(request: Request, db=Depends(_db_or_503)):
    try:
        body = await request.json()
        headers = dict(request.headers)
        result = await process_webhook(db, body, headers=headers)
        return result
    except BillingError as exc:
        raise _http_error(exc)
    except Exception:
        return {"status": "ok"}
