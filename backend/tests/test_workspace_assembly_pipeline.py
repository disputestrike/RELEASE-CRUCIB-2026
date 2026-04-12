import os

import pytest
from orchestration.workspace_assembly_pipeline import (
    assembly_v2_enabled,
    extract_json_file_maps,
    materialize_merged_map,
    merge_last_writer,
    parse_proposed_files,
    upsert_assembly_merge_map_paths,
    write_assembly_merge_map,
)


def test_assembly_v2_default_on_with_explicit_opt_out():
    try:
        os.environ.pop("CRUCIBAI_ASSEMBLY_V2", None)
        assert assembly_v2_enabled() is True
        os.environ["CRUCIBAI_ASSEMBLY_V2"] = "0"
        assert assembly_v2_enabled() is False
        os.environ["CRUCIBAI_ASSEMBLY_V2"] = "off"
        assert assembly_v2_enabled() is False
        os.environ["CRUCIBAI_ASSEMBLY_V2"] = "1"
        assert assembly_v2_enabled() is True
    finally:
        os.environ.pop("CRUCIBAI_ASSEMBLY_V2", None)


def test_parse_lang_path_fence():
    raw = """Here is code:
```tsx src/components/Widget.jsx
export function Widget() { return <div/> }
```
"""
    pairs = parse_proposed_files(raw, "src/App.jsx", "Frontend Generation")
    assert any(p[0] == "src/components/Widget.jsx" for p in pairs)


def test_parse_json_file_map_fence():
    raw = r"""
```json
{
  "files": {
    "src/lib/util.ts": "export const x = 1;\n"
  }
}
```
"""
    pairs = parse_proposed_files(raw, "", "Planner")
    assert any(p[0] == "src/lib/util.ts" for p in pairs)


def test_extract_json_file_map_list_shape():
    raw = """```json
[{"path": "api/routes.ts", "content": "export const routes = [];"}]
```"""
    got = extract_json_file_maps(raw)
    assert got == [("api/routes.ts", "export const routes = [];")]


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


def test_write_assembly_merge_map_creates_meta(tmp_path):
    merged = {"src/x.jsx": ("//x", "Frontend Generation")}
    write_assembly_merge_map(str(tmp_path), merged)
    mm = tmp_path / "META" / "merge_map.json"
    assert mm.is_file()
    import json

    doc = json.loads(mm.read_text(encoding="utf-8"))
    assert doc["paths"]["src/x.jsx"]["last_writer_agent"] == "Frontend Generation"


def test_upsert_assembly_merge_map_preserves_other_paths(tmp_path):
    import json

    write_assembly_merge_map(
        str(tmp_path),
        {"a.txt": ("1", "Planner"), "b.txt": ("2", "Design Agent")},
    )
    upsert_assembly_merge_map_paths(
        str(tmp_path),
        {"a.txt": ("3", "Backend Generation")},
    )
    doc = json.loads((tmp_path / "META" / "merge_map.json").read_text(encoding="utf-8"))
    assert doc["paths"]["a.txt"]["last_writer_agent"] == "Backend Generation"
    assert doc["paths"]["b.txt"]["last_writer_agent"] == "Design Agent"
