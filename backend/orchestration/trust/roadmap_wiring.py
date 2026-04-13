"""
Honest status of roadmap items vs code shipped. Used by GET /api/trust/platform-capabilities.
'wired' = implemented and tested in this repo.
'partial' = implemented but not at full spec depth.
'planned' = not implemented; north-star only.
"""

from __future__ import annotations

from typing import Any, Dict, List


def roadmap_wiring_status() -> List[Dict[str, Any]]:
    return [
        {
            "id": "github_actions_verify_full",
            "phase": 5,
            "status": "wired",
            "detail": ".github/workflows/ci-verify-full.yml — pytest + uvicorn /api/health + deploy/healthcheck.sh + frontend lint/test:ci",
        },
        {
            "id": "observability_workspace_pack",
            "phase": 4,
            "status": "wired",
            "detail": "deploy/observability stubs + docs/OBSERVABILITY_PACK.md on deploy.build when goal matches",
        },
        {
            "id": "multiregion_terraform_sketch",
            "phase": 5,
            "status": "wired",
            "detail": "terraform/modules/{aws,gcp,azure}_region_stub + multiregion_sketch when goal matches",
        },
        {
            "id": "spec_guardian_engine",
            "phase": 1,
            "status": "wired",
            "detail": "spec_guardian.py + plan spec_guard + run-auto event; strict mode blocks run",
        },
        {
            "id": "truthful_multiaxis_scores",
            "phase": 2,
            "status": "wired",
            "detail": "proof scorecard: pipeline vs trust vs spec_compliance vs production_readiness",
        },
        {
            "id": "architecture_outline_on_plan",
            "phase": 2,
            "status": "wired",
            "detail": "planner architecture_outline (honest template intent)",
        },
        {
            "id": "domain_pack_multitenant_sql_api",
            "phase": 3,
            "status": "partial",
            "detail": "goal-driven 002_multitenancy_rls.sql (live RLS on app_items) + X-Tenant-Slug API + Tenant models; CI tests RLS",
        },
        {
            "id": "domain_pack_stripe_idempotency_sql",
            "phase": 3,
            "status": "partial",
            "detail": "003_stripe_idempotency_sketch.sql + stripe_routes webhook sketch",
        },
        {
            "id": "domain_pack_compliance_sketch_md",
            "phase": 3,
            "status": "wired",
            "detail": "regulated goal → docs/COMPLIANCE_SKETCH.md + file proof + UI callout; truth_scores factor",
        },
        {
            "id": "production_gate_secret_scan",
            "phase": 5,
            "status": "wired",
            "detail": "deploy.build scans workspace; CRUCIBAI_PRODUCTION_GATE_STRICT=1 fails on patterns",
        },
        {
            "id": "verification_security_workspace",
            "phase": 4,
            "status": "wired",
            "detail": "verification.security runs migration + main.py + package checks",
        },
        {
            "id": "stripe_router_mounted_in_main",
            "phase": 4,
            "status": "wired",
            "detail": "backend.stripe patches main.py with include_router(stripe_routes.router)",
        },
        {
            "id": "verification_api_smoke_static_live",
            "phase": 4,
            "status": "partial",
            "detail": "api_smoke: route scan + py_compile; optional CRUCIBAI_API_SMOKE_URL live GET",
        },
        {
            "id": "deploy_healthcheck_script",
            "phase": 5,
            "status": "wired",
            "detail": "deploy/healthcheck.sh curls /health",
        },
        {
            "id": "preflight_structured",
            "phase": 1,
            "status": "wired",
            "detail": "preflight_report.py + job_events preflight_report",
        },
        {
            "id": "preflight_hard_gate_prod",
            "phase": 1,
            "status": "partial",
            "detail": "Strict when CRUCIBAI_DEV off; dev skips extended gate",
        },
        {
            "id": "node_runtime_manifest",
            "phase": 1,
            "status": "wired",
            "detail": "node_manifest on each plan step",
        },
        {
            "id": "preview_npm_build_playwright",
            "phase": 1,
            "status": "wired",
            "detail": "browser_preview_verify + preview_gate",
        },
        {
            "id": "preview_screenshot_proof",
            "phase": 1,
            "status": "wired",
            "detail": ".crucibai/preview/screenshot.png + proof row",
        },
        {
            "id": "verification_taxonomy",
            "phase": 2,
            "status": "partial",
            "detail": "verification_class on proof; not all rows tagged yet",
        },
        {
            "id": "weighted_scoring_10_20_40_30",
            "phase": 2,
            "status": "wired",
            "detail": "trust_scoring.compute_trust_metrics in get_proof",
        },
        {
            "id": "route_contract_db",
            "phase": 2,
            "status": "partial",
            "detail": "FastAPI route scan in verifier (regex/ast light)",
        },
        {
            "id": "db_migration_verify",
            "phase": 2,
            "status": "partial",
            "detail": "Existing db proof; no live PG query in runner",
        },
        {
            "id": "auth_verification_suite",
            "phase": 2,
            "status": "partial",
            "detail": "Stub vs client-auth evidence row",
        },
        {
            "id": "quality_tier_env",
            "phase": 3,
            "status": "wired",
            "detail": "CRUCIB_QUALITY_TIER on plan",
        },
        {
            "id": "fixer_patch_diffs",
            "phase": 4,
            "status": "planned",
            "detail": "classify_failure exists; no mandatory unified diff artifact",
        },
        {
            "id": "deploy_url_health",
            "phase": 5,
            "status": "partial",
            "detail": "deploy smoke when URL set",
        },
        {
            "id": "rollback_one_click",
            "phase": 5,
            "status": "planned",
            "detail": "Not implemented",
        },
        {
            "id": "dag_graph_ui",
            "phase": 6,
            "status": "planned",
            "detail": "Frontend graph not built",
        },
        {
            "id": "node_artifacts_jsonl",
            "phase": 6,
            "status": "wired",
            "detail": ".crucibai/node_artifacts.jsonl per step",
        },
        {
            "id": "benchmark_suite_25_50",
            "phase": 9,
            "status": "partial",
            "detail": "scripts/run_trust_benchmark_smoke.py starter",
        },
        {
            "id": "trust_composite_score",
            "phase": 10,
            "status": "wired",
            "detail": "trust_score in proof API",
        },
    ]
