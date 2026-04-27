import io
import shutil
import uuid
import zipfile
from pathlib import Path

import pytest


async def _read_streaming_response(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
    return b"".join(chunks)


@pytest.mark.asyncio
async def test_job_workspace_download_zip_preserves_code_tree(monkeypatch):
    from backend.routes import workspace

    scratch = Path(".tmp_workspace_download_tests") / uuid.uuid4().hex
    root = scratch / "generated"
    try:
        (root / "src" / "components").mkdir(parents=True)
        (root / "src" / "components" / "Card.jsx").write_text("export default function Card(){}", encoding="utf-8")
        (root / "package.json").write_text('{"scripts":{"build":"vite build"}}', encoding="utf-8")
        (root / "node_modules" / "skip-me").mkdir(parents=True)
        (root / "node_modules" / "skip-me" / "index.js").write_text("huge", encoding="utf-8")

        async def fake_assert_job_access(job_id, user):
            assert job_id == "job-download-1"
            assert user == {"id": "user-1"}
            return root

        monkeypatch.setattr(workspace, "_assert_job_access", fake_assert_job_access)

        response = await workspace.download_job_workspace_zip("job-download-1", user={"id": "user-1"})
        payload = await _read_streaming_response(response)

        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            names = set(zf.namelist())

        assert "src/components/Card.jsx" in names
        assert "package.json" in names
        assert "node_modules/skip-me/index.js" not in names
        assert response.media_type == "application/zip"
        assert "crucibai-build-job-down.zip" in response.headers["content-disposition"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_workspace_download_route_aliases_exist():
    from backend.routes import workspace

    paths = {route.path for route in workspace.router.routes}

    assert "/api/jobs/{job_id}/workspace/download" in paths
    assert "/api/jobs/{job_id}/workspace-zip" in paths
    assert "/api/jobs/{job_id}/export/full.zip" in paths
