from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/payments/braintree", tags=["payments"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_db():
    try:
        from ..deps import get_db

        return get_db()
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configured() -> bool:
    return bool(
        os.environ.get("BRAINTREE_MERCHANT_ID")
        and os.environ.get("BRAINTREE_PUBLIC_KEY")
        and os.environ.get("BRAINTREE_PRIVATE_KEY")
    )


def _gateway():
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "braintree_requires_config",
                "required_config": [
                    "BRAINTREE_MERCHANT_ID",
                    "BRAINTREE_PUBLIC_KEY",
                    "BRAINTREE_PRIVATE_KEY",
                    "BRAINTREE_ENVIRONMENT",
                ],
            },
        )
    try:
        import braintree
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "braintree_sdk_missing",
                "package": "braintree",
                "message": str(exc),
            },
        )
    env_name = (os.environ.get("BRAINTREE_ENVIRONMENT") or "sandbox").lower()
    environment = braintree.Environment.Production if env_name == "production" else braintree.Environment.Sandbox
    return braintree.BraintreeGateway(
        braintree.Configuration(
            environment=environment,
            merchant_id=os.environ["BRAINTREE_MERCHANT_ID"],
            public_key=os.environ["BRAINTREE_PUBLIC_KEY"],
            private_key=os.environ["BRAINTREE_PRIVATE_KEY"],
        )
    )


def _uid(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "guest")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "guest")


def _get_pricing():
    from .. import server

    return server.TOKEN_BUNDLES, server.CREDITS_PER_TOKEN


def _amount_for_purchase(bundle: Optional[str], credits: Optional[int]) -> Dict[str, Any]:
    bundles, credits_per_token = _get_pricing()
    if bundle:
        if bundle not in bundles:
            raise HTTPException(status_code=400, detail="Invalid bundle")
        plan = bundles[bundle]
        return {
            "bundle": bundle,
            "credits": int(plan.get("credits") or plan["tokens"] // credits_per_token),
            "tokens": int(plan["tokens"]),
            "amount": Decimal(str(plan["price"])).quantize(Decimal("0.01")),
            "plan": bundle if bundle in {"builder", "pro", "scale", "teams"} else None,
        }
    if credits is None:
        raise HTTPException(status_code=400, detail="bundle or credits is required")
    if credits < 100 or credits > 10000:
        raise HTTPException(status_code=400, detail="credits must be between 100 and 10000")
    try:
        amount = (Decimal(credits) * Decimal("0.03")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="Invalid credit amount")
    return {
        "bundle": "custom",
        "credits": credits,
        "tokens": credits * credits_per_token,
        "amount": amount,
        "plan": None,
    }


async def _record(collection: str, doc: Dict[str, Any]) -> None:
    db = _get_db()
    if db is None:
        return
    await getattr(db, collection).insert_one(doc)


class BraintreeCheckoutBody(BaseModel):
    bundle: Optional[str] = None
    credits: Optional[int] = Field(None, ge=100, le=10000)
    payment_method_nonce: str = Field(..., min_length=1, max_length=4096)
    device_data: Optional[str] = Field(None, max_length=20000)
    idempotency_key: Optional[str] = Field(None, max_length=200)


@router.get("/status")
async def braintree_status():
    return {
        "provider": "braintree",
        "configured": _configured(),
        "environment": os.environ.get("BRAINTREE_ENVIRONMENT", "sandbox"),
        "required_config": [
            "BRAINTREE_MERCHANT_ID",
            "BRAINTREE_PUBLIC_KEY",
            "BRAINTREE_PRIVATE_KEY",
            "BRAINTREE_ENVIRONMENT",
        ],
    }


@router.get("/client-token")
async def braintree_client_token(user: dict = Depends(_get_auth())):
    gateway = _gateway()
    try:
        token = gateway.client_token.generate()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Braintree client token failed: {exc}")
    return {"provider": "braintree", "client_token": token, "user_id": _uid(user)}


@router.post("/checkout")
async def braintree_checkout(body: BraintreeCheckoutBody, user: dict = Depends(_get_auth())):
    user_id = _uid(user)
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    if db is not None and body.idempotency_key:
        existing = await db.braintree_transactions.find_one(
            {"user_id": user_id, "idempotency_key": body.idempotency_key, "status": "success"}
        )
        if existing:
            return {
                "status": "success",
                "provider": "braintree",
                "transaction": existing,
                "idempotent_replay": True,
            }
    purchase = _amount_for_purchase(body.bundle, body.credits)
    gateway = _gateway()
    order_id = f"crucibai_{uuid.uuid4().hex[:24]}"
    sale_payload: Dict[str, Any] = {
        "amount": f"{purchase['amount']:.2f}",
        "payment_method_nonce": body.payment_method_nonce,
        "order_id": order_id,
        "options": {"submit_for_settlement": True},
    }
    merchant_account_id = os.environ.get("BRAINTREE_MERCHANT_ACCOUNT_ID")
    if merchant_account_id:
        sale_payload["merchant_account_id"] = merchant_account_id
    if body.device_data:
        sale_payload["device_data"] = body.device_data
    try:
        result = gateway.transaction.sale(sale_payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Braintree transaction failed: {exc}")
    tx_doc = {
        "id": f"bt_{uuid.uuid4().hex}",
        "provider": "braintree",
        "user_id": user_id,
        "status": "success" if result.is_success else "failed",
        "idempotency_key": body.idempotency_key,
        "order_id": order_id,
        "bundle": purchase["bundle"],
        "credits": purchase["credits"],
        "tokens": purchase["tokens"],
        "amount": f"{purchase['amount']:.2f}",
        "transaction_id": getattr(getattr(result, "transaction", None), "id", None),
        "transaction_status": getattr(getattr(result, "transaction", None), "status", None),
        "errors": None if result.is_success else str(result.errors),
        "created_at": _now(),
    }
    await _record("braintree_transactions", tx_doc)
    if not result.is_success:
        raise HTTPException(status_code=402, detail={"error": "braintree_transaction_failed", "transaction": tx_doc})
    if db is not None:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"token_balance": purchase["tokens"], "credit_balance": purchase["credits"]}},
        )
        if purchase["plan"]:
            await db.users.update_one({"id": user_id}, {"$set": {"plan": purchase["plan"]}})
        await db.token_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tokens": purchase["tokens"],
                "credits": purchase["credits"],
                "type": "purchase",
                "provider": "braintree",
                "bundle": purchase["bundle"],
                "price": float(purchase["amount"]),
                "transaction_id": tx_doc["transaction_id"],
                "created_at": _now(),
            }
        )
    return {
        "status": "success",
        "provider": "braintree",
        "credits_added": purchase["credits"],
        "tokens_added": purchase["tokens"],
        "transaction": tx_doc,
    }


@router.post("/webhook")
async def braintree_webhook(bt_signature: str = Form(...), bt_payload: str = Form(...)):
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    gateway = _gateway()
    try:
        notification = gateway.webhook_notification.parse(bt_signature, bt_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Braintree webhook: {exc}")
    event_id = f"btwh_{uuid.uuid4().hex}"
    doc = {
        "id": event_id,
        "provider": "braintree",
        "kind": str(getattr(notification, "kind", "")),
        "timestamp": str(getattr(notification, "timestamp", "")),
        "created_at": _now(),
    }
    await _record("braintree_webhook_events", doc)
    return {"status": "accepted", "provider": "braintree", "event": doc}
