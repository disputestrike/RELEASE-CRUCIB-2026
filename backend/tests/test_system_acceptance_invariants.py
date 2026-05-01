"""
Automated slice of SYSTEM ACCEPTANCE + PROOF PASS (contract invariants).

Manual checklist still required (not runnable in CI alone):
  1. Before/after screenshots for e-commerce acceptance run.
  2. Full live build: canonical job row, refresh hydration, files explorer,
     preview_source in UI, repair dedupe vs live SSE, no chat timestamps,
     provider fallback with agents, end-state proof JSON export.

These tests lock scoring / delivery truth so regressions fail fast in CI.
"""

from __future__ import annotations

from backend.proof.build_contract import build_contract


def _minimal_bundle():
    return {
        "files": [{"proof_type": "file", "title": "package.json", "payload": {}}],
        "verification": [{"proof_type": "compile", "title": "build ok", "payload": {}}],
        "routes": [],
        "database": [],
        "deploy": [],
        "generic": [],
    }


def test_diagnostic_preview_blocks_deploy_and_success():
    """Fallback/shell preview must not count as shippable (item 7/10)."""
    c = build_contract(
        job={"id": "j1", "status": "completed", "goal": "Build a store", "project_id": "p1"},
        steps=[{"status": "completed"}],
        bundle=_minimal_bundle(),
        bundle_sha256="deadbeef",
        quality_score=90.0,
        trust_score=80.0,
        production_readiness_score=85.0,
        verification_failed_count=0,
        build_verified=True,
        truth_surface={
            "preview_source": "diagnostic_fallback",
            "prompt_contract_passed": True,
            "preview_verified": True,
            "browser_verified": True,
            "generated_app_type": "unknown",
        },
    )
    assert "preview_not_generated_artifact" in c["blockers"]
    assert c["deploy_ready"] is False
    assert c["export_ready"] is False
    assert c["success"] is False


def test_prompt_contract_failed_blocks_delivery():
    """E-commerce contract failure must block delivery/success (items 9–10)."""
    c = build_contract(
        job={"id": "j2", "status": "completed", "goal": "ecommerce", "project_id": "p2"},
        steps=[{"status": "completed"}],
        bundle=_minimal_bundle(),
        bundle_sha256="deadbeef",
        quality_score=90.0,
        trust_score=80.0,
        production_readiness_score=85.0,
        verification_failed_count=0,
        build_verified=True,
        truth_surface={
            "preview_source": "generated_artifact",
            "prompt_contract_passed": False,
            "preview_verified": True,
            "browser_verified": True,
            "generated_app_type": "ecommerce_store",
        },
    )
    assert "prompt_contract_failed" in c["blockers"]
    assert c["delivery_ready"] is False
    assert c["success"] is False


def test_build_not_verified_never_success():
    c = build_contract(
        job={"id": "j3", "status": "completed", "goal": "g", "project_id": "p3"},
        steps=[{"status": "completed"}],
        bundle=_minimal_bundle(),
        bundle_sha256="x",
        quality_score=40.0,
        trust_score=50.0,
        production_readiness_score=85.0,
        verification_failed_count=0,
        build_verified=False,
        truth_surface={
            "preview_source": "generated_artifact",
            "prompt_contract_passed": True,
            "preview_verified": True,
            "browser_verified": True,
        },
    )
    assert "build_not_verified" in c["blockers"]
    assert c["success"] is False
    assert c["deploy_ready"] is False
