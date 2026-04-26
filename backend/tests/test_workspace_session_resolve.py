import tempfile
from pathlib import Path

from backend.routes import workspace


def test_workspace_session_derives_job_ids_from_task_and_session_ids():
    assert workspace._stable_task_id_for_job("job_123") == "task_job_job_123"
    assert workspace._job_id_from_task_id("task_job_job_123") == "job_123"
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
