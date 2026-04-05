"""
Proof that trust platform pieces are wired: manifests, scoring, preflight fixes, API surface.
"""
import os
import pytest

from orchestration.trust.node_manifest import enrich_plan_with_node_manifests, manifest_for_step_key
from orchestration.trust.roadmap_wiring import roadmap_wiring_status
from orchestration.trust.trust_scoring import compute_trust_metrics


def test_manifest_for_step_key_has_verification_classes():
    m = manifest_for_step_key("verification.preview")
    assert "verification_classes" in m
    assert "experience" in m["verification_classes"]


def test_enrich_plan_attaches_node_manifest_per_step():
    plan = {
        "goal": "t",
        "phases": [{"steps": [{"key": "frontend.scaffold", "name": "x"}]}],
    }
    out = enrich_plan_with_node_manifests(plan)
    step = out["phases"][0]["steps"][0]
    assert "node_manifest" in step
    assert step["node_manifest"]["runtime"] == "python"


def test_roadmap_wiring_status_covers_core_items():
    items = roadmap_wiring_status()
    ids = {i["id"] for i in items}
    assert "preflight_structured" in ids
    assert "spec_guardian_engine" in ids
    assert "truthful_multiaxis_scores" in ids
    assert "node_runtime_manifest" in ids
    assert "weighted_scoring_10_20_40_30" in ids
    assert "domain_pack_compliance_sketch_md" in ids
    assert "github_actions_verify_full" in ids
    assert "observability_workspace_pack" in ids
    assert "multiregion_terraform_sketch" in ids
    assert all(i.get("status") in ("wired", "partial", "planned") for i in items)


def test_compute_trust_metrics_weights():
    items = [
        {"payload": {"verification_class": "presence"}, "proof_type": "file", "title": "a"},
        {"payload": {"verification_class": "syntax"}, "proof_type": "compile", "title": "b"},
        {"payload": {"verification_class": "runtime"}, "proof_type": "api", "title": "c"},
        {
            "payload": {"verification_class": "experience", "kind": "preview_screenshot"},
            "proof_type": "verification",
            "title": "shot",
        },
    ]
    m = compute_trust_metrics(items, has_screenshot_proof=True, has_live_deploy_url=False)
    assert m["trust_score"] >= 0
    assert "class_weighted_score" in m
    assert m["truth_status"]["preview_visual_evidence"] is True


@pytest.mark.asyncio
async def test_preflight_checks_include_recommended_fix():
    from orchestration.preflight_report import build_preflight_report

    r = await build_preflight_report()
    assert r.get("schema") == "crucibai.preflight/v1"
    for c in r.get("checks") or []:
        assert "recommended_fix" in c


def test_scan_routes_finds_fastapi_style():
    from orchestration.verifier import _scan_workspace_for_route_declarations
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "backend"), exist_ok=True)
        with open(os.path.join(td, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write('@app.get("/health")\nasync def h():\n    return {}\n')
        found = _scan_workspace_for_route_declarations(td)
        assert any(x["path"] == "/health" and x["method"] == "GET" for x in found)
