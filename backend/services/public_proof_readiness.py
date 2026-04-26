"""Public proof and virality readiness map.

This is the Phase 8 contract: every public claim needs a demo, benchmark, proof
artifact, shareable report, or explicit gap. The endpoint backed by this module
is intentionally conservative so marketing can only amplify what the product
can prove.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _exists(path: Path) -> bool:
    return path.exists()


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

    repeatability_summary = _first_existing(
        [
            proof_root / "benchmarks" / "repeatability_v1" / "summary.json",
            proof_root / "benchmarks" / "repeatability_v1" / "PASS_FAIL.md",
        ]
    )
    dominance_index = _first_existing(
        [
            proof_root / "benchmarks" / "product_dominance_v1" / "PUBLIC_PROOF_INDEX.json",
            proof_root / "benchmarks" / "product_dominance_v1" / "PUBLIC_PROOF_INDEX.md",
        ]
    )
    full_systems_summary = _first_existing(
        [
            proof_root / "full_systems" / "summary.json",
            proof_root / "full_systems" / "PASS_FAIL.md",
        ]
    )
    golden_path = _first_existing(
        [
            proof_root / "live_production_golden_path",
            proof_root / "e2e_golden_path",
            proof_root / "railway_verification",
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
        ]
    )
    defense_doc = _first_existing(
        [
            docs_root / "ENTERPRISE_TRUST.md",
            docs_root / "SECURITY_AND_TRUST.md",
            docs_root / "PRODUCTION_READY_AND_PROOF.md",
        ]
    )

    proof_dirs = {p.name for p in proof_root.iterdir() if p.is_dir()} if proof_root.exists() else set()
    items = [
        _proof_item(
            key="public_benchmark_page",
            title="Public Benchmark Page",
            status="available" if repeatability_summary or dominance_index else "foundation",
            evidence=[path for path in [repeatability_summary, dominance_index] if path],
            routes=[
                "/api/trust/benchmark-summary",
                "/api/trust/product-dominance-summary",
                "/api/trust/product-dominance-index",
            ],
            next_step="Publish a routed frontend page that renders the benchmark API if not already linked.",
        ),
        _proof_item(
            key="fifty_apps_gallery",
            title="50 Apps Built Gallery",
            status="foundation" if "full_system_generation_contract" in proof_dirs else "missing",
            evidence=["proof/full_system_generation_contract"] if "full_system_generation_contract" in proof_dirs else [],
            next_step="Convert generated-app proof runs into a public gallery with preview links and proof bundles.",
        ),
        _proof_item(
            key="reality_predictions_board",
            title="Reality Engine Predictions Board",
            status="foundation" if (docs_root / "SIMULATION_STANDARD_FEASIBILITY_AUDIT.md").exists() else "missing",
            evidence=["Simulation APIs and replay events"] if (docs_root / "SIMULATION_STANDARD_FEASIBILITY_AUDIT.md").exists() else [],
            routes=["/api/simulations", "/api/simulations/history"],
            next_step="Publish selected simulation verdicts with citations, trust score, and follow-up outcome status.",
        ),
        _proof_item(
            key="side_by_side_comparison",
            title="Side-By-Side Global Comparison",
            status="available" if public_rank_doc else "foundation",
            evidence=[public_rank_doc] if public_rank_doc else [],
            routes=["/api/trust/product-dominance-summary"],
            next_step="Keep comparison claims tied to timestamped proof artifacts, not static marketing copy.",
        ),
        _proof_item(
            key="shareable_simulation_reports",
            title="Shareable Simulation Reports",
            status="foundation",
            evidence=["simulation replay/history endpoints"],
            routes=["/api/simulations/{id}", "/api/simulations/{id}/runs/{runId}"],
            next_step="Add signed public share links for selected runs and redact private sources by default.",
        ),
        _proof_item(
            key="shareable_app_previews",
            title="Shareable App Previews",
            status="available" if golden_path else "foundation",
            evidence=[golden_path] if golden_path else [],
            routes=["/published/{job_id}/", "/api/jobs/{job_id}/workspace-zip"],
            next_step="Ensure every public preview has a proof bundle and rebuild date.",
        ),
        _proof_item(
            key="public_proof_bundles",
            title="Public Proof Bundles",
            status="available" if full_systems_summary else "foundation",
            evidence=[full_systems_summary] if full_systems_summary else [],
            routes=["/api/trust/full-systems-summary", "/api/trust/proof-manifest/verify"],
            next_step="Sign canonical bundles with CRUCIB_PROOF_HMAC_SECRET in production.",
        ),
        _proof_item(
            key="pricing_proof",
            title="Pricing Proof",
            status="available" if pricing_proof else "foundation",
            evidence=[pricing_proof] if pricing_proof else [],
            routes=["/api/cost/governance", "/api/payments/braintree/status"],
            next_step="Publish Braintree configured status only after production credentials are present.",
        ),
        _proof_item(
            key="agency_founder_templates",
            title="Agency And Founder Templates",
            status="foundation",
            evidence=["capability registry, prompt library, and templates routes"],
            routes=["/api/community/templates", "/api/settings/capabilities"],
            next_step="Create curated public template packs with proof-backed expected outputs.",
        ),
        _proof_item(
            key="enterprise_defense_page",
            title="Enterprise, Defense, And Self-Hosted Proof",
            status="available" if defense_doc else "foundation",
            evidence=[defense_doc] if defense_doc else [],
            routes=["/api/trust/enterprise-readiness", "/api/trust/security-posture"],
            next_step="Publish self-host/VPC guide and governance checklist before making defense-grade claims.",
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "status": "ready" if counts.get("missing", 0) == 0 and counts.get("foundation", 0) == 0 else "partial",
        "summary": counts,
        "proof_items": items,
        "rule": "No public claim graduates to available unless it has a route, demo, benchmark, proof artifact, or signed bundle.",
    }
