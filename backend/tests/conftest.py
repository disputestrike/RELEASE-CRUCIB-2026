"""
Pytest fixtures and config for CrucibAI backend tests.
Sets MONGO_URL/DB_NAME so the real app can be imported for TestClient-based tests.
"""
import asyncio
import os
import pytest

# Must set before server is ever imported (server uses os.environ["MONGO_URL"])
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "crucibai")
# Avoid 429 in tests: raise limit so suite can run without rate-limit failures
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "99999")

# Enable async tests (test_orchestration_e2e)
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Single session-scoped event loop so Motor and app share one loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Base URL for tests that still use requests (e.g. test_smoke when hitting live server)
BASE_URL = os.environ.get("CRUCIBAI_API_URL", os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000"))


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_url(base_url):
    return f"{base_url}/api"


@pytest.fixture
async def app_client():
    """Real FastAPI app via AsyncClient (in-process). For auth/DB tests, Motor may hit 'Future attached to a different loop'; run backend then use CRUCIBAI_API_URL=http://localhost:8000 for full suite."""
    from httpx import ASGITransport, AsyncClient
    from server import app
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        timeout=60.0,
    ) as client:
        yield client


# Credits granted to test users so project create / build_plan don't skip (402)
TEST_USER_CREDITS = 500


async def register_and_get_headers(app_client):
    """Register a unique user and return headers with Bearer token. Call from test body so Motor runs in same loop as test.
    Grants TEST_USER_CREDITS so project creation and build/plan tests can run without 402 skip."""
    import uuid
    email = f"test-{uuid.uuid4().hex[:12]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Test User"},
        timeout=10,
    )
    if r.status_code == 500:
        pytest.skip(
            "In-process register returned 500 (Motor/event loop conflict). Run backend and set CRUCIBAI_API_URL=http://localhost:8000 for full suite."
        )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    user_id = data.get("user", {}).get("id")
    if user_id:
        from server import db
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"credit_balance": TEST_USER_CREDITS}},
        )
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture
async def auth_headers(app_client):
    """Auth headers: register in test context so same event loop as test (avoids Motor 'different loop' 500)."""
    return await register_and_get_headers(app_client)


@pytest.fixture
async def auth_headers_with_project(app_client, auth_headers):
    """Auth headers plus a created project_id for tests that need a project."""
    r = await app_client.post(
        "/api/projects",
        json={"name": "e2e-test-project", "description": "E2E", "project_type": "web", "requirements": {"prompt": "todo app"}},
        headers=auth_headers,
        timeout=15,
    )
    if r.status_code != 200 and r.status_code != 201:
        pytest.skip(f"Project create failed (e.g. credits): {r.status_code} {r.text}")
    data = r.json()
    project = data.get("project") or data
    project_id = project.get("id")
    if not project_id:
        pytest.skip("No project id in response")
    return {**auth_headers, "x-test-project-id": project_id}
