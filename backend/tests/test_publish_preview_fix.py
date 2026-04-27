from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def _install_published_job(
    monkeypatch, workspace_root, *, job_id: str = "job-preview-123"
):
    from backend import server
    from backend.orchestration import runtime_state

    project_id = "project-preview-123"
    monkeypatch.setattr(server, "WORKSPACE_ROOT", workspace_root)

    root = server._project_workspace_path(project_id)
    (root / "dist" / "assets").mkdir(parents=True, exist_ok=True)

    async def fake_get_job(requested_job_id: str):
        if requested_job_id != job_id:
            return None
        return {
            "id": job_id,
            "status": "completed",
            "project_id": project_id,
        }

    monkeypatch.setattr(runtime_state, "get_job", fake_get_job)
    return root, job_id


@pytest.fixture
def workspace_root():
    root = (
        Path(__file__).resolve().parents[2]
        / ".tmp_pytest_manual"
        / f"published-{uuid.uuid4().hex}"
    )
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_published_route_rewrites_assets_and_serves_job_bundle(
    monkeypatch, workspace_root
):
    from backend import server

    root, job_id = _install_published_job(monkeypatch, workspace_root)
    (root / "dist" / "index.html").write_text(
        """<!doctype html><html><head><script type="module" src="/assets/app.js"></script></head><body><div id="root"></div></body></html>""",
        encoding="utf-8",
    )
    (root / "dist" / "assets" / "app.js").write_text(
        "console.log('published-preview-ok');", encoding="utf-8"
    )

    with TestClient(server.app) as client:
        html = client.get(f"/published/{job_id}/")
        asset = client.get(f"/published/{job_id}/assets/app.js")

    assert html.status_code == 200
    assert f"/published/{job_id}/assets/app.js" in html.text
    assert '<base href="/published/job-preview-123/">' in html.text
    assert asset.status_code == 200
    assert "published-preview-ok" in asset.text


def test_published_route_missing_asset_returns_404(monkeypatch, workspace_root):
    from backend import server

    root, job_id = _install_published_job(
        monkeypatch, workspace_root, job_id="job-missing-123"
    )
    (root / "dist" / "index.html").write_text(
        "<!doctype html><h1>Missing asset</h1>", encoding="utf-8"
    )

    with TestClient(server.app) as client:
        response = client.get(f"/published/{job_id}/assets/missing.js")

    assert response.status_code == 404


def test_enrich_job_public_urls_sets_preview_and_deploy(monkeypatch, workspace_root):
    from backend import server

    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai.example.com")
    monkeypatch.setattr(server, "WORKSPACE_ROOT", workspace_root)
    project_id = "project-enrich-123"
    root = server._project_workspace_path(project_id)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text(
        "<!doctype html><h1>Preview</h1>", encoding="utf-8"
    )

    enriched = server._enrich_job_public_urls(
        {
            "id": "job-enrich-123",
            "status": "completed",
            "project_id": project_id,
        }
    )

    assert (
        enriched["preview_url"]
        == "https://crucibai.example.com/published/job-enrich-123/"
    )
    assert (
        enriched["published_url"]
        == "https://crucibai.example.com/published/job-enrich-123/"
    )
    assert (
        enriched["deploy_url"]
        == "https://crucibai.example.com/published/job-enrich-123/"
    )


def test_preview_serve_root_requires_index_html(workspace_root):
    from backend.routes import preview_serve

    workspace = workspace_root / "serve-root"
    (workspace / "build").mkdir(parents=True)
    (workspace / "build" / "asset.js").write_text("console.log('no index')", encoding="utf-8")

    assert preview_serve._resolve_serve_root(workspace) is None

    (workspace / "dist").mkdir()
    (workspace / "dist" / "index.html").write_text("<!doctype html><div id='root'></div>", encoding="utf-8")

    assert preview_serve._resolve_serve_root(workspace) == (workspace / "dist").resolve()


def test_dev_preview_base_prefers_request_origin(monkeypatch):
    from backend.routes import preview_serve

    class RequestStub:
        headers = {}
        base_url = "https://www.crucibai.com/"

    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai-production.up.railway.app")

    assert preview_serve._preview_public_base(RequestStub()) == "https://www.crucibai.com"


def test_dev_preview_base_uses_forwarded_https_origin(monkeypatch):
    from backend.routes import preview_serve

    class RequestStub:
        headers = {"x-forwarded-proto": "https", "x-forwarded-host": "www.crucibai.com"}
        base_url = "http://www.crucibai.com/"

    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai-production.up.railway.app")

    assert preview_serve._preview_public_base(RequestStub()) == "https://www.crucibai.com"


def test_preview_materialize_build_creates_dist_index(monkeypatch, workspace_root):
    from backend.routes import preview_serve

    workspace = workspace_root / "materialize"
    workspace.mkdir()
    (workspace / "package.json").write_text(
        '{"scripts":{"build":"vite build"},"dependencies":{"@vitejs/plugin-react":"latest"}}',
        encoding="utf-8",
    )
    calls = []

    def fake_run(cmd, cwd, capture_output, text, timeout, env, shell):
        calls.append(cmd)
        if cmd[-1] == "build":
            dist = Path(cwd) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<!doctype html><div id='root'>ok</div>", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(preview_serve, "_npm_bin", lambda: "npm")
    monkeypatch.setattr(preview_serve.subprocess, "run", fake_run)

    result = preview_serve._run_preview_build_sync(workspace)

    assert result["ok"] is True
    assert result["reason"] == "preview_build_materialized"
    assert calls == [
        ["npm", "install", "--include=dev", "--no-fund", "--no-audit"],
        ["npm", "run", "build"],
    ]


def test_skip_browser_preview_still_builds_static_artifact(monkeypatch, workspace_root):
    from backend.orchestration import browser_preview_verify

    called = {}

    def fake_materialize(workspace_path: str):
        called["workspace_path"] = workspace_path
        return {"passed": True, "issues": [], "proof": []}

    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")
    monkeypatch.setattr(browser_preview_verify, "_materialize_dist_without_playwright", fake_materialize)

    result = asyncio.run(browser_preview_verify.verify_browser_preview(str(workspace_root)))

    assert called["workspace_path"] == str(workspace_root)
    assert result["passed"] is True
    assert any("static preview build still enforced" in p["title"] for p in result["proof"])
