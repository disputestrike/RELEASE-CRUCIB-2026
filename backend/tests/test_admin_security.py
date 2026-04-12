"""
Fortune 100 Layer 1B: Admin security and access control.
"""

import pytest
import uuid
from conftest import register_and_get_headers
from test_admin import register_admin_and_get_headers


async def register_user_with_role(app_client, role: str = "owner"):
    """Register user, set admin_role, return (headers, user_id, email)."""
    from server import db

    email = f"admin-{role}-{uuid.uuid4().hex[:10]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"Admin {role}"},
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    user_id = data.get("user", {}).get("id")
    assert user_id
    await db.users.update_one({"id": user_id}, {"$set": {"admin_role": role}})
    return {"Authorization": f"Bearer {data['token']}"}, user_id, email


@pytest.mark.asyncio
async def test_regular_user_403_on_dashboard(app_client):
    """Regular user gets 403 on /api/admin/dashboard."""
    headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/admin/dashboard", headers=headers, timeout=5)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_regular_user_403_on_users(app_client):
    """Regular user gets 403 on /api/admin/users."""
    headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/admin/users", headers=headers, timeout=5)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_no_token_401_on_admin_routes(app_client):
    """No token returns 401."""
    r = await app_client.get("/api/admin/dashboard", timeout=5)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected_on_admin_routes(app_client):
    """Invalid token is rejected (401 or 500 from JWT decode)."""
    r = await app_client.get(
        "/api/admin/dashboard",
        headers={"Authorization": "Bearer invalid-token"},
        timeout=5,
    )
    assert r.status_code in (401, 500)


@pytest.mark.asyncio
async def test_owner_can_access_all_admin(app_client):
    """Owner role can access all admin endpoints."""
    headers = await register_admin_and_get_headers(app_client)
    endpoints = [
        "/api/admin/dashboard",
        "/api/admin/users",
        "/api/admin/billing/transactions",
        "/api/admin/analytics/overview",
        "/api/admin/legal/blocked-requests",
    ]
    for path in endpoints:
        r = await app_client.get(path, headers=headers, timeout=10)
        assert r.status_code == 200, f"Owner should access {path}, got {r.status_code}"


@pytest.mark.asyncio
async def test_operations_can_manage_users(app_client):
    """Operations role can view users and grant credits."""
    headers, admin_id, _ = await register_user_with_role(app_client, "operations")
    r = await app_client.get("/api/admin/users", headers=headers, timeout=10)
    assert r.status_code == 200
    # Get a target user
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 10, "reason": "Test"},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_support_can_grant_credits_within_cap(app_client):
    """Support role can grant credits within SUPPORT_GRANT_CAP_PER_MONTH."""
    headers, _, _ = await register_user_with_role(app_client, "support")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    # Support cap is 50 per action
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 25, "reason": "Support bonus"},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_support_exceeds_cap_403(app_client):
    """Support role cannot grant more than cap in one action."""
    headers, _, _ = await register_user_with_role(app_client, "support")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 100, "reason": "Over cap"},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analyst_can_view_analytics(app_client):
    """Analyst role can view analytics."""
    headers, _, _ = await register_user_with_role(app_client, "analyst")
    r = await app_client.get(
        "/api/admin/analytics/overview", headers=headers, timeout=10
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_analyst_can_view_users(app_client):
    """Analyst role can view users list (read-only)."""
    headers, _, _ = await register_user_with_role(app_client, "analyst")
    r = await app_client.get("/api/admin/users", headers=headers, timeout=10)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_analyst_cannot_grant_credits(app_client):
    """Analyst role cannot grant credits (needs owner/operations/support)."""
    headers, _, _ = await register_user_with_role(app_client, "analyst")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 10},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_suspend(app_client):
    """Analyst cannot suspend users."""
    headers, _, _ = await register_user_with_role(app_client, "analyst")
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/suspend",
        json={"reason": "Test"},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_grant_credits_validates_amount(app_client):
    """Grant credits rejects negative or zero."""
    headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": -100},
        headers=headers,
        timeout=10,
    )
    assert r.status_code in (400, 422)
    r2 = await app_client.post(
        f"/api/admin/users/{target_id}/grant-credits",
        json={"credits": 0},
        headers=headers,
        timeout=10,
    )
    assert r2.status_code in (400, 422)


@pytest.mark.asyncio
async def test_suspend_validates_reason(app_client):
    """Suspend user requires reason."""
    headers = await register_admin_and_get_headers(app_client)
    reg = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=reg, timeout=5)
    target_id = me.json().get("id")
    r = await app_client.post(
        f"/api/admin/users/{target_id}/suspend",
        json={},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 422
