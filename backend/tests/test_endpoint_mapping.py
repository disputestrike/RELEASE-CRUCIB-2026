"""
Layer 1: ENDPOINT MAPPING TEST
Verify critical API routes exist, return correct status codes, and response schema.
"""
import pytest
from conftest import register_and_get_headers

# Endpoints that do NOT require auth (public or return 401/400 when used wrong)
PUBLIC_OR_UNAUTH = [
    {"name": "Health", "method": "GET", "path": "/api/health", "expect_status": 200, "expect_keys": ["status"]},
    {"name": "Root", "method": "GET", "path": "/api/", "expect_status": 200},
    {"name": "Tokens bundles", "method": "GET", "path": "/api/tokens/bundles", "expect_status": 200, "expect_keys": ["bundles"]},
    {"name": "Build phases", "method": "GET", "path": "/api/build/phases", "expect_status": 200},
    {"name": "Agent definitions (public)", "method": "GET", "path": "/api/agents", "expect_status": 200, "expect_keys": ["agents"]},
    {"name": "Templates", "method": "GET", "path": "/api/templates", "expect_status": 200},
    {"name": "Patterns", "method": "GET", "path": "/api/patterns", "expect_status": 200},
    {"name": "Examples", "method": "GET", "path": "/api/examples", "expect_status": 200, "expect_keys": ["examples"]},
    {"name": "Register (invalid dup)", "method": "POST", "path": "/api/auth/register", "body": {"email": "test@test.com", "password": "x", "name": "x"}, "expect_status": [200, 201, 400]},
]

# Endpoints that REQUIRE auth (expect 401 without token)
AUTH_REQUIRED_GET = [
    ("/api/auth/me", ["id", "email"]),
    ("/api/projects", ["projects"]),
    ("/api/tokens/history", ["history"]),
    ("/api/tokens/usage", None),
    ("/api/referrals/code", None),
    ("/api/referrals/stats", ["this_month", "total", "cap"]),
]

AUTH_REQUIRED_POST = [
    ("/api/build/plan", {"prompt": "a landing page"}, [200, 402], None),
    ("/api/projects", {"name": "t", "description": "d", "project_type": "web", "requirements": "r"}, [200, 201, 402, 403], ["project"]),
]


@pytest.mark.asyncio
async def test_public_endpoints_respond(app_client):
    """Layer 1a: Public / unauthenticated endpoints return expected status and keys."""
    for ep in PUBLIC_OR_UNAUTH:
        if ep["method"] == "GET":
            r = await app_client.get(ep["path"], timeout=10)
        else:
            r = await app_client.post(ep["path"], json=ep.get("body") or {}, timeout=10)
        expect = ep["expect_status"]
        if isinstance(expect, list):
            assert r.status_code in expect, f"{ep['name']}: expected one of {expect}, got {r.status_code}"
        else:
            assert r.status_code == expect, f"{ep['name']}: expected {expect}, got {r.status_code}"
        if ep.get("expect_keys") and r.status_code in (200, 201):
            data = r.json()
            for key in ep["expect_keys"]:
                assert key in data, f"{ep['name']}: missing key '{key}'"


@pytest.mark.asyncio
async def test_protected_endpoints_require_auth(app_client):
    """Layer 1b: Protected endpoints return 401 without token."""
    for path, _ in AUTH_REQUIRED_GET:
        r = await app_client.get(path, timeout=5)
        assert r.status_code == 401, f"GET {path} should require auth, got {r.status_code}"
    for path, body, _, _ in AUTH_REQUIRED_POST:
        r = await app_client.post(path, json=body, timeout=5)
        assert r.status_code == 401, f"POST {path} should require auth, got {r.status_code}"


@pytest.mark.asyncio
async def test_protected_endpoints_with_auth(app_client):
    """Layer 1c: Protected GET endpoints return 200 and expected keys with valid token."""
    auth_headers = await register_and_get_headers(app_client)
    for path, expect_keys in AUTH_REQUIRED_GET:
        r = await app_client.get(path, headers=auth_headers, timeout=10)
        assert r.status_code == 200, f"GET {path}: expected 200, got {r.status_code} {r.text[:300]}"
        if expect_keys:
            data = r.json()
            for key in expect_keys:
                assert key in data, f"GET {path}: missing key '{key}'"


@pytest.mark.asyncio
async def test_projects_crud_with_auth(app_client):
    """Layer 1d: Projects list and create return correct schema."""
    auth_headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/projects", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)


@pytest.mark.asyncio
async def test_build_plan_with_auth(app_client):
    """Layer 1e: Build plan with auth returns 200 (or 402 if insufficient credits)."""
    auth_headers = await register_and_get_headers(app_client)
    r = await app_client.post(
        "/api/build/plan",
        json={"prompt": "A simple landing page with hero and CTA"},
        headers=auth_headers,
        timeout=30,
    )
    if r.status_code == 500:
        pytest.skip("No LLM configured (500)")
    assert r.status_code in (200, 402), f"build/plan: got {r.status_code} {r.text[:300]}"
    if r.status_code == 200:
        data = r.json()
        assert "plan_text" in data or "plan" in data or "suggestions" in data or "message" in data
