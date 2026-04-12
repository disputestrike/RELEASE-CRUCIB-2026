import shutil
from pathlib import Path

import pytest

from orchestration.agent_selection_logic import select_agents_for_goal
from orchestration.planner import _should_use_agent_selection
from orchestration.preview_gate import verify_preview_workspace


def test_underwired_realtime_prompt_now_routes_into_selection():
    goal = "Build realtime collaboration editor with shared presence and socket.io"

    assert _should_use_agent_selection(goal) is True
    agents = set(select_agents_for_goal(goal))
    assert "Real-Time Collaboration Agent" in agents


def test_underwired_security_prompt_now_selects_validation_agents():
    goal = "Build enterprise API with CORS, security headers, input validation, and rate limiting"

    assert _should_use_agent_selection(goal) is True
    agents = set(select_agents_for_goal(goal))
    assert "CORS & Security Headers Agent" in agents
    assert "Input Validation Agent" in agents
    assert "Rate Limiting Agent" in agents


@pytest.mark.asyncio
async def test_preview_gate_includes_preflight_feedback(monkeypatch):
    workspace = Path("tmp_runtime_unification")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir()
    (workspace / "package.json").write_text(
        '{"dependencies":{"react":"18","react-dom":"18","react-router-dom":"6","zustand":"4"}}',
        encoding="utf-8",
    )
    src_dir = workspace / "src"
    src_dir.mkdir()
    (src_dir / "main.jsx").write_text(
        "import ReactDOM from 'react-dom/client'; ReactDOM.createRoot(document.getElementById('root'));",
        encoding="utf-8",
    )
    (src_dir / "App.jsx").write_text(
        "export default function App(){ return <div>AuthProvider localStorage BrowserRouter</div> }",
        encoding="utf-8",
    )
    components_dir = src_dir / "components"
    components_dir.mkdir()
    (components_dir / "Shell.jsx").write_text(
        "export default function Shell(){ return null }", encoding="utf-8"
    )

    async def fake_execute(self, context):
        return {
            "status": "ISSUES_FOUND",
            "critical_issues": [
                {
                    "file": "vite.config.js",
                    "issue": "missing config",
                    "suggestion": "create vite config",
                }
            ],
            "warnings": [],
            "total_files_checked": 4,
        }

    async def fake_browser_preview(workspace_path):
        return {"passed": True, "issues": [], "proof": []}

    monkeypatch.setattr(
        "agents.preview_validator_agent.PreviewValidatorAgent.execute", fake_execute
    )
    monkeypatch.setattr(
        "orchestration.browser_preview_verify.verify_browser_preview",
        fake_browser_preview,
    )

    try:
        result = await verify_preview_workspace(str(workspace))

        assert result["passed"] is False
        assert any("Preview preflight:" in issue for issue in result["issues"])
    finally:
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)


def test_server_mounts_job_progress_router():
    import pathlib

    _server = pathlib.Path(__file__).resolve().parents[1] / "server.py"
    source = _server.read_text(encoding="utf-8", errors="replace")

    assert "job_progress_router" in source
    assert 'websocket_url": f"/api/job/' in source
