"""Unit tests for verification behavior bundle merge + explicit verify_step."""

import os
import tempfile

import pytest
from orchestration.verification_behavior_bundle import merge_verification_results


def test_merge_verification_all_pass_uses_min_score():
    a = {
        "passed": True,
        "score": 100,
        "issues": [],
        "proof": [{"proof_type": "a", "title": "A", "payload": {}}],
    }
    b = {
        "passed": True,
        "score": 88,
        "issues": [],
        "proof": [{"proof_type": "b", "title": "B", "payload": {}}],
    }
    m = merge_verification_results([a, b])
    assert m["passed"] is True
    assert m["score"] == 88
    assert len(m["proof"]) == 2


def test_merge_verification_one_fail_collects_issues():
    a = {"passed": True, "score": 100, "issues": [], "proof": []}
    b = {"passed": False, "score": 30, "issues": ["stripe replay failed"], "proof": []}
    m = merge_verification_results([a, b])
    assert m["passed"] is False
    assert "stripe replay failed" in m["issues"]


@pytest.mark.asyncio
async def test_verify_step_behavior_key_matches_security_bundle_subset():
    from orchestration.verifier import verify_step

    with tempfile.TemporaryDirectory() as d:
        mig = os.path.join(d, "db", "migrations")
        os.makedirs(mig)
        with open(os.path.join(mig, "x.sql"), "w", encoding="utf-8") as f:
            f.write("-- no stripe table\n")
        os.makedirs(os.path.join(d, "backend"))
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")
        out = await verify_step({"step_key": "verification.behavior"}, workspace_path=d)
        assert out["passed"] is True
        checks = {(p.get("payload") or {}).get("check") for p in out["proof"]}
        assert "rbac_smoke_skipped" in checks
