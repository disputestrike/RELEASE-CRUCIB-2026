"""
Pricing alignment tests: single source of truth for free, builder, pro, scale, teams.
No starter. No light/dev add-ons. Speed tier access and credit logic aligned.
"""
import pytest


# --- 1. pricing_plans (no server import) ---
@pytest.mark.parametrize("plan,expected_credits,expected_price", [
    ("free", 200, 0),
    ("builder", 500, 15),
    ("pro", 1000, 30),
    ("scale", 2000, 60),
    ("teams", 5000, 150),
])
def test_credit_plans_has_correct_plans_and_values(plan, expected_credits, expected_price):
    from pricing_plans import CREDIT_PLANS
    assert plan in CREDIT_PLANS
    assert CREDIT_PLANS[plan]["credits"] == expected_credits
    assert CREDIT_PLANS[plan]["price"] == expected_price


def test_credit_plans_does_not_contain_starter():
    from pricing_plans import CREDIT_PLANS
    assert "starter" not in CREDIT_PLANS


def test_credit_plans_only_has_free_builder_pro_scale_teams():
    from pricing_plans import CREDIT_PLANS
    assert set(CREDIT_PLANS.keys()) == {"free", "builder", "pro", "scale", "teams"}


def test_token_bundles_exactly_builder_pro_scale_teams():
    from pricing_plans import TOKEN_BUNDLES
    assert set(TOKEN_BUNDLES.keys()) == {"builder", "pro", "scale", "teams"}
    for k in TOKEN_BUNDLES:
        b = TOKEN_BUNDLES[k]
        assert "credits" in b and "price" in b and "name" in b


def test_speed_from_plan():
    from pricing_plans import _speed_from_plan
    assert _speed_from_plan("free") == "lite"
    assert _speed_from_plan("builder") == "pro"
    assert _speed_from_plan("pro") == "max"
    assert _speed_from_plan("scale") == "max"
    assert _speed_from_plan("teams") == "max"
    assert _speed_from_plan("starter") == "pro"  # legacy only


def test_addons_empty_no_light_dev():
    from pricing_plans import ADDONS
    assert ADDONS == {}
    assert "light" not in ADDONS and "dev" not in ADDONS


# --- 2. speed_tier_router ---
def test_plan_speed_access_has_scale_no_starter():
    from speed_tier_router import SpeedTierRouter
    access = SpeedTierRouter.PLAN_SPEED_ACCESS
    assert "starter" not in access
    assert "scale" in access
    assert access["scale"] == ["lite", "pro", "max"]


def test_plan_speed_access_keys():
    from speed_tier_router import SpeedTierRouter
    assert set(SpeedTierRouter.PLAN_SPEED_ACCESS.keys()) == {"free", "builder", "pro", "scale", "teams"}


def test_validate_speed_tier_builder_has_pro():
    from speed_tier_router import SpeedTierRouter
    valid, _ = SpeedTierRouter.validate_speed_tier_access("builder", "pro")
    assert valid is True


def test_validate_speed_tier_scale_has_max():
    from speed_tier_router import SpeedTierRouter
    valid, _ = SpeedTierRouter.validate_speed_tier_access("scale", "max")
    assert valid is True


def test_validate_speed_tier_free_no_pro():
    from speed_tier_router import SpeedTierRouter
    valid, msg = SpeedTierRouter.validate_speed_tier_access("free", "pro")
    assert valid is False
    assert "Builder" in msg or "paid" in msg.lower()


# --- 3. credit_tracker (no starter branch) ---
def test_credit_tracker_free_does_not_pay_for_cerebras():
    from credit_tracker import CreditTracker
    cost = CreditTracker.calculate_credit_cost("cerebras", 10_000, "free")
    assert cost == 0.0


def test_credit_tracker_builder_pays_for_haiku():
    from credit_tracker import CreditTracker
    cost = CreditTracker.calculate_credit_cost("haiku", 10_000, "builder")
    assert cost >= 0


def test_credit_tracker_scale_tier_supported():
    from credit_tracker import CreditTracker
    cost = CreditTracker.calculate_credit_cost("haiku", 1000, "scale")
    assert cost >= 0


# --- 4. validators bundle pattern ---
def test_token_purchase_validator_accepts_builder_pro_scale_teams():
    from validators import TokenPurchaseValidator
    for bundle in ["builder", "pro", "scale", "teams", "custom"]:
        v = TokenPurchaseValidator(bundle=bundle)
        assert v.bundle == bundle


def test_token_purchase_validator_rejects_starter():
    from validators import TokenPurchaseValidator
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TokenPurchaseValidator(bundle="starter")


# --- 5. API bundles endpoint (if app available) ---
@pytest.mark.asyncio
async def test_api_bundles_returns_builder_pro_scale_teams(app_client):
    r = await app_client.get("/api/tokens/bundles", timeout=5)
    assert r.status_code == 200
    data = r.json()
    bundles = data["bundles"]
    for key in ["builder", "pro", "scale", "teams"]:
        assert key in bundles, f"bundles must include {key}"
        assert "credits" in bundles[key] and "price" in bundles[key] and "name" in bundles[key]
    assert "starter" not in bundles
    assert "light" not in bundles and "dev" not in bundles
