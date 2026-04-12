"""
Fortune 100 Layer 2: Admin end-to-end workflows.
"""

import pytest
from conftest import register_and_get_headers
from test_admin import register_admin_and_get_headers


@pytest.mark.asyncio
async def test_admin_suspends_user(app_client):
    """Admin suspends user -> user marked suspended in DB."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/suspend",
        json={"reason": "ToS violation"},
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    target = await db.users.find_one({"id": target_id})
    assert target.get("suspended") is True


@pytest.mark.asyncio
async def test_admin_grants_credits(app_client):
    """Admin grants credits -> user credit_balance increases."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    target_before = await db.users.find_one({"id": target_id})
    initial = target_before.get("credit_balance") or 0
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 50, "reason": "Test grant"},
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    target_after = await db.users.find_one({"id": target_id})
    assert (target_after.get("credit_balance") or 0) >= initial + 50


@pytest.mark.asyncio
async def test_admin_exports_user_data(app_client):
    """Admin exports user -> gets user, ledger, project_ids."""
    admin_headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.get(
        f"/api/admin/users/{target_id}/export",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "user" in data
    assert "ledger_entries" in data
    assert "project_ids" in data


@pytest.mark.asyncio
async def test_admin_views_blocked_requests(app_client):
    """Admin can view blocked legal requests."""
    admin_headers = await register_admin_and_get_headers(app_client)
    r = await app_client.get(
        "/api/admin/legal/blocked-requests",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "blocked_requests" in data


@pytest.mark.asyncio
async def test_admin_downgrades_user(app_client):
    """Admin downgrades user plan -> plan becomes free."""
    from server import db

    admin_headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    await db.users.update_one({"id": target_id}, {"$set": {"plan": "pro"}})
    r = await app_client.post(
        f"/api/admin/users/{target_id}/downgrade",
        headers=admin_headers,
        timeout=10,
    )
    assert r.status_code == 200
    target = await db.users.find_one({"id": target_id})
    assert target.get("plan") == "free"


@pytest.mark.asyncio
async def test_admin_cannot_suspend_another_admin(app_client):
    """Admin cannot suspend another admin."""
    from test_admin_security import register_user_with_role

    admin1_headers, admin1_id, _ = await register_user_with_role(app_client, "owner")
    admin2_headers, admin2_id, _ = await register_user_with_role(
        app_client, "operations"
    )
    r = await app_client.post(
        f"/api/admin/users/{admin2_id}/suspend",
        json={"reason": "Test"},
        headers=admin1_headers,
        timeout=10,
    )
    assert r.status_code == 403
