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
    verification_failed_count: int = 0,
    build_verified: Optional[bool] = None,
    truth_surface: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the stable contract summary for a job proof bundle."""
    job = job or {}
    ts = dict(truth_surface or {})
    preview_source = str(ts.get("preview_source") or "unknown").strip() or "unknown"
    prompt_contract_passed = ts.get("prompt_contract_passed", True)
    if isinstance(prompt_contract_passed, str):
        prompt_contract_passed = prompt_contract_passed.lower() in ("1", "true", "yes")
    preview_verified = bool(ts.get("preview_verified"))
    step_list: List[Mapping[str, Any]] = list(steps or [])
    counts = _step_counts(step_list)
    evidence = _evidence_flags(bundle)
    blockers: List[str] = []

    if not job.get("goal"):
        blockers.append("missing_goal")
    if counts.get("failed") or counts.get("blocked"):
        blockers.append("failed_or_blocked_steps")
    st = str(job.get("status") or "").strip().lower()
    if st and st != "completed":
        blockers.append("job_not_completed")
    if int(verification_failed_count or 0) > 0:
        blockers.append("verification_failures_in_proof")
    if build_verified is False:
        blockers.append("build_not_verified")
    if prompt_contract_passed is False:
        blockers.append("prompt_contract_failed")
    if preview_source in (
        "sandpack_fallback",
        "diagnostic_fallback",
        "main_app_shell",
    ):
        blockers.append("preview_not_generated_artifact")
    if preview_source == "generated_artifact" and not preview_verified:
        blockers.append("preview_not_verified")
    if not evidence["files"]:
        blockers.append("missing_file_evidence")
    if not evidence["verification"]:
        blockers.append("missing_verification_evidence")
    if float(production_readiness_score or 0.0) < 70.0:
        blockers.append("production_readiness_below_70")

    completed_steps = counts.get("completed", 0)
    total_steps = len(step_list)
    deploy_ready = len(blockers) == 0
    export_ready = deploy_ready and evidence["files"] and st == "completed"
    delivery_ready = export_ready and prompt_contract_passed is not False
    success = deploy_ready and bool(build_verified)
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
        "truth_surface": {
            "preview_source": preview_source,
            "prompt_contract_passed": bool(prompt_contract_passed),
            "preview_verified": preview_verified,
            "browser_verified": bool(ts.get("browser_verified")),
            "generated_app_type": str(ts.get("generated_app_type") or "unknown"),
        },
        "scores": {
            "quality": float(quality_score or 0.0),
            "trust": float(trust_score or 0.0),
            "production_readiness": float(production_readiness_score or 0.0),
        },
        "deploy_ready": deploy_ready,
        "export_ready": export_ready,
        "delivery_ready": delivery_ready,
        "success": success,
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
        verification_failed_count=0,
        build_verified=False,
    )
