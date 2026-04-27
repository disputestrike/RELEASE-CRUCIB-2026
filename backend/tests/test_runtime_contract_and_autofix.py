from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.orchestration.npm_build_autofix import (
    parse_build_error_location,
    repair_npm_build_failure,
)
from backend.services.runtime_contract import require_canonical_db


def _manual_temp_workspace() -> Path:
    root = Path(__file__).resolve().parents[2] / ".tmp_autofix_tests"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    return path


def test_production_runtime_requires_canonical_db(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")

    with pytest.raises(HTTPException) as exc:
        require_canonical_db(None, action="create_job")

    assert exc.value.status_code == 503
    assert exc.value.detail["failure_reason"] == "database_unavailable"


def test_local_runtime_allows_file_backed_compatibility(monkeypatch):
    for key in ("RAILWAY_ENVIRONMENT", "CRUCIBAI_ENV", "ENVIRONMENT", "APP_ENV", "NODE_ENV"):
        monkeypatch.delenv(key, raising=False)

    assert require_canonical_db(None, action="local_test") is None


def test_parse_build_error_location_from_vite_style_log():
    temp_path = _manual_temp_workspace()
    try:
        app = temp_path / "src" / "App.jsx"
        app.parent.mkdir()
        app.write_text("export default function App(){ return null }\n", encoding="utf-8")

        location = parse_build_error_location("src/App.jsx:1:12: ERROR: Expected ';'", str(temp_path))

        assert location
        assert location["relative_path"] == "src/App.jsx"
        assert location["line"] == 1
        assert location["column"] == 12
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_repair_npm_build_failure_removes_typescript_annotation_in_jsx():
    temp_path = _manual_temp_workspace()
    try:
        app = temp_path / "src" / "App.jsx"
        app.parent.mkdir()
        app.write_text(
            "export default function App() {\n"
            "  const label: string = 'Hello';\n"
            "  return <div>{label}</div>;\n"
            "}\n",
            encoding="utf-8",
        )
        log = "src/App.jsx:2:14: ERROR: Expected ';' but found ':'"

        result = repair_npm_build_failure(str(temp_path), log)

        assert result["changed_files"] == ["src/App.jsx"]
        assert "label = 'Hello'" in app.read_text(encoding="utf-8")
        assert "label: string" not in app.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)
