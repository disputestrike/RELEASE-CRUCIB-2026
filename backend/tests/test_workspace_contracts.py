from pathlib import Path


def test_final_preview_duplicate_skip_is_off_by_default(monkeypatch):
    from backend.orchestration import auto_runner

    monkeypatch.delenv("CRUCIBAI_SKIP_DUPLICATE_FINAL_PREVIEW", raising=False)

    assert auto_runner._skip_duplicate_final_preview(
        [{"step_key": "verification.preview", "status": "completed"}]
    ) is False


def test_final_preview_duplicate_skip_is_ignored_in_production(monkeypatch):
    from backend.orchestration import auto_runner

    monkeypatch.setenv("CRUCIBAI_SKIP_DUPLICATE_FINAL_PREVIEW", "1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")

    assert auto_runner._skip_duplicate_final_preview(
        [{"step_key": "verification.preview", "status": "completed"}]
    ) is False


def test_workspace_manifest_reports_preview_contract():
    from backend.routes.workspace import _collect_job_workspace_files, _workspace_manifest_payload

    workspace = Path(__file__).resolve().parents[2] / ".tmp_workspace_contracts" / "manifest"
    try:
        (workspace / "src").mkdir(parents=True, exist_ok=True)
        (workspace / "dist").mkdir(parents=True, exist_ok=True)
        (workspace / "package.json").write_text('{"scripts":{"build":"vite build"}}', encoding="utf-8")
        (workspace / "src" / "App.jsx").write_text("export default function App(){return null}", encoding="utf-8")
        (workspace / "dist" / "index.html").write_text("<div id='root'></div>", encoding="utf-8")

        files = _collect_job_workspace_files(workspace, "job-manifest")
        manifest = _workspace_manifest_payload(workspace, "job-manifest", files)

        assert manifest["has_package_json"] is True
        assert manifest["has_app_entry"] is True
        assert manifest["has_dist_index"] is True
        assert manifest["source_count"] >= 2
        assert manifest["preview_artifact_count"] >= 1
        assert manifest["fingerprint"]
    finally:
        import shutil

        shutil.rmtree(workspace.parents[0], ignore_errors=True)


def test_transcript_messages_from_events_normalizes_workspace_transcript():
    from backend.routes.jobs import _transcript_messages_from_events

    messages = _transcript_messages_from_events(
        [
            {"id": "ignored", "event_type": "step_started", "payload_json": "{}"},
            {
                "id": "evt-1",
                "event_type": "workspace_transcript",
                "created_at": "2026-04-26T00:00:00Z",
                "payload_json": '{"role":"assistant","text":"Ready.","ts":123}',
            },
        ],
        "job-1",
    )

    assert messages == [
        {
            "id": "evt-1",
            "jobId": "job-1",
            "role": "assistant",
            "body": "Ready.",
            "text": "Ready.",
            "created_at": "2026-04-26T00:00:00Z",
            "ts": 123,
            "source": "workspace_transcript",
        }
    ]
