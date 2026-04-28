"""Pollution guards for OpsLedger-class wrong-language-in-file failures."""

from __future__ import annotations


from backend.orchestration.file_language_sanity import (
    detect_write_time_violations,
    sniff_touched_files_language_mismatch,
)


def test_detect_tree_art_in_jsx():
    bad = '├── src/\n│   └── App.jsx\nexport default function Layout() {}'
    v = detect_write_time_violations("src/components/Layout.jsx", bad)
    assert any("tree" in m.lower() or "├" in m for m in v)


def test_detect_package_json_fragment_in_jsx():
    bad = '''{
  "name": "opsledger",
  "version": "1.0.0"
}
'''
    v = detect_write_time_violations("src/charts/Dashboard.jsx", bad)
    assert any("json" in m.lower() or "manifest" in m.lower() for m in v)


def test_allow_valid_react_component():
    ok = """import React from 'react';
export default function Dashboard() {
  return <div>ok</div>;
}
"""
    assert detect_write_time_violations("src/charts/Dashboard.jsx", ok) == []


def test_detect_express_in_python():
    bad = """import { Router } from 'express';
def x():
    pass
"""
    v = detect_write_time_violations("backend/auth.py", bad)
    assert any("express" in m.lower() or "es-module" in m.lower() for m in v)


def test_sniff_touched_reads_workspace_files(tmp_path: Path):
    root = tmp_path
    p = root / "src" / "bad.jsx"
    p.parent.mkdir(parents=True)
    p.write_text('├── foo\nexport default function X(){return null}', encoding="utf-8")
    issues = sniff_touched_files_language_mismatch(
        str(root), ["src/bad.jsx"], max_files=10
    )
    assert len(issues) >= 1
