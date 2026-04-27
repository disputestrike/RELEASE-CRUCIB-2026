"""
delivery_gate.py — Universal delivery gate for CrucibAI builds.

Centralises all pre-delivery checks so that EVERY exit path from the system
(ZIP download, /published/ serve, manual export) runs the same guards.

Guards (in order):
1. BIV marker  — .crucibai/biv_final.json must exist and passed=True
2. Proof score — proof bundle score must meet minimum threshold
3. dist/index.html — published builds must have a built artifact

Design rules from the research synthesis:
  • Validator exists but must be a universal gate — not advisory.
  • Proof with score < threshold is a FAIL regardless of user intent.
  • /published/{job_id} only if dist/index.html passed final BIV.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
# Match HARD_FAIL_THRESHOLD in build_integrity_validator.py (70).
# Raise env var CRUCIBAI_MIN_BIV_SCORE to tighten; lower only for dev.
_DEFAULT_MIN_BIV_SCORE = 70
_DEFAULT_MIN_PROOF_SCORE = 0.40   # 40 % of proof items must be non-trivial

BIV_MARKER_PATH = ".crucibai/biv_final.json"
PROOF_MARKER_PATH = ".crucibai/proof_summary.json"


def _read_json(workspace_path: str, rel: str) -> Optional[Dict[str, Any]]:
    full = os.path.join(workspace_path, rel)
    if not os.path.isfile(full):
        return None
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            return json.loads(fh.read())
    except Exception:
        return None


def _min_biv_score() -> int:
    try:
        return int(os.environ.get("CRUCIBAI_MIN_BIV_SCORE", "") or _DEFAULT_MIN_BIV_SCORE)
    except Exception:
        return _DEFAULT_MIN_BIV_SCORE


def _min_proof_score() -> float:
    try:
        return float(os.environ.get("CRUCIBAI_MIN_PROOF_SCORE", "") or _DEFAULT_MIN_PROOF_SCORE)
    except Exception:
        return _DEFAULT_MIN_PROOF_SCORE


def write_biv_marker(workspace_path: str, biv_result: Dict[str, Any]) -> None:
    """Persist the final BIV result to disk so download/publish gates can read it
    without needing DB access. Called by auto_runner after each BIV run."""
    if not workspace_path:
        return
    meta_dir = Path(workspace_path) / ".crucibai"
    try:
        meta_dir.mkdir(parents=True, exist_ok=True)
        marker = {
            "passed": bool(biv_result.get("passed")),
            "score": biv_result.get("score"),
            "profile": biv_result.get("profile"),
            "phase": biv_result.get("phase"),
            "recommendation": biv_result.get("recommendation"),
            "issues": (biv_result.get("issues") or [])[:20],
            "retry_targets": biv_result.get("retry_targets") or [],
        }
        (meta_dir / "biv_final.json").write_text(
            json.dumps(marker, indent=2), encoding="utf-8"
        )
        logger.info(
            "delivery_gate: wrote BIV marker score=%s passed=%s", marker["score"], marker["passed"]
        )
    except Exception as exc:
        logger.warning("delivery_gate: could not write BIV marker: %s", exc)


def write_proof_summary(workspace_path: str, proof: Dict[str, Any]) -> None:
    """Persist a lightweight proof summary used by the proof score gate."""
    if not workspace_path:
        return
    meta_dir = Path(workspace_path) / ".crucibai"
    try:
        meta_dir.mkdir(parents=True, exist_ok=True)
        flat = proof.get("flat") or proof.get("items") or []
        total = len(flat)
        # Count non-trivial proof items (rank > presence)
        strong = sum(
            1 for item in flat
            if (item.get("payload") or {}).get("verification_class", "presence") != "presence"
        )
        score = (strong / total) if total > 0 else 0.0
        summary = {
            "total_items": total,
            "strong_items": strong,
            "proof_score": round(score, 4),
            "trust_score": proof.get("trust_score"),
            "quality_score": proof.get("quality_score"),
            "production_readiness_score": proof.get("production_readiness_score"),
        }
        (meta_dir / "proof_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("delivery_gate: could not write proof summary: %s", exc)


# ── Gate result ───────────────────────────────────────────────────────────────

class GateResult:
    """Simple value object — gate_passed, http_status, detail."""

    def __init__(self, passed: bool, status: int, detail: str, meta: Optional[Dict] = None):
        self.passed = passed
        self.status = status
        self.detail = detail
        self.meta = meta or {}

    def raise_if_blocked(self):
        """Raise an HTTPException if gate is blocked."""
        if not self.passed:
            from fastapi import HTTPException
            raise HTTPException(status_code=self.status, detail=self.detail)


# ── Individual gate checks ────────────────────────────────────────────────────

def check_biv_marker(workspace_path: str) -> GateResult:
    """
    Gate 1: BIV must have run and passed.

    - If marker is missing → 423 Locked (build never reached final gate)
    - If marker present but failed → 422 Unprocessable (build failed BIV)
    - If passed → OK
    """
    if not workspace_path:
        return GateResult(False, 423, "Workspace not available for delivery gate check")

    marker = _read_json(workspace_path, BIV_MARKER_PATH)
    if marker is None:
        # Marker absent — BIV never ran (old build or dev env). Emit a warning
        # but allow in environments that set CRUCIBAI_GATE_BIV_REQUIRED=0.
        if os.environ.get("CRUCIBAI_GATE_BIV_REQUIRED", "1").strip() != "0":
            return GateResult(
                False, 423,
                "Build has not passed the Build Integrity Validator. "
                "Download is blocked until the build completes successfully.",
                {"gate": "biv_marker", "reason": "marker_missing"},
            )
        logger.warning("delivery_gate: BIV marker missing — allowing (CRUCIBAI_GATE_BIV_REQUIRED=0)")
        return GateResult(True, 200, "OK (biv gate bypassed by env)", {"gate": "biv_marker", "skipped": True})

    if not marker.get("passed"):
        score = marker.get("score")
        issues = (marker.get("issues") or [])[:5]
        issue_summary = "; ".join(str(i) for i in issues)[:300]
        return GateResult(
            False, 422,
            f"Build failed integrity check (score={score}). "
            f"Top issues: {issue_summary or 'see build log for details'}. "
            "Please rebuild or request a repair before downloading.",
            {"gate": "biv_marker", "score": score, "issues": issues},
        )

    score = marker.get("score")
    min_score = _min_biv_score()
    if score is not None and isinstance(score, (int, float)) and score < min_score:
        return GateResult(
            False, 422,
            f"Build integrity score {score} is below required minimum {min_score}. "
            "Rebuild to improve score before downloading.",
            {"gate": "biv_score", "score": score, "required": min_score},
        )

    return GateResult(True, 200, "OK", {"gate": "biv_marker", "score": score})


def check_proof_score(workspace_path: str) -> GateResult:
    """
    Gate 2: Proof score must meet minimum threshold.

    Proof hard-block: any proof bundle with score below threshold blocks delivery
    unless the user explicitly requested a draft export.
    """
    if not workspace_path:
        return GateResult(True, 200, "OK (no workspace)")

    summary = _read_json(workspace_path, PROOF_MARKER_PATH)
    if summary is None:
        # Proof not yet written — allow, but log
        logger.debug("delivery_gate: proof summary missing — gate skipped")
        return GateResult(True, 200, "OK (no proof summary)")

    proof_score = summary.get("proof_score")
    if proof_score is None:
        return GateResult(True, 200, "OK (no proof score)")

    min_ps = _min_proof_score()
    if isinstance(proof_score, float) and proof_score < min_ps:
        return GateResult(
            False, 422,
            f"Proof score {proof_score:.0%} is below the required {min_ps:.0%} threshold. "
            "The build has insufficient verification evidence. "
            "Use draft mode or request a stronger build.",
            {"gate": "proof_score", "proof_score": proof_score, "required": min_ps},
        )

    return GateResult(True, 200, "OK", {"gate": "proof_score", "proof_score": proof_score})


def check_dist_index(workspace_path: str, project_id: Optional[str] = None) -> GateResult:
    """
    Gate 3: Published builds must have dist/index.html.
    Only applied to /published/ route — ZIP downloads keep source files.
    """
    check_path = workspace_path
    if project_id:
        # Try project-scoped path first
        from pathlib import Path as _Path
        candidate = _Path(workspace_path).parent / project_id / "dist" / "index.html"
        if candidate.exists():
            return GateResult(True, 200, "OK")
    dist_index = os.path.join(check_path, "dist", "index.html")
    if not os.path.isfile(dist_index):
        return GateResult(
            False, 404,
            "Published app has no built artifact (dist/index.html missing). "
            "The build may still be in progress or failed during the Vite build step.",
            {"gate": "dist_index", "expected": dist_index},
        )
    return GateResult(True, 200, "OK", {"gate": "dist_index"})


# ── Composite gate ─────────────────────────────────────────────────────────────

def run_download_gate(
    workspace_path: str,
    *,
    draft: bool = False,
) -> GateResult:
    """
    Full delivery gate for ZIP downloads and artifact exports.
    draft=True skips the proof score check (user explicitly requested draft).
    """
    r = check_biv_marker(workspace_path)
    if not r.passed:
        return r

    if not draft:
        r = check_proof_score(workspace_path)
        if not r.passed:
            return r

    return GateResult(True, 200, "OK", {"gate": "download", "draft": draft})


def run_publish_gate(workspace_path: str) -> GateResult:
    """
    Full delivery gate for /published/{job_id} serving.
    BIV + proof + dist/index.html all required.
    """
    r = check_biv_marker(workspace_path)
    if not r.passed:
        return r

    r = check_proof_score(workspace_path)
    if not r.passed:
        return r

    r = check_dist_index(workspace_path)
    if not r.passed:
        return r

    return GateResult(True, 200, "OK", {"gate": "publish"})
