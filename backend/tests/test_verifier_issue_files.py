"""P1 — compile stderr must yield every path for targeted repair."""

from __future__ import annotations

import tempfile
from pathlib import Path

from backend.orchestration.verifier_issue_files import candidate_files_from_verification_issues


def test_extracts_secondary_paths_from_esbuild_stderr():
    issue = (
        "esbuild failed src/App.jsx: ✘ [ERROR] Unexpected token\n"
        "    src/layouts/SEO.jsx:3:0:\n"
        "    src/charts/Dashboard.jsx:12:4:"
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel in (
            "src/App.jsx",
            "src/layouts/SEO.jsx",
            "src/charts/Dashboard.jsx",
        ):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("// ok\n", encoding="utf-8")
        out = candidate_files_from_verification_issues([issue], str(root))
        assert "src/App.jsx" in out
        assert "src/layouts/SEO.jsx" in out
        assert "src/charts/Dashboard.jsx" in out


def test_extracts_python_trace_paths():
    issue = (
        'Traceback ... File "backend/auth.py", line 2\n'
        "Sorry: IndentationError: expected an indented block (models.py, line 40)"
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "backend").mkdir(parents=True)
        (root / "backend" / "auth.py").write_text("x\n", encoding="utf-8")
        (root / "models.py").write_text("x\n", encoding="utf-8")
        out = candidate_files_from_verification_issues([issue], str(root))
        assert "backend/auth.py" in out
        assert "models.py" in out
