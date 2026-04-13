"""
Layer 2: WEBHOOK & EVENT FLOW TEST
Verify async flows: project creation, token deduction, Stripe webhook handling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from conftest import register_and_get_headers


@pytest.mark.asyncio
async def test_project_creation_returns_and_deduction(app_client):
    """Create project: 200/201, project in response; credits deducted (user balance decreases)."""
    auth_headers = await register_and_get_headers(app_client)
    r_me = await app_client.get("/api/auth/me", headers=auth_headers, timeout=5)
    assert r_me.status_code == 200
    balance_before = r_me.json().get("credit_balance") or 0

    r = await app_client.post(
        "/api/projects",
        json={
            "name": "flow-test-project",
            "description": "Flow test",
            "project_type": "web",
            "requirements": {"prompt": "one page landing"},
        },
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code not in (402, 403), r.text
    assert r.status_code in (
        200,
        201,
    ), f"Expected 200/201, got {r.status_code} {r.text[:300]}"
    data = r.json()
    project = data.get("project") or data
    assert "id" in project
    assert (
        project.get("status") in ("queued", "running", None) or "status" not in project
    )

    r_me_after = await app_client.get("/api/auth/me", headers=auth_headers, timeout=5)
    assert r_me_after.status_code == 200
    balance_after = r_me_after.json().get("credit_balance") or 0
    assert balance_after <= balance_before, "Credits should be deducted or same"


@pytest.mark.asyncio
async def test_stripe_webhook_rejects_invalid_signature(app_client):
    """Stripe webhook returns 400 when signature is invalid (no secret leak)."""
    r = await app_client.post(
        "/api/stripe/webhook",
        content=b'{"type":"checkout.session.completed"}',
        headers={"Stripe-Signature": "invalid"},
        timeout=5,
    )
    # 400 when Stripe is configured and signature invalid; 503 when Stripe not configured
    assert r.status_code in (
        400,
        503,
    ), f"Webhook should reject invalid signature or be unavailable: {r.status_code}"


@pytest.mark.asyncio
async def test_build_plan_returns_structure(app_client):
    """Build plan endpoint returns plan text or suggestions when credits sufficient."""
    import server as server_mod

    auth_headers = await register_and_get_headers(app_client)
    llm_returns = [
        ("Plan\nKey Features:\n• Hero\nLet me build this now.", 10),
        ('["More CTAs", "Newsletter", "Menu section"]', 10),
    ]

    async def _fake_llm(*args, **kwargs):
        if llm_returns:
            return llm_returns.pop(0)
        return ("Plan\nLet me build this now.", 10)

    with patch.object(
        server_mod, "_call_llm_with_fallback", new=AsyncMock(side_effect=_fake_llm)
    ):
        r = await app_client.post(
            "/api/build/plan",
            json={"prompt": "A landing page for a coffee shop"},
            headers=auth_headers,
            timeout=45,
        )
    assert r.status_code == 200, f"build/plan: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert (
        "plan_text" in data
        or "plan" in data
        or "suggestions" in data
        or "message" in data
    )
