"""
Build contract helpers for CrucibAI proof bundles.

The contract is the stable "what was promised / what was proved" envelope
around a build. It is intentionally small so the UI, tests, and future deploy
gates can depend on it without coupling to every proof row detail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

CONTRACT_VERSION = "2026-04-08.v1"

GOLDEN_PATH_STAGES = [
    "goal",
    "plan",
    "approval",
    "workspace",
    "build",
    "proof",
    "preview",
    "export_or_deploy",
    "continue",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step_counts(steps: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for step in steps or []:
        status = str(step.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _evidence_flags(bundle: Mapping[str, Any]) -> Dict[str, bool]:
    groups = bundle or {}
    verification_rows = groups.get("verification") or []
    deploy_rows = groups.get("deploy") or []
    file_rows = groups.get("files") or []
    return {
        "files": bool(file_rows),
        "verification": bool(verification_rows),
        "deploy": bool(deploy_rows),
        "preview": any(
            (row.get("payload") or {}).get("kind") in {"preview", "preview_screenshot"}
            for row in verification_rows
        ),
        "tests": any(
            (row.get("type") or row.get("proof_type")) == "test"
            for row in verification_rows
        ),
    }


def build_contract(
    *,
    job: Optional[Mapping[str, Any]],
    steps: Iterable[Mapping[str, Any]],
    bundle: Mapping[str, Any],
    bundle_sha256: str,
    quality_score: float,
    trust_score: float,
    production_readiness_score: float,
) -> Dict[str, Any]:
    """Return the stable contract summary for a job proof bundle."""
    job = job or {}
    step_list: List[Mapping[str, Any]] = list(steps or [])
    counts = _step_counts(step_list)
    evidence = _evidence_flags(bundle)
    blockers: List[str] = []

    if not job.get("goal"):
        blockers.append("missing_goal")
    if counts.get("failed") or counts.get("blocked"):
        blockers.append("failed_or_blocked_steps")
    if not evidence["files"]:
        blockers.append("missing_file_evidence")
    if not evidence["verification"]:
        blockers.append("missing_verification_evidence")
    if float(production_readiness_score or 0.0) < 70.0:
        blockers.append("production_readiness_below_70")

    completed_steps = counts.get("completed", 0)
    total_steps = len(step_list)
    return {
        "version": CONTRACT_VERSION,
        "generated_at": _now_iso(),
        "job_id": job.get("id"),
        "project_id": job.get("project_id"),
        "user_id": job.get("user_id"),
        "goal": job.get("goal") or "",
        "status": job.get("status") or "unknown",
        "mode": job.get("mode") or "guided",
        "golden_path": GOLDEN_PATH_STAGES,
        "step_counts": counts,
        "step_completion": {
            "completed": completed_steps,
            "total": total_steps,
            "percent": round((completed_steps / max(1, total_steps)) * 100, 2),
        },
        "evidence": evidence,
        "scores": {
            "quality": float(quality_score or 0.0),
            "trust": float(trust_score or 0.0),
            "production_readiness": float(production_readiness_score or 0.0),
        },
        "deploy_ready": len(blockers) == 0,
        "blockers": blockers,
        "bundle_sha256": bundle_sha256,
    }


def empty_contract(job_id: str) -> Dict[str, Any]:
    """Contract shape for unavailable proof state."""
    return build_contract(
        job={"id": job_id, "status": "unknown", "goal": ""},
        steps=[],
        bundle={},
        bundle_sha256="",
        quality_score=0.0,
        trust_score=0.0,
        production_readiness_score=0.0,
    )
