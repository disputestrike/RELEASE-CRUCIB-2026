import json

from orchestration.workspace_assembly import (
    build_artifact_manifest,
    merge_map_owner_overlay,
)


def test_build_artifact_manifest_fills_last_writer(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.jsx").write_text("//x", encoding="utf-8")
    owners = {
        "src/App.jsx": {"step_key": "agents.frontend_generation", "step_id": "s1"}
    }
    m = build_artifact_manifest(tmp_path, path_owners=owners)
    rows = {r["path"]: r for r in m["files"]}
    assert rows["src/App.jsx"]["last_writer_agent"] == "agents.frontend_generation"
    assert rows["src/App.jsx"]["last_writer_step_id"] == "s1"


def test_merge_map_owner_overlay_reads_meta(tmp_path):
    meta = tmp_path / "META"
    meta.mkdir(parents=True)
    (meta / "merge_map.json").write_text(
        json.dumps(
            {
                "paths": {
                    "src/App.jsx": {"last_writer_agent": "Planner"},
                }
            }
        ),
        encoding="utf-8",
    )
    o = merge_map_owner_overlay(tmp_path)
    assert o["src/App.jsx"]["step_key"] == "Planner"


def test_build_artifact_manifest_event_owner_over_merge_map(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.jsx").write_text("//x", encoding="utf-8")
    merge_o = {"src/App.jsx": {"step_key": "from_merge", "step_id": ""}}
    event_o = {"src/App.jsx": {"step_key": "from_event", "step_id": "e1"}}
    combined = dict(merge_o)
    combined.update(event_o)
    m = build_artifact_manifest(tmp_path, path_owners=combined)
    rows = {r["path"]: r for r in m["files"]}
    assert rows["src/App.jsx"]["last_writer_agent"] == "from_event"
    assert rows["src/App.jsx"]["last_writer_step_id"] == "e1"


def test_ensure_preview_writes_next_app_stub(tmp_path):
    from orchestration.executor import _ensure_preview_contract_files

    job = {"goal": "Use Next.js App Router", "build_target": "next_app_router"}
    written = _ensure_preview_contract_files(str(tmp_path), job)
    assert any(str(w).startswith("next-app-stub/") for w in written)
    assert (tmp_path / "next-app-stub" / "app" / "page.tsx").is_file()
