from pathlib import Path

from orchestration.artifact_delta import (
    cap_delta,
    diff_fingerprints,
    snapshot_workspace_fingerprints,
)


def test_diff_fingerprints_detects_added_removed_modified(tmp_path):
    a = Path(tmp_path) / "a.txt"
    b = Path(tmp_path) / "b.txt"
    # Content must change *byte length* as well as mtime: fingerprint is (size, mtime_ns)
    # only; on Windows/OneDrive two 1-byte writes can share the same coarse mtime.
    a.write_text("before", encoding="utf-8")
    b.write_text("x", encoding="utf-8")
    before = snapshot_workspace_fingerprints(Path(tmp_path))
    a.write_text("after-longer", encoding="utf-8")
    b.unlink()
    c = Path(tmp_path) / "c.txt"
    c.write_text("z", encoding="utf-8")
    after = snapshot_workspace_fingerprints(Path(tmp_path))
    d = diff_fingerprints(before, after)
    assert "a.txt" in d["modified"]
    assert "b.txt" in d["removed"]
    assert "c.txt" in d["added"]


def test_cap_delta_truncation_flag():
    big = {"added": [f"f{i}" for i in range(500)], "removed": [], "modified": []}
    capped = cap_delta(big, cap=50)
    assert capped["truncated"] is True
    assert len(capped["added"]) == 50
