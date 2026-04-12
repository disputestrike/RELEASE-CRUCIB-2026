"""
Layer 3: DATA INTEGRITY TEST
Concurrent requests, failure recovery, consistent state.
"""

import asyncio
import pytest
from conftest import register_and_get_headers


@pytest.mark.asyncio
async def test_concurrent_public_reads(app_client):
    """Multiple concurrent GETs to public endpoints all succeed."""

    async def get_health():
        return await app_client.get("/api/health", timeout=5)

    tasks = [get_health() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            pytest.fail(f"Request {i} raised {r}")
        assert r.status_code == 200, f"Request {i}: {r.status_code}"


@pytest.mark.asyncio
async def test_tokens_bundles_consistent_schema(app_client):
    """Bundles response has consistent structure (bundles dict, optional annual_prices)."""
    r = await app_client.get("/api/tokens/bundles", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "bundles" in data
    assert isinstance(data["bundles"], dict)
    for k, v in data["bundles"].items():
        assert "price" in v or "credits" in v or "tokens" in v


@pytest.mark.asyncio
async def test_auth_me_returns_no_password(app_client):
    """GET /auth/me never returns password or raw API keys."""
    auth_headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/auth/me", headers=auth_headers, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "password" not in data
    for key in data:
        if isinstance(data[key], str) and "sk-" in data[key]:
            pytest.fail("Sensitive key material should not be in /me response")
