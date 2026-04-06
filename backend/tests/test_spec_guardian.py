"""Spec Guardian and truthful score helpers."""
import os
import pytest

from orchestration.spec_guardian import evaluate_goal_against_runner, merge_plan_risk_flags_into_report
from orchestration.truth_scores import compute_production_readiness, build_honest_scorecard


def test_default_mode_is_advisory_allows_nextjs_without_env(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_SPEC_GUARD_MODE", raising=False)
    r = evaluate_goal_against_runner("Ship the marketing site on Next.js 14")
    assert r["mode"] == "advisory"
    assert r["blocks_run"] is False
    assert any(v.get("code") == "stack_nextjs_requested" for v in r["violations"])


def test_advisory_mode_allows_nextjs_goal_but_lowers_compliance(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "advisory")
    r = evaluate_goal_against_runner("Build with Next.js 14 app router")
    assert r["blocks_run"] is False
    assert r["spec_compliance_percent"] < 100
    assert any("next" in (v.get("code") or "").lower() or "next" in v.get("message", "").lower() for v in r["violations"])


def test_strict_mode_blocks_nextjs_goal(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    r = evaluate_goal_against_runner("Production SaaS with Next.js and Vercel")
    assert r["blocks_run"] is True
    assert r["block_reasons"]


def test_merge_planner_flags():
    base = evaluate_goal_against_runner("simple todo app")
    merged = merge_plan_risk_flags_into_report(
        ["goal_spec_nextjs_autorunner_template_is_vite_react"],
        base,
    )
    assert len(merged["violations"]) >= 1


def test_strict_mode_next_track_skips_nextjs_blocker(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    r = evaluate_goal_against_runner(
        "Production SaaS with Next.js App Router",
        build_target="next_app_router",
    )
    assert r["blocks_run"] is False
    assert not any(v.get("code") == "stack_nextjs_requested" for v in r["violations"])


def test_merge_skips_nextjs_planner_flag_when_next_target(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    base = evaluate_goal_against_runner("simple todo app", build_target="next_app_router")
    merged = merge_plan_risk_flags_into_report(
        ["goal_spec_nextjs_autorunner_template_is_vite_react"],
        base,
        build_target="next_app_router",
    )
    assert not any(v.get("code") == "stack_nextjs_requested" for v in merged["violations"])
    assert merged["blocks_run"] is False


def test_truth_scorecard_shape():
    flat = [{"proof_type": "compile", "title": "ok", "payload": {"verification_class": "syntax"}}]
    bundle = {"verification": flat, "routes": [{"x": 1}], "database": [], "deploy": [], "files": [], "generic": []}
    pr = compute_production_readiness(flat, bundle)
    card = build_honest_scorecard(
        pipeline_quality_score=78,
        trust_score=80,
        spec_compliance_percent=55,
        production_readiness=pr,
    )
    assert "honest_summary" in card
    assert card["spec_compliance_percent"] == 55


def test_rls_multitenant_goal_is_advisory_not_strict_blocker(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    r = evaluate_goal_against_runner("Multi-tenant B2B SaaS with Postgres RLS on app data")
    assert not r["blocks_run"]
    codes = {v["code"] for v in r["violations"]}
    assert "tenancy_template_scope" in codes
    assert "tenancy_not_automated" not in codes


def test_schema_per_tenant_strict_blocker(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    r = evaluate_goal_against_runner("One database schema per tenant for isolation")
    assert r["blocks_run"]
    assert any(v.get("code") == "tenancy_schema_per_tenant" for v in r["violations"])


def test_orm_js_stack_strict_blocker(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SPEC_GUARD_MODE", "strict")
    r = evaluate_goal_against_runner("Use TypeORM with PostgreSQL for entities")
    assert r["blocks_run"]
    assert any(v.get("code") == "orm_js_requested" for v in r["violations"])


def test_rls_verification_proof_adds_readiness_factor():
    flat = [
        {
            "proof_type": "verification",
            "title": "Security: migration SQL includes PostgreSQL RLS",
            "payload": {"check": "rls_policies_in_migrations"},
        },
    ]
    bundle = {"verification": flat, "routes": [], "database": [], "deploy": [], "files": [], "generic": []}
    pr = compute_production_readiness(flat, bundle)
    assert "rls_policies_detected_in_verification_proof" in pr["production_readiness_factors"]


def test_compliance_sketch_proof_adds_readiness_factor():
    flat = [
        {
            "proof_type": "file",
            "title": "File exists: docs/COMPLIANCE_SKETCH.md",
            "payload": {"path": "docs/COMPLIANCE_SKETCH.md", "compliance_sketch": True},
        },
    ]
    bundle = {"verification": [], "routes": [], "database": [], "deploy": [], "files": flat, "generic": []}
    pr = compute_production_readiness(flat, bundle)
    assert "compliance_sketch_file_in_proof" in pr["production_readiness_factors"]
