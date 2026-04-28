import tempfile
from pathlib import Path

from backend.orchestration.auto_runner import _verify_final_preview_servability


def test_final_preview_servability_fails_without_static_index():
    with tempfile.TemporaryDirectory(prefix="crucib_final_preview_") as temp:
        workspace = Path(temp)
        (workspace / "package.json").write_text("{}", encoding="utf-8")

        result = _verify_final_preview_servability("job_123", str(workspace), {"project_id": "proj_123"})

    assert result["passed"] is False
    assert result["failure_reason"] == "preview_not_servable"
    assert result["issues"]


def test_final_preview_servability_requires_mount_root():
    with tempfile.TemporaryDirectory(prefix="crucib_final_preview_") as temp:
        workspace = Path(temp)
        (workspace / "dist").mkdir()
        (workspace / "dist" / "index.html").write_text("<html><body>No mount here</body></html>", encoding="utf-8")

        result = _verify_final_preview_servability("job_123", str(workspace), {"project_id": "proj_123"})

    assert result["passed"] is False
    assert result["failure_reason"] == "preview_not_servable"
    assert "root/app mount" in result["issues"][0]


def test_final_preview_servability_accepts_dist_index_with_root():
    with tempfile.TemporaryDirectory(prefix="crucib_final_preview_") as temp:
        workspace = Path(temp)
        (workspace / "dist").mkdir()
        (workspace / "dist" / "index.html").write_text('<html><body><div id="root"></div></body></html>', encoding="utf-8")

        result = _verify_final_preview_servability("job_123", str(workspace), {"project_id": "proj_123"})

    assert result["passed"] is True
    assert result["dev_server_url"] == "/api/preview/job_123/serve"
    assert result["content_type"].startswith("text/html")
