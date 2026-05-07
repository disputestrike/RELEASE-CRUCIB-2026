from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.orchestration import pipeline_orchestrator
from backend.orchestration.build_reliability import npm_install_with_retry


def test_npm_install_forces_dev_dependencies_on_production_hosts(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("backend.orchestration.build_reliability.subprocess.run", fake_run)

    rc, stdout, stderr = npm_install_with_retry(str(tmp_path))

    assert rc == 0
    assert stdout == "ok"
    assert stderr == ""
    cmd, kwargs = calls[0]
    assert str(cmd[0]).lower().endswith(("npm", "npm.cmd"))
    assert cmd[1] == "install"
    assert "--include=dev" in cmd
    assert kwargs["env"]["NODE_ENV"] == "development"
    assert kwargs["env"]["NPM_CONFIG_PRODUCTION"] == "false"


def test_build_command_uses_local_node_bin(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env") or {}
        return SimpleNamespace(returncode=0, stdout="built", stderr="")

    monkeypatch.setattr(pipeline_orchestrator.subprocess, "run", fake_run)

    rc, stdout, stderr = pipeline_orchestrator._run_command_sync(["npm", "run", "build"], str(tmp_path))

    assert rc == 0
    assert stdout == "built"
    assert stderr == ""
    assert str(seen["cmd"][0]).lower().endswith(("npm", "npm.cmd"))
    assert seen["cmd"][1:] == ["run", "build"]
    assert str(tmp_path / "node_modules" / ".bin") in seen["env"]["PATH"]
    assert seen["env"]["NODE_ENV"] == "development"


@pytest.mark.asyncio
async def test_deterministic_workspace_is_written_when_model_returns_no_files(tmp_path):
    events = []

    async def on_progress(event_type, payload):
        events.append((event_type, payload))

    written = await pipeline_orchestrator._write_deterministic_workspace(
        str(tmp_path),
        "Build a multi-page SaaS product UI with pricing and contact sections",
        {"build_type": "saas_app"},
        on_progress=on_progress,
    )

    assert "package.json" in written
    assert any(path.startswith("src/") for path in written)
    assert (tmp_path / "package.json").exists()
    assert (tmp_path / "src").exists()
    assert any(event_type == "workspace_files_updated" for event_type, _ in events)
