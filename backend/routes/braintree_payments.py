from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel, Field

from ..services.braintree_billing import (
    BillingConfigError,
    BillingError,
    braintree_configured,
    billing_history,
    billing_overview,
    cancel_subscription,
    change_subscription_plan,
    create_one_time_checkout,
    create_subscription_checkout,
    default_merchant_account_id,
    ensure_custom_credit_price,
    generate_client_token,
    make_gateway,
    process_webhook,
    required_braintree_config,
    resume_subscription,
    update_default_payment_method,
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


def _gateway_or_503():
    try:
        return make_gateway()
    except BillingConfigError as exc:
        raise _http_error(exc)


def _db_or_503():
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    return db


class OneTimeCheckoutBody(BaseModel):
    productId: Optional[str] = None
    priceId: Optional[str] = None
    paymentMethodNonce: Optional[str] = None
    payment_method_nonce: Optional[str] = None
    billingDetails: Dict[str, Any] = Field(default_factory=dict)
    deviceData: Optional[str] = None
    device_data: Optional[str] = None
    idempotencyKey: Optional[str] = None
    idempotency_key: Optional[str] = None


class SubscriptionCheckoutBody(BaseModel):
    productId: Optional[str] = None
    planId: Optional[str] = None
    priceId: Optional[str] = None
    paymentMethodNonce: Optional[str] = None
    payment_method_nonce: Optional[str] = None
    idempotencyKey: Optional[str] = None
    idempotency_key: Optional[str] = None


class PaymentMethodBody(BaseModel):
    paymentMethodNonce: Optional[str] = None
    payment_method_nonce: Optional[str] = None


class ChangePlanBody(BaseModel):
    subscriptionId: str
    newPlanId: Optional[str] = None
    newPriceId: Optional[str] = None


class CancelSubscriptionBody(BaseModel):
    subscriptionId: str
    cancelAtPeriodEnd: bool = True


class ResumeSubscriptionBody(BaseModel):
    subscriptionId: str


class LegacyBraintreeCheckoutBody(BaseModel):
    bundle: Optional[str] = None
    credits: Optional[int] = Field(None, ge=100, le=10000)
    payment_method_nonce: str = Field(..., min_length=1, max_length=4096)
    device_data: Optional[str] = Field(None, max_length=20000)
    idempotency_key: Optional[str] = Field(None, max_length=200)


def _nonce(body: Any) -> str:
    value = getattr(body, "paymentMethodNonce", None) or getattr(body, "payment_method_nonce", None)
    if not value:
        raise HTTPException(status_code=400, detail="paymentMethodNonce is required")
    return value


def _idempotency(body: Any) -> Optional[str]:
    return getattr(body, "idempotencyKey", None) or getattr(body, "idempotency_key", None)


@router.get("/api/payments/braintree/status")
async def braintree_status():
    return {
        "provider": "braintree",
        "configured": braintree_configured(),
        "environment": os.environ.get("BRAINTREE_ENVIRONMENT", "sandbox"),
        "merchant_account_id": default_merchant_account_id(),
        "required_config": required_braintree_config(),
        "webhook_endpoint": f"{os.environ.get('APP_URL', '').rstrip('/')}/api/webhooks/braintree"
        if os.environ.get("APP_URL")
        else "/api/webhooks/braintree",
    }


@router.get("/api/payments/braintree/client-token")
@router.get("/api/billing/client-token")
async def braintree_client_token(user: dict = Depends(_get_auth())):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await generate_client_token(db, gateway, user)
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/payments/braintree/checkout")
async def legacy_braintree_checkout(
    body: LegacyBraintreeCheckoutBody,
    user: dict = Depends(_get_auth()),
):
    """Compatibility checkout for Credit Center bundles.

    It now runs through the product/price/order layer instead of charging from
    frontend-provided amounts.
    """
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        price_id = None
        if body.bundle:
            price_id = f"price_{body.bundle}_one_time"
        elif body.credits:
            custom_price = await ensure_custom_credit_price(db, int(body.credits))
            price_id = custom_price["id"]
        result = await create_one_time_checkout(
            db,
            gateway,
            user,
            product_id=None,
            price_id=price_id,
            payment_method_nonce=body.payment_method_nonce,
            idempotency_key=body.idempotency_key,
            device_data=body.device_data,
        )
        price_meta = result["order"].get("metadata") or {}
        return {
            "status": "success",
            "provider": "braintree",
            "credits_added": price_meta.get("credits"),
            "tokens_added": price_meta.get("tokens"),
            "transaction": result["order"],
        }
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/checkout/one-time")
async def checkout_one_time(body: OneTimeCheckoutBody, user: dict = Depends(_get_auth())):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await create_one_time_checkout(
            db,
            gateway,
            user,
            product_id=body.productId,
            price_id=body.priceId,
            payment_method_nonce=_nonce(body),
            idempotency_key=_idempotency(body),
            device_data=body.deviceData or body.device_data,
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/checkout/subscription")
async def checkout_subscription(
    body: SubscriptionCheckoutBody,
    user: dict = Depends(_get_auth()),
):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await create_subscription_checkout(
            db,
            gateway,
            user,
            product_id=body.productId,
            price_id=body.priceId or body.planId,
            payment_method_nonce=_nonce(body),
            idempotency_key=_idempotency(body),
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.get("/api/billing/overview")
async def get_billing_overview(user: dict = Depends(_get_auth())):
    db = _db_or_503()
    return await billing_overview(db, user)


@router.get("/api/billing/history")
async def get_billing_history(user: dict = Depends(_get_auth())):
    db = _db_or_503()
    return await billing_history(db, user)


@router.post("/api/billing/payment-method")
async def post_payment_method(body: PaymentMethodBody, user: dict = Depends(_get_auth())):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await update_default_payment_method(
            db,
            gateway,
            user,
            payment_method_nonce=_nonce(body),
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/billing/change-plan")
async def post_change_plan(body: ChangePlanBody, user: dict = Depends(_get_auth())):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await change_subscription_plan(
            db,
            gateway,
            user,
            subscription_id=body.subscriptionId,
            new_price_id=body.newPriceId or body.newPlanId or "",
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/billing/cancel-subscription")
async def post_cancel_subscription(
    body: CancelSubscriptionBody,
    user: dict = Depends(_get_auth()),
):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        return await cancel_subscription(
            db,
            gateway,
            user,
            subscription_id=body.subscriptionId,
            cancel_at_period_end=body.cancelAtPeriodEnd,
        )
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/billing/resume-subscription")
async def post_resume_subscription(
    body: ResumeSubscriptionBody,
    user: dict = Depends(_get_auth()),
):
    db = _db_or_503()
    try:
        return await resume_subscription(db, user, subscription_id=body.subscriptionId)
    except BillingError as exc:
        raise _http_error(exc)


@router.post("/api/payments/braintree/webhook")
@router.post("/api/webhooks/braintree")
async def braintree_webhook(bt_signature: str = Form(...), bt_payload: str = Form(...)):
    db = _db_or_503()
    gateway = _gateway_or_503()
    try:
        notification = gateway.webhook_notification.parse(bt_signature, bt_payload)
        return await process_webhook(db, notification, signature=bt_signature, payload=bt_payload)
    except BillingError as exc:
        raise _http_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Braintree webhook: {exc}")
