"""
Admin API tests: 401 without auth, 403 for regular users, 200 with expected schema for admins.
"""

import pytest
from conftest import register_and_get_headers


async def register_admin_and_get_headers(app_client):
    """Register a user, grant admin_role in DB, return auth headers."""
    import uuid

    from backend import server as _srv

    db = _srv.db
    assert db is not None

    email = f"admin-{uuid.uuid4().hex[:12]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "AdminPass123!", "name": "Admin User"},
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    user_id = data.get("user", {}).get("id")
    assert user_id
    await db.users.update_one({"id": user_id}, {"$set": {"admin_role": "owner"}})
    return {"Authorization": f"Bearer {data['token']}"}


ADMIN_GET_PATHS = [
    "/api/admin/dashboard",
    "/api/admin/analytics/overview",
    "/api/admin/users",
    "/api/admin/billing/transactions",
    "/api/admin/fraud/flags",
    "/api/admin/legal/blocked-requests",
    "/api/admin/referrals/links",
    "/api/admin/referrals/leaderboard",
    "/api/admin/segments",
]


@pytest.mark.asyncio
async def test_admin_endpoints_401_without_token(app_client):
    """Admin endpoints return 401 when no Authorization header."""
    for path in ADMIN_GET_PATHS:
        r = await app_client.get(path, timeout=5)
        assert (
            r.status_code == 401
        ), f"GET {path} should require auth, got {r.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_403_for_regular_user(app_client):
    """Admin endpoints return 403 for authenticated non-admin users."""
    auth_headers = await register_and_get_headers(app_client)
    for path in ADMIN_GET_PATHS:
        r = await app_client.get(path, headers=auth_headers, timeout=10)
        assert (
            r.status_code == 403
        ), f"GET {path} should reject non-admin, got {r.status_code}"


@pytest.mark.asyncio
async def test_admin_dashboard_200_with_admin(app_client):
    """Admin dashboard returns 200 and expected schema when called by admin."""
    headers = await register_admin_and_get_headers(app_client)
    r = await app_client.get("/api/admin/dashboard", headers=headers, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text[:300]}"
    data = r.json()
    for key in (
        "total_users",
        "signups_today",
        "signups_week",
        "revenue_today",
        "revenue_week",
        "revenue_month",
    ):
        assert key in data, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_users_list_200_with_admin(app_client):
    """Admin users list returns 200 and users array when called by admin."""
    headers = await register_admin_and_get_headers(app_client)
    r = await app_client.get("/api/admin/users", headers=headers, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text[:300]}"
    data = r.json()
    assert "users" in data
    assert isinstance(data["users"], list)


@pytest.mark.asyncio
async def test_admin_analytics_overview_200_with_admin(app_client):
    """Admin analytics overview returns 200 and expected keys when called by admin."""
    headers = await register_admin_and_get_headers(app_client)
    r = await app_client.get(
        "/api/admin/analytics/overview", headers=headers, timeout=10
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text[:300]}"
    data = r.json()
    for key in ("total_users", "signups_today", "signups_week"):
        assert key in data, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_user_profile_404_for_nonexistent(app_client):
    """Admin user profile returns 404 for non-existent user_id."""
    headers = await register_admin_and_get_headers(app_client)
    r = await app_client.get(
        "/api/admin/users/nonexistent-user-id-12345",
        headers=headers,
        timeout=10,
    )
    assert (
        r.status_code == 404
    ), f"Expected 404 for nonexistent user, got {r.status_code}"


@pytest.mark.asyncio
async def test_admin_user_profile_200_for_existing(app_client):
    """Admin user profile returns 200 for existing user."""
    headers = await register_admin_and_get_headers(app_client)
    # Create another user to fetch
    auth = await register_and_get_headers(app_client)
    me = await app_client.get("/api/auth/me", headers=auth, timeout=5)
    assert me.status_code == 200
    target_id = me.json().get("id")
    assert target_id
    r = await app_client.get(
        f"/api/admin/users/{target_id}", headers=headers, timeout=10
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("id") == target_id
    assert "password" not in data
