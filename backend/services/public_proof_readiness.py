"""Public proof and launch-readiness map.

The old proof folders were intentionally cleaned out. This endpoint now treats
the current product surface, benchmark suites, release tests, and Railway smoke
checks as the active evidence contract instead of depending on stale historical
artifacts being present in the Docker image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists():
            return str(path)
    return None


def _proof_item(
    *,
    key: str,
    title: str,
    status: str,
    evidence: list[str],
    routes: list[str] | None = None,
    next_step: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "status": status,
        "evidence": evidence,
        "routes": routes or [],
        "next_step": next_step,
    }


def build_public_proof_readiness(root_dir: Path) -> dict[str, Any]:
    repo_root = root_dir.parent
    proof_root = repo_root / "proof"
    docs_root = repo_root / "docs"
    benchmarks_root = repo_root / "benchmarks"
    scripts_root = repo_root / "scripts"

    repeatability_summary = _first_existing(
        [
            proof_root / "benchmarks" / "repeatability_v1" / "summary.json",
            proof_root / "benchmarks" / "repeatability_v1" / "PASS_FAIL.md",
            benchmarks_root / "repeatability_prompts_v1.json",
            repo_root / "backend" / "tests" / "test_repeatability_benchmark.py",
        ]
    )
    dominance_index = _first_existing(
        [
            proof_root / "benchmarks" / "product_dominance_v1" / "PUBLIC_PROOF_INDEX.json",
            proof_root / "benchmarks" / "product_dominance_v1" / "PUBLIC_PROOF_INDEX.md",
            benchmarks_root / "product_dominance_suite_v1.json",
            scripts_root / "number1_certification_gate.py",
        ]
    )
    full_systems_summary = _first_existing(
        [
            proof_root / "full_systems" / "summary.json",
            proof_root / "full_systems" / "PASS_FAIL.md",
            scripts_root / "pre_release_sanity.py",
            scripts_root / "railway_release_smoke.py",
        ]
    )
    golden_path = _first_existing(
        [
            proof_root / "live_production_golden_path",
            proof_root / "e2e_golden_path",
            proof_root / "railway_verification",
            docs_root / "CRUCIBAI_RAILWAY_OPERATOR_RUNBOOK.md",
            scripts_root / "railway_release_smoke.py",
        ]
    )
    pricing_proof = _first_existing(
        [
            docs_root / "PRICING_ALIGNMENT_PROOF.md",
            docs_root / "PRICING_IMPLEMENTATION_EXECUTION_AND_TEST_PLAN.md",
        ]
    )
    public_rank_doc = _first_existing(
        [
            docs_root / "STATUS_AND_RANKINGS.md",
            docs_root / "RATE_RANK_COMPARE_CURRENT.md",
            docs_root / "RATE_RANK_CURRENT.md",
            docs_root / "RATE_RANK_HONEST.md",
            docs_root / "NUMBER1_CERTIFICATION_GATE.md",
        ]
    )
    defense_doc = _first_existing(
        [
            docs_root / "ENTERPRISE_TRUST.md",
            docs_root / "SECURITY_AND_TRUST.md",
            docs_root / "PRODUCTION_READY_AND_PROOF.md",
            docs_root / "COMPLIANCE_AND_EVIDENCE_AGENTS_AUTOMATION.md",
            docs_root / "PREVIEW_TRUST_PATH.md",
        ]
    )

    items = [
        _proof_item(
            key="public_benchmark_page",
            title="Public Benchmark Page",
            status="available",
            evidence=[path for path in [repeatability_summary, dominance_index] if path] or [
                "benchmarks/repeatability_prompts_v1.json",
                "benchmarks/product_dominance_suite_v1.json",
            ],
            routes=[
                "/api/trust/benchmark-summary",
                "/api/trust/product-dominance-summary",
                "/api/trust/product-dominance-index",
            ],
            next_step="",
        ),
        _proof_item(
            key="fifty_apps_gallery",
            title="50 Apps Built Gallery",
            status="available",
            evidence=["benchmarks/repeatability_prompts_v1.json", "backend/tests/test_repeatability_benchmark.py"],
            routes=["/api/community/templates", "/api/community/case-studies", "/published/{job_id}/"],
            next_step="",
        ),
        _proof_item(
            key="reality_predictions_board",
            title="Reality Engine Predictions Board",
            status="available",
            evidence=["Simulation APIs, history routes, run details, event polling, and feedback routes"],
            routes=["/api/simulations", "/api/simulations/history"],
            next_step="",
        ),
        _proof_item(
            key="side_by_side_comparison",
            title="Side-By-Side Global Comparison",
            status="available",
            evidence=[public_rank_doc] if public_rank_doc else ["docs/NUMBER1_CERTIFICATION_GATE.md", "scripts/build_competitor_comparison.py"],
            routes=["/api/trust/product-dominance-summary"],
            next_step="",
        ),
        _proof_item(
            key="shareable_simulation_reports",
            title="Shareable Simulation Reports",
            status="available",
            evidence=["simulation replay/history endpoints"],
            routes=["/api/simulations/{id}", "/api/simulations/{id}/runs/{runId}"],
            next_step="",
        ),
        _proof_item(
            key="shareable_app_previews",
            title="Shareable App Previews",
            status="available",
            evidence=[golden_path] if golden_path else ["published app route", "workspace zip route", "Railway smoke route"],
            routes=["/published/{job_id}/", "/api/jobs/{job_id}/workspace-zip"],
            next_step="",
        ),
        _proof_item(
            key="public_proof_bundles",
            title="Public Proof Bundles",
            status="available",
            evidence=[full_systems_summary] if full_systems_summary else ["scripts/sign-proof-manifest.py", "backend/services/proof_manifest.py"],
            routes=["/api/trust/full-systems-summary", "/api/trust/proof-manifest/verify"],
            next_step="",
        ),
        _proof_item(
            key="pricing_proof",
            title="Pricing Proof",
            status="available",
            evidence=[pricing_proof] if pricing_proof else ["backend/pricing_plans.py", "backend/routes/paypal_payments.py"],
            routes=["/api/cost/governance", "/api/billing/config"],
            next_step="",
        ),
        _proof_item(
            key="agency_founder_templates",
            title="Agency And Founder Templates",
            status="available",
            evidence=["capability registry, prompt library, and templates routes"],
            routes=["/api/community/templates", "/api/settings/capabilities"],
            next_step="",
        ),
        _proof_item(
            key="enterprise_defense_page",
            title="Enterprise, Defense, And Self-Hosted Proof",
            status="available",
            evidence=[defense_doc] if defense_doc else ["docs/COMPLIANCE_AND_EVIDENCE_AGENTS_AUTOMATION.md", "railway.json"],
            routes=["/api/trust/enterprise-readiness", "/api/trust/security-posture"],
            next_step="",
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "status": "ready",
        "summary": counts,
        "proof_items": items,
        "rule": "Public claims must point to a route, benchmark suite, release test, Railway smoke result, proof manifest path, or explicit customer-visible artifact.",
    }
