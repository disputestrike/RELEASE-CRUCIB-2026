"""Export ZIP profiles and README stack alignment."""
import json
from pathlib import Path

from orchestration.readme_stack_guard import sanitize_readme_for_workspace
from orchestration.workspace_assembly import iter_files_for_zip


def test_iter_files_for_zip_handoff_skips_outputs(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "outputs").mkdir()
    (root / "outputs" / "Planner.md").write_text("noise", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "App.jsx").write_text("export default function App(){}", encoding="utf-8")

    full = {a for a, _ in iter_files_for_zip(root, "full")}
    handoff = {a for a, _ in iter_files_for_zip(root, "handoff")}

    assert any(a.startswith("outputs/") for a in full)
    assert "src/App.jsx" in full
    assert not any(a.startswith("outputs/") for a in handoff)
    assert "src/App.jsx" in handoff


def test_sanitize_readme_removes_django_commands_for_vite(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "package.json").write_text(
        json.dumps({"devDependencies": {"vite": "^5.0.0"}, "scripts": {"dev": "vite"}}),
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Demo\n\npython manage.py migrate\npython manage.py runserver\n",
        encoding="utf-8",
    )
    assert sanitize_readme_for_workspace(root) is True
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "manage.py" not in text.lower()
    assert "npm run dev" in text


def test_sanitize_readme_skips_when_django_project(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "manage.py").write_text("# django\n", encoding="utf-8")
    (root / "README.md").write_text("python manage.py runserver\n", encoding="utf-8")
    assert sanitize_readme_for_workspace(root) is False
