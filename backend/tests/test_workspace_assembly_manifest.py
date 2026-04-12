from orchestration.workspace_assembly import build_artifact_manifest


def test_build_artifact_manifest_fills_last_writer(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.jsx").write_text("//x", encoding="utf-8")
    owners = {"src/App.jsx": {"step_key": "agents.frontend_generation", "step_id": "s1"}}
    m = build_artifact_manifest(tmp_path, path_owners=owners)
    rows = {r["path"]: r for r in m["files"]}
    assert rows["src/App.jsx"]["last_writer_agent"] == "agents.frontend_generation"
    assert rows["src/App.jsx"]["last_writer_step_id"] == "s1"
