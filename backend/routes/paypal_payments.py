"""
PayPal payment routes — CrucibAI
POST /api/paypal/create-order   -> { order_id, approve_url, ... }
POST /api/paypal/capture-order  -> { status, credits, payer_email, ... }
POST /api/paypal/webhook        -> PayPal IPN / webhook handler
GET  /api/paypal/plans          -> List of available plans with prices
GET  /api/paypal/status         -> Whether PayPal is configured
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.paypal_billing import (
    PayPalConfigError,
    PayPalError,
    capture_order,
    create_order,
    get_order,
    list_plans,
    paypal_configured,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/paypal", tags=["paypal"])


def _get_current_user():
    try:
        from ..deps import get_current_user
        return get_current_user
    except Exception:
        return None


def _http(exc: PayPalError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail())


# ── Models ───────────────────────────────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    plan: str = Field(..., description="Plan key: starter | pro | enterprise | credits_10 | credits_50")
    return_url: str = Field(..., description="URL PayPal redirects to on success")
    cancel_url: str = Field(..., description="URL PayPal redirects to on cancel")


class CaptureOrderRequest(BaseModel):
    order_id: str = Field(..., description="PayPal order ID to capture")


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get("/status")
async def paypal_status():
    """Returns whether PayPal is configured and which environment is active."""
    from ..services.paypal_billing import PAYPAL_ENV
    return {
        "configured": paypal_configured(),
        "environment": PAYPAL_ENV,
        "provider": "paypal",
    }


@router.get("/plans")
async def get_plans():
    """Return all available pricing plans."""
    return {"plans": list_plans()}


@router.post("/create-order")
async def create_paypal_order(body: CreateOrderRequest, request: Request):
    """
    Create a PayPal order for a given plan.
    Returns order_id + approve_url; frontend opens approve_url in PayPal JS SDK.
    """
    if not paypal_configured():
        raise HTTPException(status_code=503, detail="PayPal is not configured on this server.")

    # Try to get user_id from auth token (non-fatal if auth not wired)
    user_id = "guest"
    try:
        from ..deps import get_current_user
        from fastapi.security import HTTPBearer
        scheme = HTTPBearer(auto_error=False)
        creds = await scheme(request)
        if creds:
            user = await get_current_user(creds)
            user_id = str(getattr(user, "id", None) or getattr(user, "user_id", None) or "guest")
    except Exception:
        pass

    try:
        result = await create_order(
            plan_key=body.plan,
            user_id=user_id,
            return_url=body.return_url,
            cancel_url=body.cancel_url,
        )
    except PayPalConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except PayPalError as exc:
        raise _http(exc)

    return result


@router.post("/capture-order")
async def capture_paypal_order(body: CaptureOrderRequest, request: Request):
    """
    Capture an approved PayPal order.
    Call this after the user approves via PayPal JS SDK onApprove callback.
    Returns payer details + credits to grant.
    """
    if not paypal_configured():
        raise HTTPException(status_code=503, detail="PayPal is not configured on this server.")

    try:
        result = await capture_order(body.order_id)
    except PayPalError as exc:
        raise _http(exc)

    # TODO: grant credits to user in DB here
    # await grant_credits(user_id=result["payer_id"], credits=result["credits"])
    logger.info("Order captured and ready for credit grant: %s", result)

    return result


@router.post("/webhook")
async def paypal_webhook(request: Request):
    """
    PayPal webhook handler (PAYMENT.CAPTURE.COMPLETED, etc.)
    Verifies signature then processes event.
    Set PAYPAL_WEBHOOK_ID in your env to enable signature verification.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    is_valid = await verify_webhook_signature(headers, raw_body)
    if not is_valid:
        logger.warning("PayPal webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = event.get("event_type", "")
    resource = event.get("resource", {})

    logger.info("PayPal webhook received: %s", event_type)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture_id = resource.get("id", "")
        amount = resource.get("amount", {}).get("value", "0")
        custom_id = resource.get("custom_id", "")
        logger.info("Payment captured: capture_id=%s amount=%s user=%s", capture_id, amount, custom_id)
        # TODO: persist to DB, grant credits
        # await record_payment(capture_id=capture_id, user_id=custom_id, amount=amount)

    elif event_type == "PAYMENT.CAPTURE.DENIED":
        logger.warning("Payment denied: %s", resource.get("id"))

    elif event_type == "PAYMENT.CAPTURE.REFUNDED":
        logger.info("Payment refunded: %s", resource.get("id"))
        # TODO: revoke credits

    return {"received": True, "event_type": event_type}
