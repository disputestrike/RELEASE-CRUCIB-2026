import tempfile
from pathlib import Path

import backend.config as config
from backend.services.workspace_resolver import WorkspaceResolver


def test_workspace_resolver_prefers_project_workspace_for_jobs(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="crucib_resolver_") as temp:
        root = Path(temp)
        monkeypatch.setattr(config, "WORKSPACE_ROOT", root)
        resolver = WorkspaceResolver()
        primary = root / "projects" / "proj_123"
        primary.mkdir(parents=True)

        resolved = resolver.workspace_for_job("job_123", "proj_123")

    assert resolved.job_id == "job_123"
    assert resolved.project_id == "proj_123"
    assert resolved.workspace == primary.resolve()
    assert resolved.dist_path == primary.resolve() / "dist"
    assert resolved.package_path == primary.resolve() / "package.json"
    assert resolved.preview_url == "/api/preview/job_123/serve"


def test_workspace_resolver_includes_legacy_job_roots(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="crucib_resolver_") as temp:
        root = Path(temp)
        monkeypatch.setattr(config, "WORKSPACE_ROOT", root)
        resolver = WorkspaceResolver()
        legacy = root / "job_123"
        legacy.mkdir(parents=True)

        resolved = resolver.workspace_for_job("job_123", "proj_123")
        candidates = {str(path) for path in resolved.candidates}

    assert resolved.workspace == legacy.resolve()
    assert str((root / "projects" / "proj_123").resolve()) in candidates
    assert str((root / "projects" / "job_123").resolve()) in candidates
    assert str(legacy.resolve()) in candidates
