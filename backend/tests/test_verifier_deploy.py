"""Deploy step verification: file proofs for deploy.build artifacts."""

import os
import tempfile

import pytest

from orchestration.verifier import verify_deploy_step


@pytest.mark.asyncio
async def test_deploy_build_emits_file_proof_for_compliance_sketch():
    with tempfile.TemporaryDirectory() as d:
        rel = "docs/COMPLIANCE_SKETCH.md"
        full = os.path.join(d, "docs", "COMPLIANCE_SKETCH.md")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write("# Compliance sketch\nEducational only.\n")
        step = {
            "step_key": "deploy.build",
            "output_files": [rel, "Dockerfile"],
            "deploy_url": None,
        }
        r = await verify_deploy_step(step, d)
        assert not r["passed"]
        assert any("Dockerfile" in i for i in r["issues"])
        file_proofs = [p for p in r["proof"] if p["proof_type"] == "file"]
        assert any(p.get("payload", {}).get("compliance_sketch") for p in file_proofs)
        assert any("COMPLIANCE_SKETCH" in p["title"] for p in file_proofs)


@pytest.mark.asyncio
async def test_deploy_build_all_outputs_present():
    with tempfile.TemporaryDirectory() as d:
        files = [
            "Dockerfile",
            "deploy/PRODUCTION_SKETCH.md",
            "docs/COMPLIANCE_SKETCH.md",
        ]
        for rel in files:
            full = os.path.normpath(os.path.join(d, rel.replace("/", os.sep)))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write("# stub\n")
        step = {
            "step_key": "deploy.build",
            "output_files": files,
            "deploy_url": None,
        }
        r = await verify_deploy_step(step, d)
        assert r["passed"]
        assert len([p for p in r["proof"] if p["proof_type"] == "file"]) == 3
