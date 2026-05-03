from __future__ import annotations

import asyncio

from backend import pricing_plans
from backend.routes.paypal_payments import billing_config


def test_public_pricing_is_locked_to_approved_credit_plans():
    assert pricing_plans.CREDIT_PLANS["free"]["credits"] == 100
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


def test_payment_provider_status_is_paypal(monkeypatch):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)

    status = asyncio.run(billing_config())

    assert status["provider"] == "paypal"
    assert status["configured"] is False
    assert "PAYPAL_CLIENT_ID" in status["required_config"]
