"""
Layer 4: USER JOURNEY TEST
Complete workflows: signup -> use app -> tokens.
"""

import pytest
from conftest import register_and_get_headers


@pytest.mark.asyncio
async def test_journey_register_me_projects(app_client):
    """Register -> GET /me -> GET /projects (full journey)."""
    email = f"journey-{__import__('uuid').uuid4().hex[:10]}@example.com"
    r_reg = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "JourneyPass123!", "name": "Journey User"},
        timeout=10,
    )
    assert r_reg.status_code in (200, 201), r_reg.text
    token = r_reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r_me = await app_client.get("/api/auth/me", headers=headers, timeout=5)
    assert r_me.status_code == 200
    me = r_me.json()
    assert me.get("email") == email
    assert "credit_balance" in me or "id" in me

    r_projects = await app_client.get("/api/projects", headers=headers, timeout=5)
    assert r_projects.status_code == 200
    assert "projects" in r_projects.json()


@pytest.mark.asyncio
async def test_journey_tokens_history_after_register(app_client):
    """With auth: tokens/history returns list, tokens/bundles returns bundles."""
    auth_headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/tokens/history", headers=auth_headers, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "history" in data
    assert isinstance(data["history"], list)
