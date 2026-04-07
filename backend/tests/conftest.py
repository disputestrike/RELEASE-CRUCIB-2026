"""
Pytest fixtures and config for CrucibAI backend tests.
PostgreSQL: defaults match repo docker-compose (host 5434). Session start brings up deps when possible.
"""
import asyncio
import os
import sys

# asyncpg + Windows ProactorEventLoop causes "another operation is in progress" / wrong-loop errors.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import socket
import subprocess
import time
from pathlib import Path

import pytest

try:
    import pytest_asyncio
except ImportError as exc:  # pragma: no cover - env setup
    raise ImportError(
        "Missing pytest_asyncio. Install test deps: pip install -r backend/requirements.txt "
        "(includes pytest-asyncio)."
    ) from exc

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_test_env():
    """Defaults so in-process FastAPI tests match docker-compose.local.yml and pass env_setup."""
    if os.environ.get("TEST_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    if not os.environ.get("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
    if not os.environ.get("REDIS_URL", "").strip():
        os.environ["REDIS_URL"] = "redis://127.0.0.1:6381/0"
    if not os.environ.get("JWT_SECRET", "").strip():
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-pytest-minimum-32-characters-long"
    if not os.environ.get("GOOGLE_CLIENT_ID", "").strip():
        os.environ["GOOGLE_CLIENT_ID"] = "test.apps.googleusercontent.com"
    if not os.environ.get("GOOGLE_CLIENT_SECRET", "").strip():
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
    if not os.environ.get("FRONTEND_URL", "").strip():
        os.environ["FRONTEND_URL"] = "http://localhost:3000"


_ensure_test_env()
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "99999")
os.environ["DISABLE_CSRF_FOR_TEST"] = "1"
os.environ.setdefault("CRUCIBAI_TEST", "1")

pytest_plugins = ("pytest_asyncio",)


def pytest_sessionstart(session):
    """Bring up local docker deps when not in GitHub Actions; CI uses service containers + DATABASE_URL."""
    skip_compose = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    compose = _REPO_ROOT / "docker-compose.yml"
    if not skip_compose and compose.is_file():
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose), "up", "-d", "postgres", "redis"],
                cwd=str(_REPO_ROOT),
                timeout=120,
                capture_output=True,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return
        deadline = time.time() + 90
        ok = False
        while time.time() < deadline:
            try:
                s = socket.create_connection(("127.0.0.1", 5434), timeout=2)
                s.close()
                ok = True
                break
            except OSError:
                time.sleep(1)
        if not ok:
            pytest.exit(
                "PostgreSQL not reachable on 127.0.0.1:5434 after 90s. "
                "From repo root run: docker compose up -d postgres redis",
                returncode=1,
            )

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    async def _migrate_once():
        from db_pg import close_pg_pool, ensure_all_tables, get_pg_pool, run_migrations

        await run_migrations()
        if os.environ.get("CRUCIBAI_TEST"):
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS audit_log CASCADE")
            await close_pg_pool()
        await ensure_all_tables()
        await close_pg_pool()

    asyncio.run(_migrate_once())


BASE_URL = os.environ.get("CRUCIBAI_API_URL", os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000"))


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_url(base_url):
    return f"{base_url}/api"


@pytest_asyncio.fixture
async def app_client():
    """Per-test AsyncClient + asyncpg pool on the same event loop (required on Windows + httpx)."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from httpx import ASGITransport, AsyncClient

    import server as server_module
    from db_pg import close_pg_pool, get_db
    from server import app

    await close_pg_pool()
    server_module.db = None
    try:
        server_module.db = await get_db()
        try:
            from utils.audit_log import AuditLogger as DbAuditLogger

            server_module.audit_logger = DbAuditLogger(server_module.db)
        except Exception:
            server_module.audit_logger = None
    except Exception as e:
        pytest.fail(
            f"PostgreSQL required for tests ({e}). "
            f"Start deps: docker compose up -d postgres redis (repo root). DATABASE_URL={os.environ.get('DATABASE_URL')!r}"
        )

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        timeout=120.0,
    ) as client:
        yield client

    await close_pg_pool()
    server_module.db = None
    server_module.audit_logger = None


TEST_USER_CREDITS = 10000


async def register_and_get_headers(app_client):
    """Register a unique user and return headers with Bearer token."""
    import uuid

    email = f"test-{uuid.uuid4().hex[:12]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Test User"},
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    user_id = data.get("user", {}).get("id")
    if user_id:
        from server import db

        await db.users.update_one(
            {"id": user_id},
            {"$set": {"credit_balance": TEST_USER_CREDITS, "plan": "pro"}},
        )
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture
async def auth_headers(app_client):
    return await register_and_get_headers(app_client)


@pytest.fixture
async def auth_headers_with_project(app_client, auth_headers):
    r = await app_client.post(
        "/api/projects",
        json={
            "name": "e2e-test-project",
            "description": "E2E",
            "project_type": "web",
            "requirements": {"prompt": "todo app"},
        },
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code in (200, 201), f"Project create failed: {r.status_code} {r.text}"
    data = r.json()
    project = data.get("project") or data
    project_id = project.get("id")
    assert project_id, f"No project id in response: {data}"
    return {**auth_headers, "x-test-project-id": project_id}


@pytest.fixture
def mock_llm_response():
    return {
        "content": "Generated code output from LLM",
        "model": "test-model",
        "tokens_used": 150,
        "finish_reason": "stop",
    }


@pytest.fixture
def mock_llm_caller(mock_llm_response):
    from unittest.mock import AsyncMock

    async def _caller(message, system_message, session_id, model_chain, api_keys):
        return mock_llm_response["content"], mock_llm_response["tokens_used"]

    return _caller


@pytest.fixture
def test_user():
    return {
        "id": "test-user-id-12345",
        "email": "testuser@crucibai.com",
        "name": "Test User",
        "plan": "pro",
        "tokens_remaining": 10000,
        "role": "user",
    }


@pytest.fixture
def sample_agent_config():
    return {
        "name": "test_agent",
        "role": "code_generator",
        "system_message": "You are a test agent that generates Python code.",
        "model_preference": ["cerebras", "haiku"],
        "timeout": 30,
        "max_retries": 2,
    }


@pytest.fixture
def mock_metrics():
    from unittest.mock import MagicMock

    metrics = MagicMock()
    metrics.builds_total = MagicMock()
    metrics.build_queue_depth = MagicMock()
    metrics.agent_executions_total = MagicMock()
    metrics.active_agents = MagicMock()
    metrics.errors_total = MagicMock()
    return metrics
