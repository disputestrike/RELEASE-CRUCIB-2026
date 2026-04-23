"""
Layer 5: SECURITY & COMPLIANCE TEST
Auth required, no token leakage, safe error responses.
"""

import pytest


@pytest.mark.asyncio
async def test_protected_endpoints_401_without_token(app_client):
    """Critical protected routes return 401 when no Authorization header."""
    protected = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/projects"),
        ("GET", "/api/tokens/history"),
        ("GET", "/api/referrals/code"),
    ]
    for method, path in protected:
        if method == "GET":
            r = await app_client.get(path, timeout=5)
        else:
            r = await app_client.post(path, json={}, timeout=5)
        assert (
            r.status_code == 401
        ), f"{method} {path} should return 401 without auth, got {r.status_code}"


@pytest.mark.asyncio
async def test_register_response_no_password(app_client):
    """Register and login responses must not contain password hash."""
    email = f"sec-{__import__('uuid').uuid4().hex[:10]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "SecretPass123!", "name": "Sec"},
        timeout=10,
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert "user" in data or "token" in data
    user = data.get("user", data)
    assert "password" not in user


@pytest.mark.asyncio
async def test_invalid_token_rejected(app_client):
    """Invalid or malformed Bearer token yields 401."""
    r = await app_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token-here"},
        timeout=5,
    )
    assert r.status_code == 401
