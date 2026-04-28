from pathlib import Path
import shutil
import uuid

from backend.routes.workspace import (
    _collect_job_workspace_files,
    _resolve_job_workspace_file,
)


def _make_test_root() -> Path:
    root = Path(__file__).resolve().parents[2] / ".tmp_workspace_listing_tests" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_job_workspace_files_include_preview_artifacts_when_sources_missing():
    tmp_path = _make_test_root()
    try:
        workspace = tmp_path / "projects" / "project-a"
        (workspace / "dist" / "assets").mkdir(parents=True)
        (workspace / "dist" / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
        (workspace / "dist" / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (workspace / "node_modules" / "ignored").mkdir(parents=True)
        (workspace / "node_modules" / "ignored" / "pkg.js").write_text("ignored", encoding="utf-8")

        files = _collect_job_workspace_files(workspace, "tsk_missing_source")
        paths = {row["path"] for row in files}

        assert "dist/index.html" in paths
        assert "dist/assets/app.js" in paths
        assert not any(path.startswith("node_modules/") for path in paths)
        assert all(row["kind"] == "preview_artifact" for row in files)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_job_workspace_files_prefer_sources_but_keep_preview_artifacts():
    tmp_path = _make_test_root()
    try:
        workspace = tmp_path / "projects" / "project-b"
        (workspace / "src").mkdir(parents=True)
        (workspace / "dist").mkdir(parents=True)
        (workspace / "src" / "App.jsx").write_text("export default function App(){}", encoding="utf-8")
        (workspace / "dist" / "index.html").write_text("<div id='root'></div>", encoding="utf-8")

        files = _collect_job_workspace_files(workspace, "tsk_with_source")
        paths = [row["path"] for row in files]

        assert "src/App.jsx" in paths
        assert "dist/index.html" in paths
        assert paths.index("src/App.jsx") < paths.index("dist/index.html")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_resolve_job_workspace_file_reads_compatible_legacy_root(monkeypatch):
    from backend.routes import workspace as workspace_routes

    tmp_path = _make_test_root()
    try:
        monkeypatch.setattr(workspace_routes, "_workspace_root", lambda: tmp_path / "projects")
        primary = tmp_path / "projects" / "project-c"
        legacy = tmp_path / "project-c"
        primary.mkdir(parents=True)
        legacy.mkdir(parents=True)
        (legacy / "src").mkdir()
        (legacy / "src" / "App.jsx").write_text("export default function App(){}", encoding="utf-8")

        resolved = _resolve_job_workspace_file(primary, "src/App.jsx", "tsk_legacy")

        assert resolved == legacy / "src" / "App.jsx"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_assert_job_access_uses_runtime_project_id(monkeypatch):
    from backend.routes import workspace as workspace_routes

    async def fake_get_pg_pool():
        return None

    async def fake_get_job(job_id: str):
        return {
            "id": job_id,
            "project_id": "project-from-runtime",
            "user_id": "user-1",
        }

    def fake_assert_owner(owner_id, user):
        assert owner_id == "user-1"
        assert user["id"] == "user-1"

    class FakeRuntimeState:
        async def get_job(self, job_id: str):
            return await fake_get_job(job_id)

        def set_pool(self, pool):
            raise AssertionError("pool should be None in this test")

    monkeypatch.setattr(workspace_routes, "get_pg_pool", fake_get_pg_pool, raising=False)
    monkeypatch.setattr("backend.db_pg.get_pg_pool", fake_get_pg_pool)
    monkeypatch.setattr("backend.server._assert_job_owner_match", fake_assert_owner)
    monkeypatch.setattr("backend.orchestration.runtime_state.get_job", fake_get_job)
    monkeypatch.setattr(workspace_routes, "_project_workspace_path", lambda pid: Path("/tmp/workspaces/projects") / pid)

    import asyncio

    workspace = asyncio.run(
        workspace_routes._assert_job_access("tsk_runtime", {"id": "user-1"})
    )

    assert workspace.as_posix().endswith("/projects/project-from-runtime")
