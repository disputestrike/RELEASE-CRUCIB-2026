"""WS-E smoke test for WorkspaceExplorerAgent."""
import asyncio
import os
from pathlib import Path

import pytest

from agents.workspace_explorer_agent import WorkspaceExplorerAgent


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text(
        '"""Demo module."""\nimport os\n\nclass Foo:\n    def bar(self):\n        return 1\n\n\ndef baz():\n    return 2\n'
    )
    (tmp_path / "requirements.txt").write_text("pytest\nhttpx\n")
    return tmp_path


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_discover(tmp_workspace: Path):
    agent = WorkspaceExplorerAgent(config={"workspace": str(tmp_workspace)})
    result = _run(agent.execute({"action": "discover", "path": str(tmp_workspace)}))
    assert "files" in result and result["file_count"] >= 3
    paths = {f["path"] for f in result["files"]}
    assert "requirements.txt" in paths


def test_symbol_index(tmp_workspace: Path):
    agent = WorkspaceExplorerAgent(config={"workspace": str(tmp_workspace)})
    result = _run(agent.execute({"action": "symbol_index", "path": str(tmp_workspace)}))
    assert "symbols" in result and result["symbol_count"] >= 3
    # Expect Foo, bar, baz
    all_names = {s["name"] for syms in result["symbols"].values() for s in syms}
    assert {"Foo", "bar", "baz"}.issubset(all_names)


def test_file_summary(tmp_workspace: Path):
    agent = WorkspaceExplorerAgent(config={"workspace": str(tmp_workspace)})
    target = str(tmp_workspace / "pkg" / "mod.py")
    result = _run(agent.execute({"action": "file_summary", "path": str(tmp_workspace), "target": target}))
    assert result.get("path") == target
    assert "Demo module" in result.get("docstring", "")
    assert any(s["name"] == "Foo" for s in result.get("symbols", []))


def test_search(tmp_workspace: Path):
    agent = WorkspaceExplorerAgent(config={"workspace": str(tmp_workspace)})
    result = _run(agent.execute({"action": "search", "path": str(tmp_workspace), "query": "baz"}))
    assert "results" in result
    assert result["total_matches"] >= 1


def test_analyze_dependencies(tmp_workspace: Path):
    agent = WorkspaceExplorerAgent(config={"workspace": str(tmp_workspace)})
    result = _run(agent.execute({"action": "analyze_dependencies", "path": str(tmp_workspace)}))
    assert "python" in result.get("dependencies", {})
