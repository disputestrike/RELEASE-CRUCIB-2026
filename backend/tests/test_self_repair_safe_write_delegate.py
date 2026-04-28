"""self_repair._safe_write must delegate to executor guards (same as swarm path)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from backend.orchestration import self_repair as sr


def test_self_repair_safe_write_accepts_valid_jsx():
    with tempfile.TemporaryDirectory() as td:
        ok = sr._safe_write(
            td,
            "src/App.jsx",
            "import React from 'react'; export default function App(){return null;}\n",
        )
        assert ok is True
        assert (Path(td) / "src" / "App.jsx").is_file()


def test_self_repair_safe_write_blocks_tree_art():
    with tempfile.TemporaryDirectory() as td:
        ok = sr._safe_write(td, "src/Bad.jsx", "├── src/\nexport default function(){return null}\n")
        assert ok is False
