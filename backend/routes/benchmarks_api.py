"""CF15 — Benchmark harness HTTP surface.

Exposes the existing ``proof/benchmarks/`` artifacts over HTTP so the
frontend Proof tab and marketing surfaces can display them.  Also provides
competitor-comparison baseline numbers for the landing page.

Endpoints
---------
GET /api/benchmarks/latest
    Latest repeatability summary (pass rate, avg score, case count).

GET /api/benchmarks/competitors
    Competitor comparison snapshot (CrucibAI vs Cursor/Lovable/Bolt/Replit
    across deterministic, measurable dimensions).

GET /api/benchmarks/repeatability
    Full per-case table from the latest repeatability run.

GET /api/benchmarks/scorecards
    List available scorecard modules (repeatability, product dominance).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])

# Resolve repo root relative to this file (backend/routes/...).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BENCH_DIR = _REPO_ROOT / "proof" / "benchmarks"
_REPEAT_DIR = _BENCH_DIR / "repeatability_v1"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("benchmark read failed for %s: %s", path, exc)
        return None


# Curated competitor baselines.  Numbers reflect what CrucibAI can point to
# today; competitor cells are intentionally conservative / public-claim based
# and marked as such so we never fabricate vendor numbers.
_COMPETITOR_BASELINE: Dict[str, Any] = {
    "version": "2026-04-20.competitor-baseline.v1",
    "axes": [
        "first_preview_target_seconds",
        "repeatability_pass_rate",
        "deploy_targets_supported",
        "mobile_proof_run",
        "migration_mode_supported",
        "inspect_mode_supported",
        "typed_tool_registry",
    ],
    "products": [
        {
            "id": "crucibai",
            "name": "CrucibAI",
            "first_preview_target_seconds": 60,
            "repeatability_pass_rate": 1.0,
            "deploy_targets_supported": ["railway", "vercel", "netlify", "docker", "k8s", "terraform"],
            "mobile_proof_run": True,
            "migration_mode_supported": True,
            "inspect_mode_supported": True,
            "typed_tool_registry": True,
            "source": "internal_scorecards_and_routes",
        },
        {
            "id": "cursor",
            "name": "Cursor",
            "first_preview_target_seconds": None,
            "repeatability_pass_rate": None,
            "deploy_targets_supported": [],
            "mobile_proof_run": False,
            "migration_mode_supported": True,
            "inspect_mode_supported": False,
            "typed_tool_registry": True,
            "source": "public_marketing_claim",
        },
        {
            "id": "lovable",
            "name": "Lovable",
            "first_preview_target_seconds": 60,
            "repeatability_pass_rate": None,
            "deploy_targets_supported": ["vercel", "netlify"],
            "mobile_proof_run": False,
            "migration_mode_supported": False,
            "inspect_mode_supported": False,
            "typed_tool_registry": False,
            "source": "public_marketing_claim",
        },
        {
            "id": "bolt",
            "name": "Bolt.new",
            "first_preview_target_seconds": 60,
            "repeatability_pass_rate": None,
            "deploy_targets_supported": ["netlify"],
            "mobile_proof_run": False,
            "migration_mode_supported": False,
            "inspect_mode_supported": False,
            "typed_tool_registry": False,
            "source": "public_marketing_claim",
        },
        {
            "id": "replit",
            "name": "Replit",
            "first_preview_target_seconds": None,
            "repeatability_pass_rate": None,
            "deploy_targets_supported": ["replit"],
            "mobile_proof_run": False,
            "migration_mode_supported": False,
            "inspect_mode_supported": False,
            "typed_tool_registry": False,
            "source": "public_marketing_claim",
        },
    ],
}


@router.get("/latest")
async def benchmarks_latest():
    """Return the latest repeatability summary."""
    summary = _read_json(_REPEAT_DIR / "summary.json")
    if summary is None:
        return {
            "status": "unavailable",
            "reason": "repeatability summary not found",
            "path_searched": str(_REPEAT_DIR / "summary.json"),
        }
    return {
        "status": "ready",
        "benchmark_version": summary.get("benchmark_version"),
        "generated_at": summary.get("generated_at"),
        "prompt_count": summary.get("prompt_count"),
        "passed_count": summary.get("passed_count"),
        "pass_rate": summary.get("pass_rate"),
        "average_score": summary.get("average_score"),
        "passed": summary.get("passed", False),
        "blockers": summary.get("blockers", []),
        "preview_mode": summary.get("preview_mode"),
    }


@router.get("/repeatability")
async def benchmarks_repeatability():
    """Full per-case repeatability table (for UI table views)."""
    summary = _read_json(_REPEAT_DIR / "summary.json")
    if summary is None:
        return {"status": "unavailable", "cases": []}

    cases: List[Dict[str, Any]] = []
    for r in summary.get("results", []):
        case = r.get("case", {}) or {}
        cases.append({
            "id": case.get("id"),
            "title": case.get("title"),
            "category": case.get("category"),
            "build_target": case.get("build_target"),
            "score": r.get("score"),
            "passed": r.get("passed", False),
            "failed_stages": r.get("failed_stages", []),
        })
    return {
        "status": "ready",
        "benchmark_version": summary.get("benchmark_version"),
        "cases": cases,
        "count": len(cases),
    }


@router.get("/competitors")
async def benchmarks_competitors():
    """Competitor comparison snapshot for marketing/proof surfaces."""
    # Prefer persisted snapshot if present, else return baseline.
    persisted = _read_json(_BENCH_DIR / "competitor_comparison_latest.json")
    return {
        "status": "ready",
        "baseline": _COMPETITOR_BASELINE,
        "latest_snapshot": persisted,
    }


@router.get("/scorecards")
async def benchmarks_scorecards():
    """List the scorecard modules available in this build."""
    modules: List[Dict[str, Any]] = []
    scorecard_dir = _REPO_ROOT / "backend" / "benchmarks"
    if scorecard_dir.exists():
        for path in sorted(scorecard_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            modules.append({
                "module": f"backend.benchmarks.{path.stem}",
                "name": path.stem.replace("_", " ").title(),
                "file": str(path.relative_to(_REPO_ROOT)),
            })
    return {"status": "ready", "scorecards": modules, "count": len(modules)}
