from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_orchestration_hook_files_exist():
    assert (ROOT / "frontend/src/hooks/useWebSocket.js").exists()
    assert (ROOT / "frontend/src/hooks/useJobProgress.js").exists()


def test_orchestration_component_files_exist():
    expected = [
        "frontend/src/components/orchestration/KanbanBoard.jsx",
        "frontend/src/components/orchestration/PhaseGroup.jsx",
        "frontend/src/components/orchestration/AgentCard.jsx",
        "frontend/src/components/orchestration/ProgressBar.jsx",
        "frontend/src/components/orchestration/LiveLog.jsx",
        "frontend/src/components/orchestration/orchestration.module.css",
        "frontend/src/components/orchestration/index.jsx",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel


def test_orchestration_index_is_barrel_not_css_dump():
    text = (ROOT / "frontend/src/components/orchestration/index.jsx").read_text(
        encoding="utf-8"
    )
    assert "export { default as KanbanBoard }" in text
    assert ".kanbanContainer" not in text


def test_live_orchestration_board_is_mounted_in_workspace_surfaces():
    """CF21 — canonical workspace is now WorkspaceV3Shell (CrucibAIWorkspace was deleted in EX17).

    Ensures the live orchestration surfaces are wired into the V3 shell directly so
    users get Controller Brain + Kanban + job stream without going through legacy panels.
    """
    panels = (
        ROOT / "frontend/src/components/workspace/WorkspaceProPanels.jsx"
    ).read_text(encoding="utf-8")
    v3_shell = (ROOT / "frontend/src/pages/WorkspaceV3Shell.jsx").read_text(encoding="utf-8")
    kanban = (ROOT / "frontend/src/components/orchestration/KanbanBoard.jsx").read_text(
        encoding="utf-8"
    )

    assert "KanbanBoard" in panels
    assert "useJobStream" in v3_shell
    assert "KanbanBoard" in v3_shell
    assert "data-testid=\"crucib-workspace-root\"" in v3_shell
    assert "Controller Brain" in kanban
    assert "Recommended focus" in kanban
    assert "Next actions" in kanban
    assert "Project Memory" in kanban
    assert "Recent memories" in kanban
