from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.cost_hook import router
from backend.services.cost_governance import cost_governance_payload, estimate_cost


def test_cost_governance_uses_approved_public_pricing():
    payload = cost_governance_payload()
    plans = {plan["key"]: plan for plan in payload["pricing"]["plans"]}

    assert plans["free"]["price_usd"] == 0
    assert plans["builder"]["price_usd"] == 20
    assert plans["pro"]["price_usd"] == 50
    assert plans["scale"]["price_usd"] == 100
    assert plans["teams"]["price_usd"] == 200
    assert payload["pricing"]["approved_price_floor"] == "$20 Builder plan"
    assert payload["pricing"]["legacy_prices_allowed"] is False


def test_simulation_depths_cap_agents_rounds_and_modeled_perspectives():
    payload = cost_governance_payload()
    depths = payload["simulation_depths"]

    assert depths["fast"]["credit_cap"] < depths["balanced"]["credit_cap"]
    assert depths["balanced"]["credit_cap"] < depths["deep"]["credit_cap"]
    assert depths["maximum"]["modeled_perspectives"] == "7500-10000"
    assert "evidence" in depths["deep"]["evidence_policy"]


def test_cost_estimate_flags_approval_when_action_cap_is_exceeded():
    estimate = estimate_cost(
        action="simulation",
        plan="builder",
        depth="fast",
        input_tokens=9000,
        output_tokens=1000,
    )

    assert estimate["estimated_credits"] == 20
    assert estimate["policy_credit_cap"] == 8
    assert estimate["within_action_cap"] is False
    assert estimate["requires_approval"] is True


def test_cost_governance_routes_return_json():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    governance = client.get("/api/cost/governance")
    assert governance.status_code == 200
    assert governance.json()["pricing"]["bulk_credit_rate_usd"] == 0.05

    estimate = client.post(
        "/api/cost/estimate",
        json={
            "action": "build",
            "plan": "pro",
            "input_tokens": 1000,
            "output_tokens": 1000,
        },
    )
    assert estimate.status_code == 200
    assert estimate.json()["estimated_credits"] == 4
