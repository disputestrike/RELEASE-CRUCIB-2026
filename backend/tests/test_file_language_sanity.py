from pathlib import Path

from orchestration.file_language_sanity import sniff_touched_files_language_mismatch


def test_detects_python_triple_quote_in_tsx(tmp_path: Path):
    ws = tmp_path / "w"
    ws.mkdir()
    f = ws / "src" / "Bad.tsx"
    f.parent.mkdir(parents=True)
    f.write_text('"""\nnot ts\n"""\nexport default function X(){return null}', encoding="utf-8")
    issues = sniff_touched_files_language_mismatch(str(ws), ["src/Bad.tsx"])
    assert issues and "triple" in issues[0].lower()


def test_detects_invalid_json(tmp_path: Path):
    ws = tmp_path / "w"
    ws.mkdir()
    f = ws / "data.json"
    f.write_text("{ not json", encoding="utf-8")
    issues = sniff_touched_files_language_mismatch(str(ws), ["data.json"])
    assert any("invalid json" in i.lower() for i in issues)


def test_clean_react_file_ok(tmp_path: Path):
    ws = tmp_path / "w"
    ws.mkdir()
    f = ws / "App.jsx"
    f.write_text("import React from 'react';\nexport default function App(){return null}", encoding="utf-8")
    assert sniff_touched_files_language_mismatch(str(ws), ["App.jsx"]) == []


def test_sql_file_python_def_detected(tmp_path: Path):
    ws = tmp_path / "w"
    ws.mkdir()
    f = ws / "db" / "bad.sql"
    f.parent.mkdir(parents=True)
    f.write_text("def migrate():\n  pass\n", encoding="utf-8")
    issues = sniff_touched_files_language_mismatch(str(ws), ["db/bad.sql"])
    assert issues and "def/class" in issues[0].lower()
