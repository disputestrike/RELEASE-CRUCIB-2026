"""Public trust routes for benchmark and security posture evidence."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def create_trust_router(root_dir: Path) -> APIRouter:
    """Create the public trust router.

    The backend runs from ``backend/`` locally but from ``/app`` in the Docker
    image, so proof lookup checks both repo-relative and image-root locations.
    """
    router = APIRouter(prefix="/api", tags=["trust"])
    proof_candidates = [
        root_dir.parent / "proof" / "benchmarks" / "repeatability_v1",
        root_dir / "proof" / "benchmarks" / "repeatability_v1",
        Path("/proof/benchmarks/repeatability_v1"),
    ]

    @router.get("/trust/benchmark-summary")
    async def trust_benchmark_summary():
        """Public benchmark summary for trust/status/benchmark pages."""
        summary_path = _first_existing(path / "summary.json" for path in proof_candidates)
        pass_fail_path = _first_existing(path / "PASS_FAIL.md" for path in proof_candidates)
        if not summary_path:
            return {
                "status": "not_available",
                "message": "Repeatability benchmark proof has not been generated in this deployment.",
                "prompt_count": 0,
                "passed_count": 0,
                "pass_rate": 0,
                "average_score": 0,
                "proof": {"summary": "proof/benchmarks/repeatability_v1/summary.json", "pass_fail": None},
                "cases": [],
            }
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("trust_benchmark_summary parse failed: %s", exc)
            raise HTTPException(status_code=503, detail="Benchmark proof summary unreadable")
        return {
            "status": "ready" if data.get("passed") else "failing",
            "benchmark_version": data.get("benchmark_version"),
            "generated_at": data.get("generated_at"),
            "prompt_count": data.get("prompt_count"),
            "passed_count": data.get("passed_count"),
            "pass_rate": data.get("pass_rate"),
            "average_score": data.get("average_score"),
            "thresholds": data.get("thresholds"),
            "preview_mode": data.get("preview_mode"),
            "summary_sha256": data.get("summary_sha256"),
            "blockers": data.get("blockers") or [],
            "proof": {
                "summary": "proof/benchmarks/repeatability_v1/summary.json",
                "pass_fail": "proof/benchmarks/repeatability_v1/PASS_FAIL.md" if pass_fail_path else None,
            },
            "cases": [
                {
                    "id": ((case.get("case") or {}).get("id")),
                    "category": ((case.get("case") or {}).get("category")),
                    "score": case.get("score"),
                    "passed": case.get("passed"),
                }
                for case in (data.get("results") or [])
                if isinstance(case, dict)
            ],
        }

    @router.get("/trust/security-posture")
    async def trust_security_posture():
        """Public security posture summary without exposing secret values."""
        return {
            "database": "PostgreSQL only",
            "tenant_isolation": "auth and project ownership enforced on workspace/job/helper routes",
            "terminal_policy": {
                "status": "restricted",
                "public_default": "disabled unless CRUCIBAI_TERMINAL_ENABLED explicitly allows it",
                "boundary": "project-scoped with command deny policy; container sandbox remains launch debt before broad public exposure",
            },
            "proof_locations": [
                "proof/phase2_security/",
                "proof/pipeline_crash_fix/",
                "proof/live_production_golden_path/",
                "proof/benchmarks/",
            ],
            "generated_app_publish": {
                "mode": "in-platform public URL",
                "route": "/published/{job_id}/",
                "external_providers": "Vercel/Netlify/Railway adapters remain separate provider work",
            },
        }

    return router
