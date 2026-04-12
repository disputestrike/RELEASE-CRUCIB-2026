import os

import pytest

from orchestration.workspace_assembly_pipeline import (
    assembly_v2_enabled,
    merge_last_writer,
    parse_proposed_files,
    materialize_merged_map,
)


def test_assembly_v2_default_off():
    os.environ.pop("CRUCIBAI_ASSEMBLY_V2", None)
    assert assembly_v2_enabled() is False
    os.environ["CRUCIBAI_ASSEMBLY_V2"] = "1"
    assert assembly_v2_enabled() is True
    os.environ.pop("CRUCIBAI_ASSEMBLY_V2", None)


def test_parse_lang_path_fence():
    raw = """Here is code:
```tsx src/components/Widget.jsx
export function Widget() { return <div/> }
```
"""
    pairs = parse_proposed_files(raw, "src/App.jsx", "Frontend Generation")
    assert any(p[0] == "src/components/Widget.jsx" for p in pairs)


def test_parse_fallback_default():
    raw = "const App = () => <div>ok</div>\nexport default App\n"
    pairs = parse_proposed_files(raw, "src/App.jsx", "Frontend Generation")
    assert pairs and pairs[0][0] == "src/App.jsx"


def test_merge_last_writer():
    m = merge_last_writer(
        [
            ("a.txt", "one", "A"),
            ("b.txt", "two", "B"),
            ("a.txt", "three", "C"),
        ]
    )
    assert m["a.txt"][0] == "three"
    assert m["a.txt"][1] == "C"


def test_materialize_merged_map_writes(tmp_path):
    merged = {
        "src/x.jsx": ("export default function X(){return null}", "Test"),
        "notes/readme.md": ("# hi", "Test"),
    }
    written, err = materialize_merged_map(str(tmp_path), merged)
    assert not err
    assert "src/x.jsx" in written
    p = tmp_path / "src" / "x.jsx"
    assert p.is_file()
    assert "export default" in p.read_text(encoding="utf-8")
