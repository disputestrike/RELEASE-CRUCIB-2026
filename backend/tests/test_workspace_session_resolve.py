import importlib
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from backend.routes import workspace


def test_workspace_session_derives_job_ids_from_task_and_session_ids():
    assert workspace._stable_task_id_for_job("job_123") == "task_job_job_123"
    assert workspace._job_id_from_task_id("task_job_job_123") == "job_123"
    assert workspace._job_id_from_task_id("tsk_9ef99f68f89e") == "tsk_9ef99f68f89e"
    assert workspace._job_id_from_task_id("tsk_DEADBEEF1234") == "tsk_DEADBEEF1234"
    assert workspace._job_id_from_task_id("tsk_short") is None
    assert workspace._job_id_from_task_id("task_abc") is None
    assert workspace._job_id_from_session_id("job:job_456") == "job_456"
    assert workspace._job_id_from_session_id("task_job_job_789") == "job_789"
    assert workspace._project_id_from_session_id("project:proj_123") == "proj_123"


def test_workspace_session_payload_uses_backend_job_as_canonical_source():
    with tempfile.TemporaryDirectory(prefix="crucib_session_") as temp:
        temp_path = Path(temp)
        files = [
            {"path": "package.json", "size": 2, "kind": "source"},
            {"path": "src/App.jsx", "size": 12, "kind": "source"},
        ]
        payload = workspace._workspace_session_payload(
            job={
                "id": "job_123",
                "project_id": "proj_123",
                "status": "running",
                "goal": "Build a complete app",
            },
            job_id="job_123",
            task_id="task_random_local",
            project_id=None,
            workspace=temp_path,
            files=files,
            resolved_from="job",
        )

    assert payload["sessionId"] == "job:job_123"
    assert payload["taskId"] == "task_job_job_123"
    assert payload["jobId"] == "job_123"
    assert payload["projectId"] == "proj_123"
    assert payload["threadId"] == "job:job_123"
    assert payload["status"] == "running"
    assert payload["previewStatus"]["status"] == "building"


def test_preview_status_requires_a_servable_index():
    with tempfile.TemporaryDirectory(prefix="crucib_session_") as temp:
        temp_path = Path(temp)
        (temp_path / "package.json").write_text("{}", encoding="utf-8")
        (temp_path / "src").mkdir()
        (temp_path / "src" / "App.jsx").write_text("export default function App() { return null }", encoding="utf-8")
        files = workspace._collect_workspace_files_from_root(temp_path)

        building = workspace._preview_status_for_session("job_123", temp_path, files)
        assert building["status"] == "building"
        assert building["url"] is None

        (temp_path / "dist").mkdir()
        (temp_path / "dist" / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
        files = workspace._collect_workspace_files_from_root(temp_path)
        ready = workspace._preview_status_for_session("job_123", temp_path, files)

    assert ready["status"] == "ready"
    assert ready["url"] == "/api/preview/job_123/serve"
    assert ready["manifest"]["has_dist_index"] is True


@pytest.mark.asyncio
async def test_preview_project_id_falls_back_to_build_plans(monkeypatch):
    """When runtime and jobs.project_id are empty, serve preview resolves via build_plans."""
    from backend.routes import preview_serve

    async def fake_get_job(_jid: str):
        return None

    rs_mod = importlib.import_module("backend.orchestration.runtime_state")
    monkeypatch.setattr(rs_mod, "get_job", fake_get_job)

    class FakeConn:
        async def fetchrow(self, sql: str, *args):
            s = sql.lower()
            if "from jobs" in s:
                return None
            if "from build_plans" in s:
                return {"project_id": "proj-from-build-plan"}
            return None

    class FakePool:
        @asynccontextmanager
        async def acquire(self):
            yield FakeConn()

    async def fake_get_pg_pool():
        return FakePool()

    monkeypatch.setattr("backend.db_pg.get_pg_pool", fake_get_pg_pool)

    pid = await preview_serve._get_project_id_for_job("tsk_anyjobid0001")
    assert pid == "proj-from-build-plan"


@pytest.mark.asyncio
async def test_project_only_resolve_can_recover_latest_job(monkeypatch):
    class FakeConn:
        async def fetchrow(self, sql: str, *args):
            assert "from jobs" in sql.lower()
            return {
                "id": "tsk_9ef99f68f89e",
                "project_id": "proj_123",
                "user_id": "user_1",
                "status": "running",
                "goal": "Build store",
            }

    class FakePool:
        @asynccontextmanager
        async def acquire(self):
            yield FakeConn()

    async def fake_get_pg_pool():
        return FakePool()

    def fake_owner_assert(job_user_id, user):
        assert job_user_id == "user_1"
        assert user.get("sub") == "user_1"

    monkeypatch.setattr("backend.db_pg.get_pg_pool", fake_get_pg_pool)
    monkeypatch.setattr("backend.server._assert_job_owner_match", fake_owner_assert)

    job = await workspace._load_latest_job_for_project("proj_123", {"sub": "user_1"})
    assert job is not None
    assert job["id"] == "tsk_9ef99f68f89e"
    assert job["project_id"] == "proj_123"


@pytest.mark.asyncio
async def test_project_only_resolve_latest_job_returns_none_when_missing(monkeypatch):
    class FakeConn:
        async def fetchrow(self, sql: str, *args):
            return None

    class FakePool:
        @asynccontextmanager
        async def acquire(self):
            yield FakeConn()

    async def fake_get_pg_pool():
        return FakePool()

    monkeypatch.setattr("backend.db_pg.get_pg_pool", fake_get_pg_pool)
    monkeypatch.setattr("backend.server._assert_job_owner_match", lambda *_: None)

    job = await workspace._load_latest_job_for_project("proj_123", {"sub": "user_1"})
    assert job is None
