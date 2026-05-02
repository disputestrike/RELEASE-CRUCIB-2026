"""
PayPal Orders API v2 — CrucibAI billing service.

Env vars required:
  PAYPAL_CLIENT_ID      — from developer.paypal.com app credentials
  PAYPAL_CLIENT_SECRET  — from developer.paypal.com app credentials
  PAYPAL_ENVIRONMENT    — "sandbox" (default) or "live"
  PAYPAL_WEBHOOK_ID     — from PayPal developer dashboard webhooks

Features:
  - OAuth 2 client-credentials token (cached, auto-refreshed)
  - create_order()   -> Returns PayPal order id + approve URL for JS SDK
  - capture_order()  -> Captures an approved order, returns transaction details
  - verify_webhook() -> Validates PayPal webhook signature
  - list_plans()     -> STARTER $9/mo, PRO $29/mo, ENTERPRISE $99/mo + credit packs
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

PAYPAL_CLIENT_ID: str = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET: str = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV: str = os.environ.get("PAYPAL_ENVIRONMENT", "sandbox").lower()
PAYPAL_WEBHOOK_ID: str = os.environ.get("PAYPAL_WEBHOOK_ID", "")

BASE_URL = (
    "https://api-m.paypal.com"
    if PAYPAL_ENV == "live"
    else "https://api-m.sandbox.paypal.com"
)

PLANS: Dict[str, Dict[str, Any]] = {
    "starter":     {"label": "Starter",    "price_usd": "9.00",  "credits": 50,   "description": "50 AI builds/month"},
    "pro":         {"label": "Pro",        "price_usd": "29.00", "credits": 200,  "description": "200 AI builds/month"},
    "enterprise":  {"label": "Enterprise", "price_usd": "99.00", "credits": 1000, "description": "1000 AI builds/month"},
    "credits_10":  {"label": "10 Credits", "price_usd": "4.99",  "credits": 10,   "description": "Top-up: 10 builds"},
    "credits_50":  {"label": "50 Credits", "price_usd": "19.99", "credits": 50,   "description": "Top-up: 50 builds"},
}

_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}


class PayPalConfigError(Exception):
    pass


class PayPalError(Exception):
    def __init__(self, message: str, status_code: int = 400, raw: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw

    def detail(self) -> Dict[str, Any]:
        return {"error": str(self), "provider": "paypal"}


def paypal_configured() -> bool:
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


def _require_config() -> None:
    if not paypal_configured():
        raise PayPalConfigError("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.")


async def _get_access_token() -> str:
    _require_config()
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
    if resp.status_code != 200:
        raise PayPalError("PayPal auth failed", status_code=502, raw=resp.text)
    body = resp.json()
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = now + int(body.get("expires_in", 3600))
    return _token_cache["access_token"]


async def _headers() -> Dict[str, str]:
    token = await _get_access_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Prefer": "return=representation"}


async def create_order(plan_key: str, user_id: str, return_url: str, cancel_url: str) -> Dict[str, Any]:
    _require_config()
    plan = PLANS.get(plan_key)
    if plan is None:
        raise PayPalError(f"Unknown plan: {plan_key}", status_code=400)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": f"{plan_key}:{user_id}",
            "description": plan["description"],
            "amount": {"currency_code": "USD", "value": plan["price_usd"]},
            "custom_id": user_id,
            "soft_descriptor": "CrucibAI",
        }],
        "application_context": {
            "brand_name": "CrucibAI",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/v2/checkout/orders", json=payload, headers=await _headers(), timeout=15)
    if resp.status_code not in (200, 201):
        raise PayPalError(f"Create order failed: {resp.status_code}", status_code=502, raw=resp.text)
    body = resp.json()
    approve_url = next((lk["href"] for lk in body.get("links", []) if lk["rel"] == "approve"), None)
    return {"order_id": body["id"], "approve_url": approve_url, "status": body["status"],
            "plan": plan_key, "amount": plan["price_usd"], "credits": plan.get("credits", 0)}


async def capture_order(order_id: str) -> Dict[str, Any]:
    _require_config()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
                                 headers=await _headers(), timeout=15)
    if resp.status_code not in (200, 201):
        raise PayPalError(f"Capture failed: {resp.status_code}", status_code=502, raw=resp.text)
    body = resp.json()
    payer = body.get("payer", {})
    units = body.get("purchase_units", [{}])
    ref_id = units[0].get("reference_id", ":") if units else ":"
    plan_key = ref_id.split(":")[0] if ":" in ref_id else ref_id
    plan = PLANS.get(plan_key, {})
    capture = units[0].get("payments", {}).get("captures", [{}])[0] if units else {}
    amount_val = capture.get("amount", {}).get("value", "0.00")
    logger.info("PayPal captured: id=%s plan=%s amount=%s payer=%s", order_id, plan_key, amount_val, payer.get("email_address"))
    return {"order_id": order_id, "status": body.get("status"), "payer_email": payer.get("email_address", ""),
            "payer_id": payer.get("payer_id", ""), "amount": amount_val,
            "currency": capture.get("amount", {}).get("currency_code", "USD"),
            "plan": plan_key, "credits": plan.get("credits", 0), "capture_id": capture.get("id", "")}


async def get_order(order_id: str) -> Dict[str, Any]:
    _require_config()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/v2/checkout/orders/{order_id}", headers=await _headers(), timeout=10)
    if resp.status_code != 200:
        raise PayPalError(f"Get order failed: {resp.status_code}", status_code=502)
    return resp.json()


async def verify_webhook_signature(headers: Dict[str, str], raw_body: bytes) -> bool:
    if not PAYPAL_WEBHOOK_ID:
        logger.warning("PAYPAL_WEBHOOK_ID not set — skipping verification")
        return True
    payload = {
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "webhook_id": PAYPAL_WEBHOOK_ID,
        "webhook_event": raw_body.decode("utf-8"),
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{BASE_URL}/v1/notifications/verify-webhook-signature",
                                     json=payload, headers=await _headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json().get("verification_status") == "SUCCESS"
    except Exception as exc:
        logger.error("Webhook verification error: %s", exc)
    return False


def list_plans() -> Dict[str, Any]:
    return {k: {"key": k, **{f: v[f] for f in ("label", "price_usd", "credits", "description")}} for k, v in PLANS.items()}
