"""P3 — regression for legacy four-file File Tool path (CRUCIBAI_ASSEMBLY_V2 opt-out / fallback)."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from orchestration.legacy_file_tool_writes import run_legacy_file_tool_writes


def _extract(out, filepath: str = "") -> str:  # noqa: ARG001 — matches legacy extract_code shape
    if isinstance(out, str):
        return out.strip()
    if isinstance(out, dict):
        raw = out.get("output") or out.get("result") or out.get("code") or ""
        return raw.strip() if isinstance(raw, str) else ""
    return ""


@pytest.mark.asyncio
async def test_run_legacy_file_tool_writes_writes_frontend_app():
    pid = f"pytest_legacy_ft_{uuid.uuid4().hex[:12]}"
    ws = Path(__file__).resolve().parents[1] / "workspace" / pid
    try:
        prev = {
            "Frontend Generation": {
                "output": "export default function App() { return <div data-testid='x'>ok</div>; }",
            },
        }
        res = await run_legacy_file_tool_writes(pid, prev, _extract)
        assert res.get("status") == "completed"
        assert "src/App.jsx" in (res.get("files_written") or [])
        app = ws / "src" / "App.jsx"
        assert app.is_file()
        assert "data-testid" in app.read_text(encoding="utf-8")
    finally:
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)
