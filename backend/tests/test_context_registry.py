import json
from pathlib import Path

from orchestration.context_registry import merge_file_ownership, REGISTRY_FILENAME, REGISTRY_REL_DIR


def test_merge_file_ownership_writes_registry(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    merge_file_ownership(
        str(ws),
        job_id="job_1",
        step_key="agents.planner",
        paths=["/src/App.jsx", "src/main.tsx"],
        verification_status="verified",
    )
    reg = ws / REGISTRY_REL_DIR / REGISTRY_FILENAME
    assert reg.is_file()
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert data.get("job_id") == "job_1"
    assert "/src/App.jsx" in data.get("files", {})
    assert "/src/main.tsx" in data.get("files", {})
    assert data["files"]["/src/App.jsx"]["last_step"] == "agents.planner"


def test_merge_file_ownership_ignores_path_traversal(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    merge_file_ownership(
        str(ws),
        job_id="job_1",
        step_key="x",
        paths=["/../../etc/passwd", "/../secret"],
        verification_status="verified",
    )
    reg = ws / REGISTRY_REL_DIR / REGISTRY_FILENAME
    assert reg.is_file()
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert "/etc/passwd" not in data.get("files", {})
    assert "/secret" not in data.get("files", {})
