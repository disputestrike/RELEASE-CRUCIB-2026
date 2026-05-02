"""PayPal billing service — Orders API v2 (one-time) + Subscriptions API v1 (recurring).

Environment variables required:
  PAYPAL_CLIENT_ID      – from PayPal Developer Dashboard (app client id)
  PAYPAL_CLIENT_SECRET  – from PayPal Developer Dashboard (app secret)
  PAYPAL_MODE           – "sandbox" or "live"  (default: live)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Constants / config helpers
# ---------------------------------------------------------------------------

PAYPAL_LIVE_URL = "https://api-m.paypal.com"
PAYPAL_SANDBOX_URL = "https://api-m.sandbox.paypal.com"

DEFAULT_BUSINESS_ID = "biz_starlight"
DEFAULT_PRODUCT_ID = "prod_crucible_ai_credits"
DEFAULT_BUSINESS_SLUG = "starlight"
DEFAULT_PRODUCT_SLUG = "crucible-ai"
DEFAULT_LEGAL_ENTITY = "Starlight Global LLC"
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "approval_pending", "approved"}


def paypal_configured() -> bool:
    return bool(
        os.environ.get("PAYPAL_CLIENT_ID")
        and os.environ.get("PAYPAL_CLIENT_SECRET")
    )


def paypal_base_url() -> str:
    mode = (os.environ.get("PAYPAL_MODE") or "live").lower()
    return PAYPAL_SANDBOX_URL if mode == "sandbox" else PAYPAL_LIVE_URL


def paypal_client_id() -> str:
    return os.environ.get("PAYPAL_CLIENT_ID") or ""


def required_paypal_config() -> List[str]:
    return [
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_MODE",
        "APP_URL",
        "DATABASE_URL",
    ]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def coerce_user_id(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "guest")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "guest")


def coerce_user_email(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("email") or "")
    return str(getattr(user, "email", "") or "")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BillingError(Exception):
    status_code = 400
    code = "billing_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code

    def detail(self) -> Dict[str, Any]:
        return {"error": self.code, "message": str(self)}


class BillingConfigError(BillingError):
    status_code = 503
    code = "paypal_requires_config"

    def detail(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": str(self),
            "required_config": required_paypal_config(),
        }


# ---------------------------------------------------------------------------
# PayPal REST API client (httpx, async)
# ---------------------------------------------------------------------------

async def _get_access_token() -> str:
    if not paypal_configured():
        raise BillingConfigError("PayPal is not configured")
    client_id = os.environ["PAYPAL_CLIENT_ID"]
    client_secret = os.environ["PAYPAL_CLIENT_SECRET"]
    base = paypal_base_url()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise BillingError(
            f"PayPal auth failed: {resp.text[:200]}",
            code="paypal_auth_failed",
            status_code=502,
        )
    return resp.json().get("access_token", "")


async def _paypal_post(path: str, payload: Dict[str, Any], *, idempotency_key: str | None = None) -> Dict[str, Any]:
    token = await _get_access_token()
    base = paypal_base_url()
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if idempotency_key:
        headers["PayPal-Request-Id"] = idempotency_key
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{base}{path}", json=payload, headers=headers)
    if resp.status_code not in (200, 201, 202, 204):
        raise BillingError(
            f"PayPal API error {resp.status_code}: {resp.text[:400]}",
            code="paypal_api_error",
            status_code=502,
        )
    return resp.json() if resp.content else {}


async def _paypal_get(path: str) -> Dict[str, Any]:
    token = await _get_access_token()
    base = paypal_base_url()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{base}{path}", headers=headers)
    if resp.status_code not in (200, 201):
        raise BillingError(
            f"PayPal GET error {resp.status_code}: {resp.text[:400]}",
            code="paypal_api_error",
            status_code=502,
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Amount / helpers
# ---------------------------------------------------------------------------

def _amount(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise BillingError("Invalid price amount", code="invalid_price") from exc


def _estimate_period_end(interval: Optional[str]) -> str:
    days = 365 if interval in ("yearly", "year", "annual") else 31
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# DB catalog helpers (same structure as before, provider-agnostic)
# ---------------------------------------------------------------------------

async def upsert_doc(collection: Any, query: Dict[str, Any], doc: Dict[str, Any]) -> Dict[str, Any]:
    existing = await collection.find_one(query)
    payload = dict(doc)
    payload.setdefault("created_at", now_iso())
    payload["updated_at"] = now_iso()
    if existing:
        cleaned = {k: v for k, v in payload.items() if v is not None or existing.get(k) is None}
        merged = {**existing, **cleaned, "created_at": existing.get("created_at") or payload["created_at"]}
        await collection.update_one({"id": existing.get("id")}, {"$set": merged})
        return merged
    await collection.insert_one(payload)
    return payload


async def ensure_catalog(db: Any) -> Dict[str, Any]:
    from backend import pricing_plans

    business = await upsert_doc(
        db.businesses,
        {"id": DEFAULT_BUSINESS_ID},
        {
            "id": DEFAULT_BUSINESS_ID,
            "name": "Starlight",
            "slug": DEFAULT_BUSINESS_SLUG,
            "legal_entity_name": DEFAULT_LEGAL_ENTITY,
            "active": True,
        },
    )
    product = await upsert_doc(
        db.products,
        {"id": DEFAULT_PRODUCT_ID},
        {
            "id": DEFAULT_PRODUCT_ID,
            "business_id": business["id"],
            "name": "Crucible AI Credits",
            "slug": DEFAULT_PRODUCT_SLUG,
            "description": "Proof-gated build credits for Crucible AI.",
            "active": True,
        },
    )
    seeded_prices: List[Dict[str, Any]] = []
    for slug, plan in pricing_plans.TOKEN_BUNDLES.items():
        amount = _amount(plan.get("price"))
        base: Dict[str, Any] = {
            "product_id": product["id"],
            "product_slug": product["slug"],
            "business_id": business["id"],
            "name": str(plan.get("name") or slug.title()),
            "amount": float(amount),
            "currency": "USD",
            "active": True,
            "credits": int(plan.get("credits") or int(plan["tokens"] / pricing_plans.CREDITS_PER_TOKEN)),
            "tokens": int(plan.get("tokens") or 0),
            "metadata": {"source": "pricing_plans.py", "plan_slug": slug},
        }
        seeded_prices.append(
            await upsert_doc(
                db.prices,
                {"id": f"price_{slug}_one_time"},
                {**base, "id": f"price_{slug}_one_time", "slug": f"{slug}-one-time",
                 "billing_type": "one_time", "interval": None, "paypal_plan_id": None},
            )
        )
        seeded_prices.append(
            await upsert_doc(
                db.prices,
                {"id": f"price_{slug}_monthly"},
                {**base, "id": f"price_{slug}_monthly", "slug": f"{slug}-monthly",
                 "billing_type": "recurring", "interval": "monthly", "paypal_plan_id": None},
            )
        )
        annual_amount = pricing_plans.ANNUAL_PRICES.get(slug)
        if annual_amount is not None:
            seeded_prices.append(
                await upsert_doc(
                    db.prices,
                    {"id": f"price_{slug}_yearly"},
                    {**base, "id": f"price_{slug}_yearly", "slug": f"{slug}-yearly",
                     "billing_type": "recurring", "interval": "yearly",
                     "amount": float(_amount(annual_amount)), "paypal_plan_id": None},
                )
            )
    return {"business": business, "product": product, "prices": seeded_prices}


async def list_active_prices(db: Any) -> List[Dict[str, Any]]:
    await ensure_catalog(db)
    prices = await db.prices.find({}).sort("amount", 1).to_list(200)
    return [p for p in prices if p.get("active") is True]


async def find_price(
    db: Any,
    *,
    price_id: Optional[str] = None,
    product_id: Optional[str] = None,
    billing_type: Optional[str] = None,
) -> Dict[str, Any]:
    await ensure_catalog(db)
    price = None
    if price_id:
        price = await db.prices.find_one({"id": price_id})
        if not price and not price_id.startswith("price_"):
            price = await db.prices.find_one({"slug": price_id})
    elif product_id:
        query: Dict[str, Any] = {"product_id": product_id}
        if billing_type:
            query["billing_type"] = billing_type
        candidates = await db.prices.find(query).sort("amount", 1).to_list(50)
        price = next((p for p in candidates if p.get("active") is True), None)
    if not price or not price.get("active"):
        raise BillingError("Active price/plan not found", code="price_not_found", status_code=404)
    if billing_type and price.get("billing_type") != billing_type:
        raise BillingError(f"Price must be {billing_type}", code="invalid_billing_type")
    return price


# ---------------------------------------------------------------------------
# PayPal Orders (one-time payments)
# ---------------------------------------------------------------------------

async def create_paypal_order(
    db: Any,
    user: Any,
    *,
    price_id: Optional[str] = None,
    product_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a PayPal Order and return the order_id for the frontend to approve."""
    if not paypal_configured():
        raise BillingConfigError("PayPal is not configured")
    user_id = coerce_user_id(user)
    # Idempotency check
    if idempotency_key:
        existing = await db.orders.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key, "status": "success"}
        )
        if existing:
            return {"status": "success", "order": existing, "idempotent_replay": True, "paypal_order_id": existing.get("paypal_order_id")}

    price = await find_price(db, price_id=price_id, product_id=product_id, billing_type="one_time")
    amount = _amount(price["amount"])
    app_url = os.environ.get("APP_URL", "https://www.crucibai.com")
    idem_key = idempotency_key or f"order_{user_id}_{price['id']}_{uuid.uuid4().hex[:12]}"

    paypal_resp = await _paypal_post(
        "/v2/checkout/orders",
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": idem_key,
                    "description": price.get("name", "Crucible AI Credits"),
                    "amount": {
                        "currency_code": price.get("currency", "USD"),
                        "value": f"{amount:.2f}",
                    },
                    "custom_id": price["id"],
                }
            ],
            "application_context": {
                "brand_name": "Starlight Global LLC",
                "landing_page": "LOGIN",
                "user_action": "PAY_NOW",
                "return_url": f"{app_url}/billing?paypal_success=1",
                "cancel_url": f"{app_url}/billing?paypal_cancel=1",
            },
        },
        idempotency_key=idem_key,
    )

    paypal_order_id = paypal_resp.get("id")
    # Persist a pending order record
    pending_order = {
        "id": f"order_{uuid.uuid4().hex[:24]}",
        "user_id": user_id,
        "product_id": price["product_id"],
        "price_id": price["id"],
        "amount": float(amount),
        "currency": price.get("currency", "USD"),
        "status": "pending",
        "payment_type": "one_time",
        "paypal_order_id": paypal_order_id,
        "idempotency_key": idem_key,
        "metadata": {
            "price_slug": price.get("slug"),
            "credits": price.get("credits"),
            "tokens": price.get("tokens"),
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.orders.insert_one(pending_order)
    return {
        "paypal_order_id": paypal_order_id,
        "order": pending_order,
        "approve_url": next(
            (link["href"] for link in paypal_resp.get("links", []) if link.get("rel") == "approve"),
            None,
        ),
    }


async def capture_paypal_order(
    db: Any,
    user: Any,
    *,
    paypal_order_id: str,
) -> Dict[str, Any]:
    """Capture an approved PayPal order and grant credits."""
    if not paypal_configured():
        raise BillingConfigError("PayPal is not configured")
    user_id = coerce_user_id(user)
    local_order = await db.orders.find_one({"paypal_order_id": paypal_order_id, "user_id": user_id})
    if local_order and local_order.get("status") == "success":
        return {"status": "success", "order": local_order, "idempotent_replay": True}

    capture_resp = await _paypal_post(f"/v2/checkout/orders/{paypal_order_id}/capture", {})
    capture_status = capture_resp.get("status", "")
    capture_units = capture_resp.get("purchase_units", [])
    paypal_capture_id = None
    if capture_units:
        captures = capture_units[0].get("payments", {}).get("captures", [])
        if captures:
            paypal_capture_id = captures[0].get("id")

    success = capture_status == "COMPLETED"
    update = {
        "status": "success" if success else "failed",
        "paypal_capture_id": paypal_capture_id,
        "updated_at": now_iso(),
    }
    if local_order:
        await db.orders.update_one({"id": local_order["id"]}, {"$set": update})
        order = {**local_order, **update}
    else:
        # Order created without pre-registration (e.g. redirect flow)
        order = {
            "id": f"order_{uuid.uuid4().hex[:24]}",
            "user_id": user_id,
            "product_id": DEFAULT_PRODUCT_ID,
            "price_id": None,
            "amount": 0.0,
            "currency": "USD",
            **update,
            "payment_type": "one_time",
            "paypal_order_id": paypal_order_id,
            "metadata": {},
            "created_at": now_iso(),
        }
        await db.orders.insert_one(order)

    if not success:
        raise BillingError("PayPal capture failed", code="paypal_capture_failed", status_code=402)

    await grant_paid_access(db, user_id=user_id, product_id=order["product_id"], source_id=order["id"])
    if order.get("price_id"):
        price = await db.prices.find_one({"id": order["price_id"]})
        if price:
            await _grant_credits_if_present(db, user_id, price, order)
    return {"status": "success", "order": order, "paypal_capture_id": paypal_capture_id}


# ---------------------------------------------------------------------------
# PayPal Subscriptions (recurring)
# ---------------------------------------------------------------------------

async def ensure_paypal_plan(
    db: Any,
    price: Dict[str, Any],
) -> str:
    """Return an existing paypal_plan_id from DB or create one via PayPal API."""
    existing_plan_id = price.get("paypal_plan_id")
    if existing_plan_id:
        return existing_plan_id

    interval = price.get("interval", "monthly")
    interval_unit = "YEAR" if interval in ("yearly", "year", "annual") else "MONTH"
    amount = _amount(price["amount"])

    # Create a PayPal product first (or use cached)
    product_resp = await _paypal_post(
        "/v1/catalogs/products",
        {
            "name": "Crucible AI Credits",
            "description": "Build credits for Crucible AI by Starlight Global LLC",
            "type": "SERVICE",
            "category": "SOFTWARE",
        },
        idempotency_key=f"pp_product_{DEFAULT_PRODUCT_ID}",
    )
    paypal_product_id = product_resp.get("id")

    # Create billing plan
    plan_resp = await _paypal_post(
        "/v1/billing/plans",
        {
            "product_id": paypal_product_id,
            "name": price.get("name", "Crucible AI"),
            "description": f"{price.get('name')} — {price.get('credits')} credits",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {"interval_unit": interval_unit, "interval_count": 1},
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": f"{amount:.2f}",
                            "currency_code": price.get("currency", "USD"),
                        }
                    },
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3,
            },
        },
        idempotency_key=f"pp_plan_{price['id']}",
    )
    plan_id = plan_resp.get("id")
    if plan_id:
        await db.prices.update_one({"id": price["id"]}, {"$set": {"paypal_plan_id": plan_id, "updated_at": now_iso()}})
    return plan_id or ""


async def create_paypal_subscription(
    db: Any,
    user: Any,
    *,
    price_id: Optional[str] = None,
    product_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a PayPal subscription and return the subscription_id + approve URL."""
    if not paypal_configured():
        raise BillingConfigError("PayPal is not configured")
    user_id = coerce_user_id(user)
    email = coerce_user_email(user)

    if idempotency_key:
        existing = await db.subscriptions.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key}
        )
        if existing:
            return {"status": existing.get("status"), "subscription": existing, "idempotent_replay": True}

    price = await find_price(db, price_id=price_id, product_id=product_id, billing_type="recurring")
    plan_id = await ensure_paypal_plan(db, price)
    if not plan_id:
        raise BillingError("Could not create PayPal billing plan", code="paypal_plan_failed", status_code=502)

    app_url = os.environ.get("APP_URL", "https://www.crucibai.com")
    idem_key = idempotency_key or f"sub_{user_id}_{price['id']}_{uuid.uuid4().hex[:12]}"

    sub_payload: Dict[str, Any] = {
        "plan_id": plan_id,
        "custom_id": user_id,
        "application_context": {
            "brand_name": "Starlight Global LLC",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": f"{app_url}/billing?paypal_sub_success=1",
            "cancel_url": f"{app_url}/billing?paypal_sub_cancel=1",
        },
    }
    if email:
        sub_payload["subscriber"] = {"email_address": email}

    sub_resp = await _paypal_post("/v1/billing/subscriptions", sub_payload, idempotency_key=idem_key)
    paypal_sub_id = sub_resp.get("id")
    approve_url = next(
        (link["href"] for link in sub_resp.get("links", []) if link.get("rel") == "approve"),
        None,
    )

    doc = {
        "id": f"sub_{uuid.uuid4().hex}",
        "user_id": user_id,
        "product_id": price["product_id"],
        "price_id": price["id"],
        "plan_id": price["id"],
        "paypal_subscription_id": paypal_sub_id,
        "paypal_plan_id": plan_id,
        "status": "approval_pending",
        "current_period_start": now_iso(),
        "current_period_end": _estimate_period_end(price.get("interval")),
        "cancel_at_period_end": False,
        "canceled_at": None,
        "idempotency_key": idem_key,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.subscriptions.insert_one(doc)
    return {"status": "approval_pending", "subscription": doc, "approve_url": approve_url, "paypal_subscription_id": paypal_sub_id}


async def activate_paypal_subscription(
    db: Any,
    user: Any,
    *,
    paypal_subscription_id: str,
) -> Dict[str, Any]:
    """Called after user approves — verify with PayPal and activate locally."""
    if not paypal_configured():
        raise BillingConfigError("PayPal is not configured")
    user_id = coerce_user_id(user)
    sub_resp = await _paypal_get(f"/v1/billing/subscriptions/{paypal_subscription_id}")
    pp_status = sub_resp.get("status", "").upper()
    active = pp_status in ("ACTIVE", "APPROVED")

    local = await db.subscriptions.find_one(
        {"paypal_subscription_id": paypal_subscription_id, "user_id": user_id}
    )
    update = {
        "status": "active" if active else pp_status.lower(),
        "updated_at": now_iso(),
    }
    if local:
        await db.subscriptions.update_one({"id": local["id"]}, {"$set": update})
        sub = {**local, **update}
    else:
        sub = {
            "id": f"sub_{uuid.uuid4().hex}",
            "user_id": user_id,
            "product_id": DEFAULT_PRODUCT_ID,
            "price_id": None,
            "plan_id": None,
            "paypal_subscription_id": paypal_subscription_id,
            **update,
            "current_period_start": now_iso(),
            "current_period_end": _estimate_period_end("monthly"),
            "cancel_at_period_end": False,
            "canceled_at": None,
            "created_at": now_iso(),
        }
        await db.subscriptions.insert_one(sub)

    if active:
        await grant_paid_access(db, user_id=user_id, product_id=sub["product_id"], source_id=sub["id"])
    return {"status": sub["status"], "subscription": sub}


async def cancel_paypal_subscription(
    db: Any,
    user: Any,
    *,
    subscription_id: str,
    cancel_at_period_end: bool = True,
) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    sub = await db.subscriptions.find_one({"id": subscription_id})
    if not sub or sub.get("user_id") != user_id:
        raise BillingError("Subscription not found", code="subscription_not_found", status_code=404)
    paypal_sub_id = sub.get("paypal_subscription_id")
    if paypal_sub_id:
        try:
            await _paypal_post(
                f"/v1/billing/subscriptions/{paypal_sub_id}/cancel",
                {"reason": "Canceled by user"},
            )
        except Exception as exc:
            raise BillingError(
                f"PayPal cancellation failed: {exc}",
                code="paypal_cancellation_failed",
                status_code=502,
            ) from exc
    update = {
        "status": "canceled",
        "cancel_at_period_end": bool(cancel_at_period_end),
        "canceled_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": update})
    if not cancel_at_period_end:
        await db.entitlements.update_many(
            {"user_id": user_id, "product_id": sub.get("product_id")},
            {"$set": {"active": False}},
        )
    return {"subscription": {**sub, **update}}


# ---------------------------------------------------------------------------
# Access / entitlements / credits
# ---------------------------------------------------------------------------

async def grant_paid_access(db: Any, *, user_id: str, product_id: str, source_id: str) -> None:
    existing = await db.entitlements.find_one({"user_id": user_id, "product_id": product_id, "source_id": source_id})
    if existing:
        return
    await db.entitlements.insert_one({
        "id": f"ent_{uuid.uuid4().hex}",
        "user_id": user_id,
        "product_id": product_id,
        "source_id": source_id,
        "access_type": "paid",
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })


async def _grant_credits_if_present(db: Any, user_id: str, price: Dict[str, Any], order: Dict[str, Any]) -> None:
    credits = int(price.get("credits") or 0)
    tokens = int(price.get("tokens") or credits * 1000)
    if credits <= 0 and tokens <= 0:
        return
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"token_balance": tokens, "credit_balance": credits}},
    )
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tokens": tokens,
        "credits": credits,
        "type": "purchase",
        "provider": "paypal",
        "bundle": price.get("metadata", {}).get("plan_slug") or price.get("slug"),
        "price": order.get("amount"),
        "transaction_id": order.get("paypal_capture_id") or order.get("paypal_order_id"),
        "order_id": order.get("id"),
        "created_at": now_iso(),
    })


async def user_has_access(db: Any, user_id: str, product_id: str) -> bool:
    user = await db.users.find_one({"id": user_id})
    if user and (user.get("admin") or user.get("is_admin") or user.get("role") == "admin"):
        return True
    entitlement_rows = await db.entitlements.find({"user_id": user_id, "product_id": product_id}).to_list(100)
    if any(r.get("active") for r in entitlement_rows):
        return True
    order = await db.orders.find_one({"user_id": user_id, "product_id": product_id, "status": "success", "payment_type": "one_time"})
    if order:
        return True
    subs = await db.subscriptions.find({"user_id": user_id, "product_id": product_id}).to_list(100)
    now = datetime.now(timezone.utc)
    for sub in subs:
        status = str(sub.get("status") or "").lower()
        if status not in ACTIVE_SUBSCRIPTION_STATUSES and not sub.get("cancel_at_period_end"):
            continue
        end_raw = sub.get("current_period_end")
        if sub.get("cancel_at_period_end") and end_raw:
            try:
                end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
                if end >= now:
                    return True
            except Exception:
                return True
        elif status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True
    return False


# ---------------------------------------------------------------------------
# Overview / history (for Billing page)
# ---------------------------------------------------------------------------

async def billing_overview(db: Any, user: Any) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    catalog = await ensure_catalog(db)
    customer = await db.customers.find_one({"user_id": user_id})
    subscriptions = await db.subscriptions.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    prices = await list_active_prices(db)
    return {
        "provider": "paypal",
        "paypal_client_id": paypal_client_id(),
        "customer": customer,
        "active_subscriptions": [
            s for s in subscriptions
            if str(s.get("status", "")).lower() in ACTIVE_SUBSCRIPTION_STATUSES or s.get("cancel_at_period_end")
        ],
        "subscriptions": subscriptions,
        "products": [catalog["product"]],
        "plans": prices,
        "prices": prices,
        "billing_history": orders,
        "cancellable_plans": [s["id"] for s in subscriptions if str(s.get("status", "")).lower() in ACTIVE_SUBSCRIPTION_STATUSES],
        "changeable_plans": [p for p in prices if p.get("billing_type") == "recurring"],
    }


async def billing_history(db: Any, user: Any) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(200)
    return {"history": orders, "count": len(orders)}


# ---------------------------------------------------------------------------
# Webhook (PayPal IPN / Webhook Events)
# ---------------------------------------------------------------------------

async def process_webhook(db: Any, event: Dict[str, Any], *, headers: Dict[str, str]) -> Dict[str, Any]:
    """Process a PayPal webhook event."""
    import hashlib
    event_id = event.get("id") or f"ppwh_{uuid.uuid4().hex}"
    existing = await db.billing_events.find_one({"id": event_id})
    if existing and existing.get("processed_at"):
        return {"status": "duplicate", "event": existing}
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})
    doc = {
        "id": event_id,
        "event_provider": "paypal",
        "event_type": event_type,
        "payload": event,
        "processed_at": None,
        "created_at": now_iso(),
    }
    if existing:
        await db.billing_events.update_one({"id": event_id}, {"$set": doc})
    else:
        await db.billing_events.insert_one(doc)

    # Handle subscription events
    if "BILLING.SUBSCRIPTION" in event_type:
        sub_id = resource.get("id")
        if sub_id:
            local = await db.subscriptions.find_one({"paypal_subscription_id": sub_id})
            if local:
                status_map = {
                    "BILLING.SUBSCRIPTION.ACTIVATED": "active",
                    "BILLING.SUBSCRIPTION.CANCELLED": "canceled",
                    "BILLING.SUBSCRIPTION.EXPIRED": "expired",
                    "BILLING.SUBSCRIPTION.SUSPENDED": "suspended",
                    "BILLING.SUBSCRIPTION.PAYMENT.FAILED": "past_due",
                }
                new_status = status_map.get(event_type, local.get("status"))
                await db.subscriptions.update_one({"id": local["id"]}, {"$set": {"status": new_status, "updated_at": now_iso()}})

    # Handle payment capture events
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture_id = resource.get("id")
        if capture_id:
            order = await db.orders.find_one({"paypal_capture_id": capture_id})
            if order and order.get("status") != "success":
                await db.orders.update_one({"id": order["id"]}, {"$set": {"status": "success", "updated_at": now_iso()}})

    doc["processed_at"] = now_iso()
    await db.billing_events.update_one({"id": event_id}, {"$set": doc})
    return {"status": "processed", "event": doc}
