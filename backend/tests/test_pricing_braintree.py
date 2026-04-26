from __future__ import annotations

import asyncio

from backend import pricing_plans
from backend.routes.braintree_payments import braintree_status


def test_public_pricing_is_locked_to_approved_credit_plans():
    assert pricing_plans.CREDIT_PLANS["free"]["credits"] == 200
    assert pricing_plans.CREDIT_PLANS["free"]["price"] == 0

    expected = {
        "builder": (500, 15),
        "pro": (1000, 30),
        "scale": (2000, 60),
        "teams": (5000, 150),
    }
    for plan, (credits, price) in expected.items():
        assert pricing_plans.CREDIT_PLANS[plan]["credits"] == credits
        assert pricing_plans.CREDIT_PLANS[plan]["price"] == price
        assert pricing_plans.TOKEN_BUNDLES[plan]["credits"] == credits
        assert pricing_plans.TOKEN_BUNDLES[plan]["price"] == price


def test_payment_provider_status_is_braintree(monkeypatch):
    monkeypatch.delenv("BRAINTREE_MERCHANT_ID", raising=False)
    monkeypatch.delenv("BRAINTREE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("BRAINTREE_PRIVATE_KEY", raising=False)

    status = asyncio.run(braintree_status())

    assert status["provider"] == "braintree"
    assert status["configured"] is False
    assert "BRAINTREE_MERCHANT_ID" in status["required_config"]
