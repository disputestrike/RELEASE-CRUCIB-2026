"""
Job-scoped workspace API: list/read files via job id (project_id resolved server-side).
Uses async app_client + auth_headers like the rest of backend/tests.
"""
from __future__ import annotations

import shutil
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def mock_job_with_project(app_client, auth_headers):
    """Registered user, PG job row, and one file on disk under WORKSPACE_ROOT/{project_id}."""
    import project_state
    from db_pg import get_pg_pool
    from orchestration import runtime_state as rs

    r_me = await app_client.get("/api/auth/me", headers=auth_headers, timeout=10)
    assert r_me.status_code == 200
    me = r_me.json()
    user_id = me.get("id") or (me.get("user") or {}).get("id")
    assert user_id, f"auth/me missing id: {me}"

    pool = await get_pg_pool()
    rs.set_pool(pool)

    project_id = str(uuid.uuid4())
    job = await rs.create_job(project_id=project_id, mode="guided", goal="pytest job workspace", user_id=user_id)
    job_id = job["id"]

    safe = project_id.replace("/", "_").replace("\\", "_")
    root = project_state.WORKSPACE_ROOT / safe
    root.mkdir(parents=True, exist_ok=True)
    src = root / "src"
    src.mkdir(exist_ok=True)
    marker = f"job-ws-{job_id[:8]}"
    (src / "App.jsx").write_text(f"export default function App(){{ return <div>{marker}</div>; }}", encoding="utf-8")

    ns = SimpleNamespace(id=job_id, project_id=project_id, marker=marker)
    try:
        yield ns
    finally:
        shutil.rmtree(root, ignore_errors=True)


async def test_get_job_workspace_files(app_client, auth_headers, mock_job_with_project):
    job_id = mock_job_with_project.id
    resp = await app_client.get(f"/api/jobs/{job_id}/workspace/files", headers=auth_headers, timeout=15)
    assert resp.status_code == 200
    body = resp.json()
    assert "files" in body
    assert "src/App.jsx" in body["files"]


async def test_get_job_workspace_files_ignores_project_id_query_param(app_client, auth_headers, mock_job_with_project):
    """Spurious project_id must not switch which workspace is listed (resolution is from the job only)."""
    job_id = mock_job_with_project.id
    wrong = "00000000-0000-0000-0000-000000000001"
    resp = await app_client.get(
        f"/api/jobs/{job_id}/workspace/files",
        headers=auth_headers,
        params={"project_id": wrong},
        timeout=15,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "files" in body
    assert "src/App.jsx" in body["files"]


async def test_get_job_workspace_file_ignores_project_id_query_param(app_client, auth_headers, mock_job_with_project):
    job_id = mock_job_with_project.id
    wrong = "00000000-0000-0000-0000-000000000002"
    resp = await app_client.get(
        f"/api/jobs/{job_id}/workspace/file",
        headers=auth_headers,
        params={"path": "src/App.jsx", "project_id": wrong},
        timeout=15,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("path") == "src/App.jsx"
    assert mock_job_with_project.marker in (data.get("content") or "")


async def test_get_job_workspace_files_requires_auth(app_client, mock_job_with_project):
    job_id = mock_job_with_project.id
    resp = await app_client.get(f"/api/jobs/{job_id}/workspace/files", timeout=10)
    assert resp.status_code == 401
