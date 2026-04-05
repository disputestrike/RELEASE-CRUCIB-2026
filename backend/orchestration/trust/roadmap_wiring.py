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
        {"id": "preflight_structured", "phase": 1, "status": "wired", "detail": "preflight_report.py + job_events preflight_report"},
        {"id": "preflight_hard_gate_prod", "phase": 1, "status": "partial", "detail": "Strict when CRUCIBAI_DEV off; dev skips extended gate"},
        {"id": "node_runtime_manifest", "phase": 1, "status": "wired", "detail": "node_manifest on each plan step"},
        {"id": "preview_npm_build_playwright", "phase": 1, "status": "wired", "detail": "browser_preview_verify + preview_gate"},
        {"id": "preview_screenshot_proof", "phase": 1, "status": "wired", "detail": ".crucibai/preview/screenshot.png + proof row"},
        {"id": "verification_taxonomy", "phase": 2, "status": "partial", "detail": "verification_class on proof; not all rows tagged yet"},
        {"id": "weighted_scoring_10_20_40_30", "phase": 2, "status": "wired", "detail": "trust_scoring.compute_trust_metrics in get_proof"},
        {"id": "route_contract_db", "phase": 2, "status": "partial", "detail": "FastAPI route scan in verifier (regex/ast light)"},
        {"id": "db_migration_verify", "phase": 2, "status": "partial", "detail": "Existing db proof; no live PG query in runner"},
        {"id": "auth_verification_suite", "phase": 2, "status": "partial", "detail": "Stub vs client-auth evidence row"},
        {"id": "quality_tier_env", "phase": 3, "status": "wired", "detail": "CRUCIB_QUALITY_TIER on plan"},
        {"id": "fixer_patch_diffs", "phase": 4, "status": "planned", "detail": "classify_failure exists; no mandatory unified diff artifact"},
        {"id": "deploy_url_health", "phase": 5, "status": "partial", "detail": "deploy smoke when URL set"},
        {"id": "rollback_one_click", "phase": 5, "status": "planned", "detail": "Not implemented"},
        {"id": "dag_graph_ui", "phase": 6, "status": "planned", "detail": "Frontend graph not built"},
        {"id": "node_artifacts_jsonl", "phase": 6, "status": "wired", "detail": ".crucibai/node_artifacts.jsonl per step"},
        {"id": "benchmark_suite_25_50", "phase": 9, "status": "partial", "detail": "scripts/run_trust_benchmark_smoke.py starter"},
        {"id": "trust_composite_score", "phase": 10, "status": "wired", "detail": "trust_score in proof API"},
    ]
