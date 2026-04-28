from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_BUSINESS_ID = "biz_starlight"
DEFAULT_PRODUCT_ID = "prod_crucible_ai_credits"
DEFAULT_BUSINESS_SLUG = "starlight"
DEFAULT_PRODUCT_SLUG = "crucible-ai"
DEFAULT_LEGAL_ENTITY = "Starlight LLC"
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "pending", "past_due"}


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


def braintree_configured() -> bool:
    return bool(
        os.environ.get("BRAINTREE_MERCHANT_ID")
        and os.environ.get("BRAINTREE_PUBLIC_KEY")
        and os.environ.get("BRAINTREE_PRIVATE_KEY")
    )


def required_braintree_config() -> List[str]:
    return [
        "BRAINTREE_ENVIRONMENT",
        "BRAINTREE_MERCHANT_ID",
        "BRAINTREE_PUBLIC_KEY",
        "BRAINTREE_PRIVATE_KEY",
        "BRAINTREE_MERCHANT_ACCOUNT_ID",
        "APP_URL",
        "DATABASE_URL",
    ]


def default_merchant_account_id() -> Optional[str]:
    return os.environ.get("BRAINTREE_MERCHANT_ACCOUNT_ID") or None


def plan_env_key(plan_slug: str, interval: str) -> str:
    suffix = f"{plan_slug}_{interval}".upper().replace("-", "_")
    return f"BRAINTREE_PLAN_{suffix}"


def make_gateway():
    if not braintree_configured():
        raise BillingConfigError("Braintree is not configured")
    try:
        import braintree
    except Exception as exc:  # pragma: no cover - dependency guard
        raise BillingConfigError(f"Braintree SDK is not installed: {exc}") from exc

    env_name = (os.environ.get("BRAINTREE_ENVIRONMENT") or "sandbox").lower()
    environment = (
        braintree.Environment.Production
        if env_name == "production"
        else braintree.Environment.Sandbox
    )
    return braintree.BraintreeGateway(
        braintree.Configuration(
            environment=environment,
            merchant_id=os.environ["BRAINTREE_MERCHANT_ID"],
            public_key=os.environ["BRAINTREE_PUBLIC_KEY"],
            private_key=os.environ["BRAINTREE_PRIVATE_KEY"],
        )
    )


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
    code = "braintree_requires_config"

    def detail(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": str(self),
            "required_config": required_braintree_config(),
        }


def _amount(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise BillingError("Invalid price amount", code="invalid_price") from exc


def _status(value: Any) -> str:
    raw = str(value or "").strip()
    if "." in raw:
        raw = raw.rsplit(".", 1)[-1]
    return raw.lower() or "unknown"


def _date_or_none(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).isoformat()
    return str(value)


def _estimate_period_end(interval: Optional[str]) -> str:
    days = 365 if interval == "yearly" else 31
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _payment_method_doc_from_gateway(
    payment_method: Any,
    *,
    user_id: str,
    customer_id: str,
    local_customer_id: str,
    is_default: bool,
) -> Dict[str, Any]:
    expiration_date = str(_first_attr(payment_method, "expiration_date") or "")
    exp_month = _first_attr(payment_method, "expiration_month")
    exp_year = _first_attr(payment_method, "expiration_year")
    if expiration_date and "/" in expiration_date:
        exp_month = exp_month or expiration_date.split("/", 1)[0]
        exp_year = exp_year or expiration_date.split("/", 1)[1]
    token = _first_attr(payment_method, "token", "payment_method_token")
    return {
        "id": f"pm_{uuid.uuid4().hex}",
        "user_id": user_id,
        "customer_id": local_customer_id,
        "braintree_customer_id": customer_id,
        "braintree_payment_method_token": token,
        "card_type": _first_attr(payment_method, "card_type", "cardType") or "card",
        "last4": _first_attr(payment_method, "last_4", "last4") or "",
        "expiration_month": str(exp_month or ""),
        "expiration_year": str(exp_year or ""),
        "is_default": bool(is_default),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def _braintree_plan_id_for(slug: str, interval: str, existing: Optional[str]) -> Optional[str]:
    return existing or os.environ.get(plan_env_key(slug, interval)) or None


async def upsert_doc(collection: Any, query: Dict[str, Any], doc: Dict[str, Any]) -> Dict[str, Any]:
    existing = await collection.find_one(query)
    payload = dict(doc)
    payload.setdefault("created_at", now_iso())
    payload["updated_at"] = now_iso()
    if existing:
        # Preserve migration/audit IDs such as existing Stripe IDs and dashboard-entered
        # Braintree plan IDs when the codebase seed has no replacement value.
        cleaned = {
            key: value
            for key, value in payload.items()
            if value is not None or existing.get(key) is None
        }
        merged = {**existing, **cleaned, "created_at": existing.get("created_at") or payload["created_at"]}
        await collection.update_one({"id": existing.get("id")}, {"$set": merged})
        return merged
    await collection.insert_one(payload)
    return payload


async def ensure_catalog(db: Any) -> Dict[str, Any]:
    """Create default Starlight/Crucible catalog docs from the approved pricing module.

    Existing database rows win: we only seed missing products/prices and we never
    trust frontend amount input.
    """
    from backend import pricing_plans

    business = await upsert_doc(
        db.businesses,
        {"id": DEFAULT_BUSINESS_ID},
        {
            "id": DEFAULT_BUSINESS_ID,
            "name": "Starlight",
            "slug": DEFAULT_BUSINESS_SLUG,
            "legal_entity_name": DEFAULT_LEGAL_ENTITY,
            "braintree_merchant_account_id": default_merchant_account_id(),
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
            "stripe_product_id": None,
            "stripe_price_id": None,
        },
    )
    seeded_prices = []
    for slug, plan in pricing_plans.TOKEN_BUNDLES.items():
        amount = _amount(plan.get("price"))
        base = {
            "product_id": product["id"],
            "product_slug": product["slug"],
            "business_id": business["id"],
            "name": str(plan.get("name") or slug.title()),
            "amount": float(amount),
            "currency": "USD",
            "active": True,
            "credits": int(plan.get("credits") or int(plan["tokens"] / pricing_plans.CREDITS_PER_TOKEN)),
            "tokens": int(plan.get("tokens") or 0),
            "stripe_price_id": None,
            "metadata": {"source": "pricing_plans.py", "plan_slug": slug},
        }
        seeded_prices.append(
            await upsert_doc(
                db.prices,
                {"id": f"price_{slug}_one_time"},
                {
                    **base,
                    "id": f"price_{slug}_one_time",
                    "slug": f"{slug}-one-time",
                    "billing_type": "one_time",
                    "interval": None,
                    "braintree_plan_id": None,
                },
            )
        )
        seeded_prices.append(
            await upsert_doc(
                db.prices,
                {"id": f"price_{slug}_monthly"},
                {
                    **base,
                    "id": f"price_{slug}_monthly",
                    "slug": f"{slug}-monthly",
                    "billing_type": "recurring",
                    "interval": "monthly",
                    "braintree_plan_id": _braintree_plan_id_for(slug, "monthly", None),
                },
            )
        )
        annual_amount = pricing_plans.ANNUAL_PRICES.get(slug)
        if annual_amount is not None:
            seeded_prices.append(
                await upsert_doc(
                    db.prices,
                    {"id": f"price_{slug}_yearly"},
                    {
                        **base,
                        "id": f"price_{slug}_yearly",
                        "slug": f"{slug}-yearly",
                        "billing_type": "recurring",
                        "interval": "yearly",
                        "amount": float(_amount(annual_amount)),
                        "braintree_plan_id": _braintree_plan_id_for(slug, "yearly", None),
                    },
                )
            )
    return {"business": business, "product": product, "prices": seeded_prices}


async def list_active_prices(db: Any) -> List[Dict[str, Any]]:
    await ensure_catalog(db)
    prices = await db.prices.find({}).sort("amount", 1).to_list(200)
    return [price for price in prices if price.get("active") is True]


async def find_price(
    db: Any,
    *,
    price_id: Optional[str] = None,
    product_id: Optional[str] = None,
    billing_type: Optional[str] = None,
) -> Dict[str, Any]:
    await ensure_catalog(db)
    if price_id:
        price = await db.prices.find_one({"id": price_id})
        if not price and not price_id.startswith("price_"):
            price = await db.prices.find_one({"slug": price_id})
    elif product_id:
        query = {"product_id": product_id}
        if billing_type:
            query["billing_type"] = billing_type
        candidates = await db.prices.find(query).sort("amount", 1).to_list(50)
        price = next((item for item in candidates if item.get("active") is True), None)
    else:
        price = None
    if not price or not price.get("active"):
        raise BillingError("Active price/plan not found", code="price_not_found", status_code=404)
    if billing_type and price.get("billing_type") != billing_type:
        raise BillingError(
            f"Price must be {billing_type}",
            code="invalid_billing_type",
            status_code=400,
        )
    return price


async def ensure_custom_credit_price(db: Any, credits: int) -> Dict[str, Any]:
    from backend import pricing_plans

    if credits < pricing_plans.CUSTOM_CREDIT_MIN or credits > pricing_plans.CUSTOM_CREDIT_MAX:
        raise BillingError(
            f"Credits must be between {pricing_plans.CUSTOM_CREDIT_MIN} and {pricing_plans.CUSTOM_CREDIT_MAX}",
            code="invalid_credit_amount",
        )
    if credits % pricing_plans.CUSTOM_CREDIT_STEP != 0:
        raise BillingError(
            f"Credits must be in {pricing_plans.CUSTOM_CREDIT_STEP}-credit increments",
            code="invalid_credit_amount",
        )
    catalog = await ensure_catalog(db)
    amount = _amount(Decimal(credits) * Decimal(str(pricing_plans.CUSTOM_CREDIT_PRICE)))
    tokens = credits * pricing_plans.CREDITS_PER_TOKEN
    return await upsert_doc(
        db.prices,
        {"id": f"price_custom_{credits}_one_time"},
        {
            "id": f"price_custom_{credits}_one_time",
            "product_id": catalog["product"]["id"],
            "product_slug": catalog["product"]["slug"],
            "business_id": catalog["business"]["id"],
            "name": f"{credits:,} credits",
            "slug": f"custom-{credits}-credits",
            "billing_type": "one_time",
            "interval": None,
            "amount": float(amount),
            "currency": "USD",
            "active": True,
            "credits": credits,
            "tokens": tokens,
            "braintree_plan_id": None,
            "stripe_price_id": None,
            "metadata": {"source": "pricing_plans.py", "plan_slug": "custom"},
        },
    )


async def find_or_create_customer(db: Any, gateway: Any, user: Any) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    email = coerce_user_email(user)
    existing = await db.customers.find_one({"user_id": user_id})
    if existing and existing.get("braintree_customer_id"):
        return existing

    request = {"email": email} if email else {}
    try:
        result = gateway.customer.create(request) if request else gateway.customer.create()
    except Exception as exc:
        raise BillingError(
            f"Braintree customer create failed: {exc}",
            code="braintree_customer_failed",
            status_code=502,
        ) from exc
    if not getattr(result, "is_success", False):
        raise BillingError(
            f"Braintree customer create rejected: {getattr(result, 'message', '') or getattr(result, 'errors', '')}",
            code="braintree_customer_failed",
            status_code=402,
        )
    braintree_customer = getattr(result, "customer", None)
    doc = {
        "id": existing.get("id") if existing else f"cust_{uuid.uuid4().hex}",
        "user_id": user_id,
        "email": email,
        "braintree_customer_id": getattr(braintree_customer, "id", None),
        "default_payment_method_token": existing.get("default_payment_method_token") if existing else None,
        "stripe_customer_id": existing.get("stripe_customer_id") if existing else None,
        "created_at": existing.get("created_at") if existing else now_iso(),
        "updated_at": now_iso(),
    }
    if existing:
        await db.customers.update_one({"id": existing["id"]}, {"$set": doc})
    else:
        await db.customers.insert_one(doc)
    return doc


async def generate_client_token(db: Any, gateway: Any, user: Any) -> Dict[str, Any]:
    customer = await find_or_create_customer(db, gateway, user)
    payload: Dict[str, Any] = {"customer_id": customer["braintree_customer_id"]}
    merchant_account_id = default_merchant_account_id()
    if merchant_account_id:
        payload["merchant_account_id"] = merchant_account_id
    return {
        "provider": "braintree",
        "client_token": gateway.client_token.generate(payload),
        "customer": customer,
    }


async def vault_payment_method(
    db: Any,
    gateway: Any,
    user: Any,
    payment_method_nonce: str,
    *,
    make_default: bool = True,
) -> Dict[str, Any]:
    if not payment_method_nonce:
        raise BillingError("paymentMethodNonce is required", code="nonce_required")
    user_id = coerce_user_id(user)
    customer = await find_or_create_customer(db, gateway, user)
    try:
        result = gateway.payment_method.create(
            {
                "customer_id": customer["braintree_customer_id"],
                "payment_method_nonce": payment_method_nonce,
                "options": {"make_default": make_default},
            }
        )
    except Exception as exc:
        raise BillingError(
            f"Braintree payment method failed: {exc}",
            code="braintree_payment_method_failed",
            status_code=502,
        ) from exc
    if not getattr(result, "is_success", False):
        raise BillingError(
            f"Braintree payment method rejected: {getattr(result, 'message', '') or getattr(result, 'errors', '')}",
            code="braintree_payment_method_failed",
            status_code=402,
        )
    payment_method = getattr(result, "payment_method", None)
    doc = _payment_method_doc_from_gateway(
        payment_method,
        user_id=user_id,
        customer_id=customer["braintree_customer_id"],
        local_customer_id=customer["id"],
        is_default=make_default,
    )
    if make_default:
        await db.payment_methods.update_many({"user_id": user_id}, {"$set": {"is_default": False}})
        await db.customers.update_one(
            {"id": customer["id"]},
            {"$set": {"default_payment_method_token": doc["braintree_payment_method_token"]}},
        )
    await db.payment_methods.insert_one(doc)
    return {"customer": customer, "payment_method": doc}


async def create_one_time_checkout(
    db: Any,
    gateway: Any,
    user: Any,
    *,
    product_id: Optional[str],
    price_id: Optional[str],
    payment_method_nonce: str,
    idempotency_key: Optional[str] = None,
    device_data: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    if idempotency_key:
        existing = await db.orders.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key, "status": "success"}
        )
        if existing:
            return {"status": "success", "order": existing, "idempotent_replay": True}
    price = await find_price(db, price_id=price_id, product_id=product_id, billing_type="one_time")
    product = await db.products.find_one({"id": price["product_id"]})
    business = await db.businesses.find_one({"id": product.get("business_id")}) if product else None
    vaulted = await vault_payment_method(db, gateway, user, payment_method_nonce, make_default=True)
    amount = _amount(price["amount"])
    order_id = f"order_{uuid.uuid4().hex[:24]}"
    sale_payload: Dict[str, Any] = {
        "amount": f"{amount:.2f}",
        "payment_method_token": vaulted["payment_method"]["braintree_payment_method_token"],
        "order_id": order_id,
        "options": {"submit_for_settlement": True},
    }
    merchant_account_id = (
        (business or {}).get("braintree_merchant_account_id")
        or default_merchant_account_id()
    )
    if merchant_account_id:
        sale_payload["merchant_account_id"] = merchant_account_id
    if device_data:
        sale_payload["device_data"] = device_data
    try:
        result = gateway.transaction.sale(sale_payload)
    except Exception as exc:
        raise BillingError(
            f"Braintree transaction failed: {exc}",
            code="braintree_transaction_failed",
            status_code=502,
        ) from exc
    tx = getattr(result, "transaction", None)
    status = "success" if getattr(result, "is_success", False) else "failed"
    order = {
        "id": order_id,
        "user_id": user_id,
        "product_id": price["product_id"],
        "price_id": price["id"],
        "amount": float(amount),
        "currency": price.get("currency", "USD"),
        "status": status,
        "payment_type": "one_time",
        "braintree_transaction_id": getattr(tx, "id", None),
        "braintree_subscription_id": None,
        "failure_reason": None if status == "success" else str(getattr(result, "errors", "")),
        "idempotency_key": idempotency_key,
        "metadata": {
            "price_slug": price.get("slug"),
            "credits": price.get("credits"),
            "tokens": price.get("tokens"),
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.orders.insert_one(order)
    await db.braintree_transactions.insert_one(
        {
            "id": f"bt_{uuid.uuid4().hex}",
            "provider": "braintree",
            "user_id": user_id,
            "order_id": order_id,
            "status": status,
            "transaction_id": order["braintree_transaction_id"],
            "transaction_status": _status(getattr(tx, "status", None)),
            "amount": f"{amount:.2f}",
            "created_at": now_iso(),
        }
    )
    if status != "success":
        raise BillingError(
            "Braintree rejected the transaction",
            code="braintree_transaction_failed",
            status_code=402,
        )
    await grant_paid_access(db, user_id=user_id, product_id=price["product_id"], source_id=order_id)
    await _grant_credits_if_present(db, user_id, price, order)
    return {"status": "success", "order": order, "payment_method": vaulted["payment_method"]}


async def _grant_credits_if_present(db: Any, user_id: str, price: Dict[str, Any], order: Dict[str, Any]) -> None:
    credits = int(price.get("credits") or 0)
    tokens = int(price.get("tokens") or credits * 1000)
    if credits <= 0 and tokens <= 0:
        return
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"token_balance": tokens, "credit_balance": credits}},
    )
    await db.token_ledger.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tokens": tokens,
            "credits": credits,
            "type": "purchase",
            "provider": "braintree",
            "bundle": price.get("metadata", {}).get("plan_slug") or price.get("slug"),
            "price": order.get("amount"),
            "transaction_id": order.get("braintree_transaction_id"),
            "order_id": order.get("id"),
            "created_at": now_iso(),
        }
    )


async def create_subscription_checkout(
    db: Any,
    gateway: Any,
    user: Any,
    *,
    product_id: Optional[str],
    price_id: Optional[str],
    payment_method_nonce: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    if idempotency_key:
        existing = await db.subscriptions.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key}
        )
        if existing:
            return {"status": existing.get("status"), "subscription": existing, "idempotent_replay": True}
    price = await find_price(db, price_id=price_id, product_id=product_id, billing_type="recurring")
    if not price.get("braintree_plan_id"):
        raise BillingError(
            "Recurring price is missing braintree_plan_id. Configure the matching Braintree plan before checkout.",
            code="missing_braintree_plan_id",
            status_code=409,
        )
    product = await db.products.find_one({"id": price["product_id"]})
    business = await db.businesses.find_one({"id": product.get("business_id")}) if product else None
    vaulted = await vault_payment_method(db, gateway, user, payment_method_nonce, make_default=True)
    amount = _amount(price["amount"])
    payload: Dict[str, Any] = {
        "payment_method_token": vaulted["payment_method"]["braintree_payment_method_token"],
        "plan_id": price["braintree_plan_id"],
        "price": f"{amount:.2f}",
        "options": {"start_immediately": True},
    }
    merchant_account_id = (
        (business or {}).get("braintree_merchant_account_id")
        or default_merchant_account_id()
    )
    if merchant_account_id:
        payload["merchant_account_id"] = merchant_account_id
    try:
        result = gateway.subscription.create(payload)
    except Exception as exc:
        raise BillingError(
            f"Braintree subscription failed: {exc}",
            code="braintree_subscription_failed",
            status_code=502,
        ) from exc
    if not getattr(result, "is_success", False):
        raise BillingError(
            f"Braintree subscription rejected: {getattr(result, 'message', '') or getattr(result, 'errors', '')}",
            code="braintree_subscription_failed",
            status_code=402,
        )
    sub_obj = getattr(result, "subscription", None)
    doc = subscription_doc_from_gateway(
        sub_obj,
        user_id=user_id,
        product_id=price["product_id"],
        price=price,
        payment_method_token=vaulted["payment_method"]["braintree_payment_method_token"],
        idempotency_key=idempotency_key,
    )
    await db.subscriptions.insert_one(doc)
    await grant_paid_access(db, user_id=user_id, product_id=price["product_id"], source_id=doc["id"])
    first_tx = None
    transactions = getattr(sub_obj, "transactions", None) or []
    if transactions:
        first_tx = transactions[0]
        order = order_doc_from_transaction(
            first_tx,
            user_id=user_id,
            product_id=price["product_id"],
            price_id=price["id"],
            payment_type="subscription_initial",
            subscription_id=doc["braintree_subscription_id"],
        )
        await db.orders.insert_one(order)
    return {
        "status": doc["status"],
        "subscription": doc,
        "payment_method": vaulted["payment_method"],
        "initial_transaction_id": getattr(first_tx, "id", None),
    }


def subscription_doc_from_gateway(
    sub_obj: Any,
    *,
    user_id: str,
    product_id: str,
    price: Dict[str, Any],
    payment_method_token: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    sub_id = _first_attr(sub_obj, "id") or f"local_{uuid.uuid4().hex}"
    interval = price.get("interval")
    period_start = _date_or_none(_first_attr(sub_obj, "billing_period_start_date")) or now_iso()
    period_end = (
        _date_or_none(_first_attr(sub_obj, "billing_period_end_date", "paid_through_date"))
        or _estimate_period_end(interval)
    )
    return {
        "id": f"sub_{uuid.uuid4().hex}",
        "user_id": user_id,
        "product_id": product_id,
        "price_id": price["id"],
        "plan_id": price["id"],
        "braintree_subscription_id": sub_id,
        "braintree_payment_method_token": payment_method_token,
        "status": _status(_first_attr(sub_obj, "status")) or "active",
        "current_period_start": period_start,
        "current_period_end": period_end,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "idempotency_key": idempotency_key,
        "stripe_subscription_id": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def order_doc_from_transaction(
    tx: Any,
    *,
    user_id: str,
    product_id: str,
    price_id: Optional[str],
    payment_type: str,
    subscription_id: Optional[str] = None,
) -> Dict[str, Any]:
    tx_id = _first_attr(tx, "id") or f"local_tx_{uuid.uuid4().hex}"
    amount = _amount(_first_attr(tx, "amount") or "0")
    return {
        "id": f"order_{uuid.uuid4().hex[:24]}",
        "user_id": user_id,
        "product_id": product_id,
        "price_id": price_id,
        "amount": float(amount),
        "currency": _first_attr(tx, "currency_iso_code") or "USD",
        "status": "success" if _status(_first_attr(tx, "status")) in {"settled", "settling", "submitted_for_settlement", "authorized"} else _status(_first_attr(tx, "status")),
        "payment_type": payment_type,
        "braintree_transaction_id": tx_id,
        "braintree_subscription_id": subscription_id,
        "failure_reason": None,
        "metadata": {},
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


async def grant_paid_access(db: Any, *, user_id: str, product_id: str, source_id: str) -> None:
    existing = await db.entitlements.find_one(
        {"user_id": user_id, "product_id": product_id, "source_id": source_id}
    )
    if existing:
        return
    await db.entitlements.insert_one(
        {
            "id": f"ent_{uuid.uuid4().hex}",
            "user_id": user_id,
            "product_id": product_id,
            "source_id": source_id,
            "access_type": "paid",
            "active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )


async def user_has_access(db: Any, user_id: str, product_id: str) -> bool:
    user = await db.users.find_one({"id": user_id})
    if user and (user.get("admin") or user.get("is_admin") or user.get("role") == "admin"):
        return True
    entitlement_rows = await db.entitlements.find(
        {"user_id": user_id, "product_id": product_id}
    ).to_list(100)
    manual = next((row for row in entitlement_rows if row.get("active") is True), None)
    if manual:
        return True
    order = await db.orders.find_one(
        {"user_id": user_id, "product_id": product_id, "status": "success", "payment_type": "one_time"}
    )
    if order:
        return True
    subs = await db.subscriptions.find(
        {"user_id": user_id, "product_id": product_id}
    ).to_list(100)
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


async def billing_overview(db: Any, user: Any) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    catalog = await ensure_catalog(db)
    customer = await db.customers.find_one({"user_id": user_id})
    payment_method = await db.payment_methods.find_one({"user_id": user_id, "is_default": True})
    subscriptions = await db.subscriptions.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    prices = await list_active_prices(db)
    return {
        "provider": "braintree",
        "customer": customer,
        "active_subscriptions": [
            sub for sub in subscriptions if str(sub.get("status", "")).lower() in ACTIVE_SUBSCRIPTION_STATUSES or sub.get("cancel_at_period_end")
        ],
        "subscriptions": subscriptions,
        "products": [catalog["product"]],
        "plans": prices,
        "prices": prices,
        "default_payment_method": payment_method,
        "billing_history": orders,
        "cancellable_plans": [sub["id"] for sub in subscriptions if str(sub.get("status", "")).lower() in ACTIVE_SUBSCRIPTION_STATUSES],
        "changeable_plans": [price for price in prices if price.get("billing_type") == "recurring"],
    }


async def update_default_payment_method(
    db: Any,
    gateway: Any,
    user: Any,
    *,
    payment_method_nonce: str,
) -> Dict[str, Any]:
    vaulted = await vault_payment_method(db, gateway, user, payment_method_nonce, make_default=True)
    user_id = coerce_user_id(user)
    active_subs = await db.subscriptions.find({"user_id": user_id}).to_list(100)
    updated = []
    for sub in active_subs:
        if str(sub.get("status", "")).lower() not in ACTIVE_SUBSCRIPTION_STATUSES:
            continue
        braintree_sub_id = sub.get("braintree_subscription_id")
        if not braintree_sub_id:
            continue
        try:
            result = gateway.subscription.update(
                braintree_sub_id,
                {"payment_method_token": vaulted["payment_method"]["braintree_payment_method_token"]},
            )
            if getattr(result, "is_success", False):
                await db.subscriptions.update_one(
                    {"id": sub["id"]},
                    {"$set": {"braintree_payment_method_token": vaulted["payment_method"]["braintree_payment_method_token"]}},
                )
                updated.append(sub["id"])
        except Exception:
            continue
    return {"payment_method": vaulted["payment_method"], "subscriptions_updated": updated}


async def change_subscription_plan(
    db: Any,
    gateway: Any,
    user: Any,
    *,
    subscription_id: str,
    new_price_id: str,
) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    sub = await db.subscriptions.find_one({"id": subscription_id})
    if not sub or sub.get("user_id") != user_id:
        raise BillingError("Subscription not found", code="subscription_not_found", status_code=404)
    new_price = await find_price(db, price_id=new_price_id, billing_type="recurring")
    if new_price.get("product_id") != sub.get("product_id"):
        raise BillingError("Plan changes must stay within the same product", code="invalid_plan_change", status_code=400)
    if not new_price.get("braintree_plan_id"):
        raise BillingError(
            "Target plan is missing braintree_plan_id",
            code="missing_braintree_plan_id",
            status_code=409,
        )
    payload = {
        "plan_id": new_price["braintree_plan_id"],
        "price": f"{_amount(new_price['amount']):.2f}",
    }
    if sub.get("braintree_payment_method_token"):
        payload["payment_method_token"] = sub["braintree_payment_method_token"]
    merchant_account_id = default_merchant_account_id()
    if merchant_account_id:
        payload["merchant_account_id"] = merchant_account_id
    try:
        result = gateway.subscription.update(sub["braintree_subscription_id"], payload)
    except Exception as exc:
        raise BillingError(
            f"Braintree plan change failed: {exc}",
            code="braintree_plan_change_failed",
            status_code=502,
        ) from exc
    if not getattr(result, "is_success", False):
        raise BillingError(
            f"Braintree plan change rejected: {getattr(result, 'message', '') or getattr(result, 'errors', '')}",
            code="braintree_plan_change_failed",
            status_code=402,
        )
    update = {
        "price_id": new_price["id"],
        "plan_id": new_price["id"],
        "status": _status(_first_attr(getattr(result, "subscription", None), "status")) or sub.get("status"),
        "current_period_end": _date_or_none(
            _first_attr(getattr(result, "subscription", None), "billing_period_end_date", "paid_through_date")
        )
        or sub.get("current_period_end"),
    }
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": update})
    return {"subscription": {**sub, **update}, "price": new_price}


async def cancel_subscription(
    db: Any,
    gateway: Any,
    user: Any,
    *,
    subscription_id: str,
    cancel_at_period_end: bool,
) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    sub = await db.subscriptions.find_one({"id": subscription_id})
    if not sub or sub.get("user_id") != user_id:
        raise BillingError("Subscription not found", code="subscription_not_found", status_code=404)
    if sub.get("braintree_subscription_id"):
        try:
            gateway.subscription.cancel(sub["braintree_subscription_id"])
        except Exception as exc:
            raise BillingError(
                f"Braintree cancellation failed: {exc}",
                code="braintree_cancellation_failed",
                status_code=502,
            ) from exc
    update = {
        "status": "canceled",
        "cancel_at_period_end": bool(cancel_at_period_end),
        "canceled_at": now_iso(),
    }
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": update})
    if not cancel_at_period_end:
        await db.entitlements.update_many(
            {"user_id": user_id, "product_id": sub.get("product_id")},
            {"$set": {"active": False}},
        )
    return {"subscription": {**sub, **update}}


async def resume_subscription(db: Any, user: Any, *, subscription_id: str) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    sub = await db.subscriptions.find_one({"id": subscription_id})
    if not sub or sub.get("user_id") != user_id:
        raise BillingError("Subscription not found", code="subscription_not_found", status_code=404)
    if str(sub.get("status", "")).lower() == "canceled":
        raise BillingError(
            "This Braintree subscription is already canceled. Create a new subscription to resume access.",
            code="subscription_already_canceled",
            status_code=409,
        )
    update = {"cancel_at_period_end": False, "canceled_at": None}
    await db.subscriptions.update_one({"id": sub["id"]}, {"$set": update})
    return {"subscription": {**sub, **update}}


async def billing_history(db: Any, user: Any) -> Dict[str, Any]:
    user_id = coerce_user_id(user)
    orders = await db.orders.find({"user_id": user_id}).sort("created_at", -1).to_list(200)
    return {"history": orders, "count": len(orders)}


def webhook_event_id(kind: str, signature: str, payload: str, related_id: str = "") -> str:
    digest = hashlib.sha256(f"{kind}:{signature}:{payload}:{related_id}".encode("utf-8")).hexdigest()
    return f"btwh_{digest[:32]}"


async def process_webhook(db: Any, notification: Any, *, signature: str, payload: str) -> Dict[str, Any]:
    kind = str(_first_attr(notification, "kind") or "")
    sub_obj = _first_attr(notification, "subscription")
    tx_obj = _first_attr(notification, "transaction")
    related_id = _first_attr(sub_obj, "id") or _first_attr(tx_obj, "id") or ""
    event_id = webhook_event_id(kind, signature, payload, str(related_id))
    existing = await db.billing_events.find_one({"id": event_id})
    if existing and existing.get("processed_at"):
        return {"status": "duplicate", "event": existing}
    doc = {
        "id": event_id,
        "event_provider": "braintree",
        "event_type": kind,
        "braintree_webhook_id": event_id,
        "signature": signature[:96],
        "payload": {"kind": kind, "related_id": related_id},
        "processed_at": None,
        "created_at": now_iso(),
    }
    if existing:
        await db.billing_events.update_one({"id": event_id}, {"$set": doc})
    else:
        await db.billing_events.insert_one(doc)

    if sub_obj is not None:
        await _apply_subscription_webhook(db, kind, sub_obj)
    if tx_obj is not None:
        await _apply_transaction_webhook(db, kind, tx_obj)

    doc["processed_at"] = now_iso()
    await db.billing_events.update_one({"id": event_id}, {"$set": doc})
    return {"status": "processed", "event": doc}


async def _apply_subscription_webhook(db: Any, kind: str, sub_obj: Any) -> None:
    sub_id = _first_attr(sub_obj, "id")
    if not sub_id:
        return
    local = await db.subscriptions.find_one({"braintree_subscription_id": sub_id})
    if not local:
        return
    status_map = {
        "subscription_charged_successfully": "active",
        "subscription_charged_unsuccessfully": "past_due",
        "subscription_went_past_due": "past_due",
        "subscription_canceled": "canceled",
        "subscription_expired": "expired",
        "subscription_trial_ended": "active",
    }
    update = {
        "status": status_map.get(kind, _status(_first_attr(sub_obj, "status")) or local.get("status")),
        "current_period_end": _date_or_none(
            _first_attr(sub_obj, "billing_period_end_date", "paid_through_date")
        )
        or local.get("current_period_end"),
    }
    if update["status"] in {"canceled", "expired"}:
        update["canceled_at"] = now_iso()
    await db.subscriptions.update_one({"id": local["id"]}, {"$set": update})
    if kind == "subscription_charged_successfully":
        transactions = getattr(sub_obj, "transactions", None) or []
        if transactions:
            tx = transactions[0]
            tx_id = _first_attr(tx, "id")
            if tx_id and not await db.orders.find_one({"braintree_transaction_id": tx_id}):
                order = order_doc_from_transaction(
                    tx,
                    user_id=local["user_id"],
                    product_id=local["product_id"],
                    price_id=local.get("price_id"),
                    payment_type="subscription_renewal",
                    subscription_id=sub_id,
                )
                await db.orders.insert_one(order)


async def _apply_transaction_webhook(db: Any, kind: str, tx_obj: Any) -> None:
    tx_id = _first_attr(tx_obj, "id")
    if not tx_id:
        return
    status_map = {
        "transaction_settled": "success",
        "transaction_settlement_declined": "failed",
        "transaction_failed": "failed",
        "transaction_processor_declined": "failed",
    }
    existing = await db.orders.find_one({"braintree_transaction_id": tx_id})
    if existing:
        await db.orders.update_one(
            {"id": existing["id"]},
            {"$set": {"status": status_map.get(kind, existing.get("status")), "updated_at": now_iso()}},
        )
