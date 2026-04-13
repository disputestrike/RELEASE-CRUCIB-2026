from orchestration.proof_index import (
    build_proof_index_document,
    extract_path_candidates,
    resolve_paths_to_manifest,
)


def test_extract_from_nested_payload():
    payload = {
        "file": "src/App.jsx",
        "issues": ["bad token in src/components/X.tsx"],
        "nested": {"path": "server.py"},
    }
    paths = extract_path_candidates(payload)
    assert "src/App.jsx" in paths
    assert "server.py" in paths
    # sentence-like strings should not match strict REL_PATH
    assert not any("bad token" in p for p in paths)


def test_resolve_paths():
    manifest_paths = {"src/App.jsx", "README.md"}
    r, m = resolve_paths_to_manifest(["src/App.jsx", "missing/zed.jsx"], manifest_paths)
    assert r == ["src/App.jsx"]
    assert m == ["missing/zed.jsx"]


def test_extract_embedded_in_issue_text():
    payload = {"issues": ["syntax error in src/components/X.tsx near line 2"]}
    paths = extract_path_candidates(payload)
    assert "src/components/X.tsx" in paths


def test_build_proof_index_document():
    art = {
        "files": [
            {"path": "src/App.jsx", "sha256": "a", "bytes": 1},
            {"path": "server.py", "sha256": "b", "bytes": 2},
        ]
    }
    items = [
        {
            "id": "p1",
            "step_id": "s1",
            "proof_type": "compile",
            "title": "ok",
            "payload": {"file": "src/App.jsx", "note": "fine"},
        },
        {
            "id": "p2",
            "step_id": "s2",
            "proof_type": "generic",
            "title": "x",
            "payload": {"path": "ghost.py"},
        },
    ]
    doc = build_proof_index_document(
        "job-1", art, items, {"s1": "agents.frontend", "s2": "agents.backend"}
    )
    assert doc["proof_item_count"] == 2
    assert "p1" in doc.get("by_proof_item_id", {})
    assert doc["by_proof_item_id"]["p1"]["paths_resolved_in_manifest"] == [
        "src/App.jsx"
    ]
    e0 = doc["entries"][0]
    assert "src/App.jsx" in e0["paths_resolved_in_manifest"]
    e1 = doc["entries"][1]
    assert e1["paths_missing_from_manifest"] == ["ghost.py"]
    assert "src/App.jsx" in doc["by_path"]
