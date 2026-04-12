"""
Pytest fixtures and config for CrucibAI backend tests.
PostgreSQL: defaults match repo docker-compose (host 5434). Session start brings up deps when possible.
"""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import uuid

# asyncpg + Windows ProactorEventLoop causes "another operation is in progress" / wrong-loop errors.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import socket
import subprocess
import time
from copy import deepcopy
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
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_TEST_TEMP_ROOT = _REPO_ROOT / ".tmp_pytest_manual"
_TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)


class _RepoTemporaryDirectory:
    """Windows/OneDrive-safe replacement for tempfile.TemporaryDirectory in tests."""

    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | None = None,
        ignore_cleanup_errors: bool = False,
    ):
        root = Path(dir or _TEST_TEMP_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        name = f"{prefix or 'tmp'}{uuid.uuid4().hex}{suffix or ''}"
        self.name = str(root / name)
        self._ignore_cleanup_errors = ignore_cleanup_errors
        os.makedirs(self.name, exist_ok=False)

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)


def _ensure_temp_paths():
    """Keep pytest/tempfile workspaces inside the repo to avoid locked system temp dirs."""
    temp_root = str(_TEST_TEMP_ROOT)
    os.environ.setdefault("TMPDIR", temp_root)
    os.environ.setdefault("TEMP", temp_root)
    os.environ.setdefault("TMP", temp_root)
    tempfile.tempdir = temp_root
    tempfile.TemporaryDirectory = _RepoTemporaryDirectory


def _ensure_test_env():
    """Defaults so in-process FastAPI tests match docker-compose.local.yml and pass env_setup."""
    test_database_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if test_database_url:
        os.environ["DATABASE_URL"] = test_database_url
    elif not os.environ.get("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = (
            "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
        )
    if not os.environ.get("REDIS_URL", "").strip():
        os.environ["REDIS_URL"] = "redis://127.0.0.1:6381/0"
    if not os.environ.get("JWT_SECRET", "").strip():
        os.environ["JWT_SECRET"] = (
            "test-jwt-secret-for-pytest-minimum-32-characters-long"
        )
    if not os.environ.get("GOOGLE_CLIENT_ID", "").strip():
        os.environ["GOOGLE_CLIENT_ID"] = "test.apps.googleusercontent.com"
    if not os.environ.get("GOOGLE_CLIENT_SECRET", "").strip():
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
    if not os.environ.get("FRONTEND_URL", "").strip():
        os.environ["FRONTEND_URL"] = "http://localhost:3000"
    os.environ["CRUCIBAI_DEV"] = "1"
    os.environ["CRUCIBAI_TEST"] = "1"


_ensure_test_env()
_ensure_temp_paths()
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "99999")
os.environ["DISABLE_CSRF_FOR_TEST"] = "1"
os.environ.setdefault("CRUCIBAI_TEST", "1")
os.environ.setdefault("CRUCIBAI_LOG_DIR", str((_TEST_TEMP_ROOT / "logs").resolve()))

pytest_plugins = ("pytest_asyncio",)


def _apply_projection(row, projection):
    if not projection:
        return row
    include = {k for k, v in projection.items() if v}
    exclude = {k for k, v in projection.items() if not v}
    if include:
        row = {k: v for k, v in row.items() if k in include}
    for k in exclude:
        row.pop(k, None)
    return row


class _InMemoryCursor:
    """Motor-style cursor returned by ``_InMemoryCollection.find``."""

    def __init__(self, rows, projection=None):
        self._rows = rows
        self._projection = projection
        self._sort_keys = []
        self._skip_n = 0
        self._limit_n = 0

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, list):
            self._sort_keys = key_or_list
        else:
            self._sort_keys = [(key_or_list, direction or 1)]
        return self

    def skip(self, n):
        self._skip_n = n
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    async def to_list(self, length=None):
        results = list(self._rows)
        if self._sort_keys:
            for key, direction in reversed(self._sort_keys):
                results.sort(
                    key=lambda r, k=key: r.get(k, ""),
                    reverse=(direction == -1),
                )
        if self._skip_n:
            results = results[self._skip_n:]
        limit = self._limit_n or length
        if limit:
            results = results[:limit]
        return [_apply_projection(deepcopy(r), self._projection) for r in results]


class _InMemoryCollection:
    def __init__(self):
        self._rows = []

    @staticmethod
    def _matches(row, query):
        return all(row.get(k) == v for k, v in (query or {}).items())

    async def find_one(self, query=None, projection=None, sort=None):
        rows = [r for r in self._rows if self._matches(r, query)]
        if sort:
            sort_list = sort if isinstance(sort, list) else [sort]
            for key, direction in reversed(sort_list):
                rows.sort(
                    key=lambda r, k=key: r.get(k, ""),
                    reverse=(direction == -1),
                )
        if rows:
            return _apply_projection(deepcopy(rows[0]), projection)
        return None

    def find(self, query=None, projection=None):
        matched = [r for r in self._rows if self._matches(r, query)]
        return _InMemoryCursor(matched, projection)

    async def insert_one(self, document):
        self._rows.append(deepcopy(document))
        return type("InsertResult", (), {"inserted_id": document.get("id")})()

    async def update_one(self, query, update, upsert=False):
        target = None
        for row in self._rows:
            if self._matches(row, query):
                target = row
                break
        if target is None and upsert:
            target = deepcopy(query)
            self._rows.append(target)
        if target is None:
            return {"matched_count": 0, "modified_count": 0}
        for key, value in (update.get("$set") or {}).items():
            target[key] = value
        for key, value in (update.get("$inc") or {}).items():
            target[key] = target.get(key, 0) + value
        return {"matched_count": 1, "modified_count": 1}

    async def count_documents(self, query=None):
        return sum(1 for row in self._rows if self._matches(row, query))

    async def delete_one(self, query):
        for i, row in enumerate(self._rows):
            if self._matches(row, query):
                self._rows.pop(i)
                return {"deleted_count": 1}
        return {"deleted_count": 0}

    async def delete_many(self, query=None):
        before = len(self._rows)
        self._rows = [r for r in self._rows if not self._matches(r, query)]
        return {"deleted_count": before - len(self._rows)}

    async def insert_many(self, documents):
        ids = []
        for doc in documents:
            self._rows.append(deepcopy(doc))
            ids.append(doc.get("id"))
        return {"inserted_ids": ids}


class _FakeDb:
    def __init__(self):
        self.users = _InMemoryCollection()
        self.projects = _InMemoryCollection()
        self.tasks = _InMemoryCollection()
        self.examples = _InMemoryCollection()

    def __getattr__(self, name):
        col = _InMemoryCollection()
        object.__setattr__(self, name, col)
        return col


def pytest_sessionstart(session):
    """Bring up local docker deps when not in GitHub Actions; CI uses service containers + DATABASE_URL."""
    skip_compose = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    compose = _REPO_ROOT / "docker-compose.yml"
    db_ready = False
    if not skip_compose and compose.is_file():
        try:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(compose),
                    "up",
                    "-d",
                    "postgres",
                    "redis",
                ],
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
                db_ready = True
                break
            except OSError:
                time.sleep(1)
        if not ok:
            logger.warning(
                "PostgreSQL not reachable on 127.0.0.1:5434 after 90s. "
                "Continuing so non-database tests can run; database-backed fixtures will fail when used."
            )
    else:
        try:
            s = socket.create_connection(("127.0.0.1", 5434), timeout=2)
            s.close()
            db_ready = True
        except OSError:
            pass

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    if not db_ready:
        os.environ["CRUCIBAI_TEST_DB_UNAVAILABLE"] = "1"
        return

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


BASE_URL = os.environ.get(
    "CRUCIBAI_API_URL", os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
)


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
    import server as server_module
    from db_pg import close_pg_pool, get_db
    from httpx import ASGITransport, AsyncClient
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
        if os.environ.get("CRUCIBAI_TEST_DB_UNAVAILABLE") == "1":
            server_module.db = _FakeDb()
            server_module.audit_logger = None
        else:
            pytest.fail(
                f"PostgreSQL required for tests ({e}). "
                f"Start deps: docker compose up -d postgres redis (repo root). DATABASE_URL={os.environ.get('DATABASE_URL')!r}"
            )

    # Sync deps module so extracted route modules (routes/auth.py etc.) also see the db
    try:
        import deps as _deps

        _deps.init(db=server_module.db, audit_logger=server_module.audit_logger)
    except Exception:
        pass

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        timeout=120.0,
    ) as client:
        yield client

    await close_pg_pool()
    server_module.db = None
    try:
        import deps as _deps

        _deps.init(db=None, audit_logger=None)
    except Exception:
        pass
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
    assert r.status_code in (
        200,
        201,
    ), f"Project create failed: {r.status_code} {r.text}"
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
