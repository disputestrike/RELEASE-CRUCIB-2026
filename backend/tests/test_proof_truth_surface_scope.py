from pathlib import Path

from backend.proof import proof_service


def test_detect_published_asset_scope_marks_global_shell(tmp_path, monkeypatch):
    project_id = "proj_scope"
    ws = tmp_path / "projects" / project_id / "dist"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "index.html").write_text(
        '<title>CrucibAI — Inevitable AI</title><script src="/static/js/main.js"></script>',
        encoding="utf-8",
    )

    class _Resolver:
        def project_workspace_path(self, pid: str) -> Path:
            assert pid == project_id
            return tmp_path / "projects" / pid

    monkeypatch.setattr("backend.services.workspace_resolver.workspace_resolver", _Resolver())
    scope = proof_service._detect_published_asset_scope("tsk_abc123def456", project_id)
    assert scope == "global_shell"
