"""Tests for path extraction from verification issue strings."""

import os
import tempfile

from orchestration.verifier_issue_files import candidate_files_from_verification_issues


def test_esbuild_path_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        rel = "src/Broken.jsx"
        os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
        open(os.path.join(tmp, rel), "w", encoding="utf-8").write("export default 1\n")
        issues = ["esbuild failed src/Broken.jsx: unexpected token"]
        out = candidate_files_from_verification_issues(issues, tmp)
        assert rel.replace("\\", "/") in out or "src/Broken.jsx" in out


def test_empty_workspace():
    assert candidate_files_from_verification_issues(["esbuild failed x.jsx: err"], "") == []
