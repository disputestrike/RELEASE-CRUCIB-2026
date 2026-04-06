"""
Truthful multi-axis scores — pipeline success ≠ production-ready ≠ spec compliance.
"""
from __future__ import annotations

from typing import Any, Dict, List


def compute_production_readiness(flat: List[Dict[str, Any]], bundle: Dict[str, List]) -> Dict[str, Any]:
    """
    Heuristic 0–100: evidence of tests, security checks, deploy ping, compile, routes, screenshot.
    Capped honestly — missing enterprise artifacts (RLS, idempotent webhooks) cannot be inferred from proof.
    """
    score = 0.0
    reasons: List[str] = []

    if any(i.get("proof_type") == "test" for i in flat):
        score += 18
        reasons.append("test_proof_present")
    else:
        reasons.append("no_test_proof_autorunner_template")

    ver_titles = " ".join((i.get("title") or "").lower() for i in bundle.get("verification", []) or [])
    titles_lower = [(i.get("title") or "").lower() for i in flat]
    if "security" in ver_titles or any("security" in t for t in titles_lower):
        score += 12
        reasons.append("security_step_evidence")
    else:
        reasons.append("no_named_security_proof")

    if any("tenancy" in t and "migration" in t for t in titles_lower):
        score += min(8, 100 - score)
        reasons.append("tenancy_sql_sketch_in_security_proof")
    if any("stripe" in t and "idempotency" in t for t in titles_lower):
        score += min(8, 100 - score)
        reasons.append("stripe_idempotency_sql_in_security_proof")

    if any((i.get("payload") or {}).get("check") == "rls_policies_in_migrations" for i in flat):
        score += min(8, 100 - score)
        reasons.append("rls_policies_detected_in_verification_proof")

    if any((i.get("payload") or {}).get("check") == "rls_syntax_valid" for i in flat):
        score += min(12, 100 - score)
        reasons.append("rls_policy_structure_valid_in_proof")

    if any((i.get("payload") or {}).get("check") == "tenancy_isolation_proven" for i in flat):
        score += min(14, 100 - score)
        reasons.append("tenancy_smoke_live_isolation")

    if any((i.get("payload") or {}).get("check") == "stripe_webhook_idempotency_proven" for i in flat):
        score += min(10, 100 - score)
        reasons.append("stripe_replay_idempotency_proven")

    if any((i.get("payload") or {}).get("check") in ("rbac_escalation_blocked", "rbac_anonymous_blocked") for i in flat):
        score += min(8, 100 - score)
        reasons.append("rbac_enforcement_smoke")

    if any((i.get("payload") or {}).get("check") == "tenant_context_guc_wired_in_backend_sketch" for i in flat):
        score += min(6, 100 - score)
        reasons.append("tenant_guc_deploy_gate_passed")

    if any((i.get("payload") or {}).get("check") == "observability_pack_present" for i in flat):
        score += min(4, 100 - score)
        reasons.append("observability_stub_pack_in_workspace")
    if any((i.get("payload") or {}).get("check") == "multiregion_terraform_sketch_present" for i in flat):
        score += min(4, 100 - score)
        reasons.append("multiregion_terraform_sketch_in_workspace")

    if any("api smoke" in t for t in titles_lower) or any(
        (i.get("payload") or {}).get("check") == "health_endpoint" for i in flat
    ):
        score += min(10, 100 - score)
        reasons.append("api_smoke_proof")

    if any((i.get("payload") or {}).get("kind") == "preview_screenshot" for i in flat):
        score += 20
        reasons.append("preview_screenshot")
    elif any("playwright" in (i.get("title") or "").lower() for i in flat):
        score += 15
        reasons.append("playwright_mentioned")

    if bundle.get("deploy") and any(
        (r.get("payload") or {}).get("url") for r in bundle["deploy"]
    ):
        score += 15
        reasons.append("deploy_url_in_proof")

    compile_n = len(bundle.get("verification", []) or [])  # rough
    compile_hits = sum(1 for i in flat if i.get("proof_type") == "compile")
    if compile_hits:
        score += min(15, 5 + compile_hits * 2)
        reasons.append("compile_checks")

    route_n = len(bundle.get("routes", []) or [])
    has_runtime_route = any(
        (i.get("payload") or {}).get("check") == "health_endpoint"
        or "api smoke" in (i.get("title") or "").lower()
        for i in flat
    )
    if route_n:
        if has_runtime_route:
            score += min(12, 4 + route_n)
            reasons.append("route_proof_with_runtime_hint")
        else:
            score += min(4, 2 + max(1, route_n // 2))
            reasons.append("route_proof_structure_only_demoted")

    if bundle.get("database"):
        score += 8
        reasons.append("database_artifacts")

    if any(
        (i.get("payload") or {}).get("compliance_sketch")
        or (i.get("payload") or {}).get("path") == "docs/COMPLIANCE_SKETCH.md"
        for i in flat
    ):
        score += min(6, 100 - score)
        reasons.append("compliance_sketch_file_in_proof")

    score = min(100.0, round(score, 1))
    return {
        "production_readiness_score": score,
        "production_readiness_cap_note": (
            "Capped heuristic only. Template RLS covers generated app_items; it does not certify "
            "your full data model, webhook idempotency, MFA, or infra."
        ),
        "production_readiness_factors": reasons,
    }


def build_honest_scorecard(
    *,
    pipeline_quality_score: float,
    trust_score: float,
    spec_compliance_percent: float,
    production_readiness: Dict[str, Any],
) -> Dict[str, Any]:
    """Single object for API/UI — no single '100% verified' claim."""
    pr = production_readiness.get("production_readiness_score", 0.0)
    return {
        "pipeline_quality_score": round(pipeline_quality_score, 1),
        "trust_evidence_score": round(trust_score, 1),
        "spec_compliance_percent": round(spec_compliance_percent, 1),
        "production_readiness_score": pr,
        "honest_summary": (
            f"Pipeline quality (proof density): ~{pipeline_quality_score:.0f}. "
            f"Trust-weighted evidence: ~{trust_score:.0f}. "
            f"Spec compliance vs stated goal: ~{spec_compliance_percent:.0f}%. "
            f"Production readiness (heuristic): ~{pr:.0f}. "
            "These are different axes; high pipeline score does not mean enterprise spec was met."
        ),
    }
