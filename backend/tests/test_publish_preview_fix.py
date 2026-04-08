from __future__ import annotations

from fastapi.testclient import TestClient


def _install_published_job(monkeypatch, tmp_path, *, job_id: str = "job-preview-123"):
    import server
    from orchestration import runtime_state

    project_id = "project-preview-123"
    monkeypatch.setattr(server, "WORKSPACE_ROOT", tmp_path)

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


def test_published_route_rewrites_assets_and_serves_job_bundle(monkeypatch, tmp_path):
    import server

    root, job_id = _install_published_job(monkeypatch, tmp_path)
    (root / "dist" / "index.html").write_text(
        """<!doctype html><html><head><script type="module" src="/assets/app.js"></script></head><body><div id="root"></div></body></html>""",
        encoding="utf-8",
    )
    (root / "dist" / "assets" / "app.js").write_text("console.log('published-preview-ok');", encoding="utf-8")

    with TestClient(server.app) as client:
        html = client.get(f"/published/{job_id}/")
        asset = client.get(f"/published/{job_id}/assets/app.js")

    assert html.status_code == 200
    assert f'/published/{job_id}/assets/app.js' in html.text
    assert '<base href="/published/job-preview-123/">' in html.text
    assert asset.status_code == 200
    assert "published-preview-ok" in asset.text


def test_published_route_missing_asset_returns_404(monkeypatch, tmp_path):
    import server

    root, job_id = _install_published_job(monkeypatch, tmp_path, job_id="job-missing-123")
    (root / "dist" / "index.html").write_text("<!doctype html><h1>Missing asset</h1>", encoding="utf-8")

    with TestClient(server.app) as client:
        response = client.get(f"/published/{job_id}/assets/missing.js")

    assert response.status_code == 404


def test_enrich_job_public_urls_sets_preview_and_deploy(monkeypatch, tmp_path):
    import server

    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai.example.com")
    monkeypatch.setattr(server, "WORKSPACE_ROOT", tmp_path)
    project_id = "project-enrich-123"
    root = server._project_workspace_path(project_id)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text("<!doctype html><h1>Preview</h1>", encoding="utf-8")

    enriched = server._enrich_job_public_urls(
        {
            "id": "job-enrich-123",
            "status": "completed",
            "project_id": project_id,
        }
    )

    assert enriched["preview_url"] == "https://crucibai.example.com/published/job-enrich-123/"
    assert enriched["published_url"] == "https://crucibai.example.com/published/job-enrich-123/"
    assert enriched["deploy_url"] == "https://crucibai.example.com/published/job-enrich-123/"
