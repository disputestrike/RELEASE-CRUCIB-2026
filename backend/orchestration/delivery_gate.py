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



# ── Artifact reconciliation ────────────────────────────────────────────────────

def check_artifact_reconciliation(workspace_path: str) -> GateResult:
    """
    Gate 4: Disk SHA256 must match the sealed manifest.

    Reads .crucibai/seal.json (manifest_sha256) and .crucibai/artifact_manifest.json
    (per-file hashes), then recomputes a fresh SHA256 of the files listed in the
    manifest.  If any file is missing or its hash differs → block.

    Rationale: agents can silently mutate files after the seal. This gate makes
    post-seal mutations a hard delivery failure, not just a log warning.
    """
    if not workspace_path:
        return GateResult(True, 200, "OK (no workspace)")

    seal = _read_json(workspace_path, ".crucibai/seal.json")
    if seal is None:
        # Seal absent — old build or in-progress; allow unless required.
        if os.environ.get("CRUCIBAI_GATE_SEAL_REQUIRED", "0").strip() == "1":
            return GateResult(False, 423, "Workspace has no seal — build did not complete final assembly step.")
        return GateResult(True, 200, "OK (no seal — skipped)")

    stored_sha = seal.get("manifest_sha256")
    if not stored_sha:
        return GateResult(True, 200, "OK (seal has no manifest_sha256 — legacy build)")

    manifest = _read_json(workspace_path, ".crucibai/artifact_manifest.json")
    if manifest is None:
        return GateResult(True, 200, "OK (no artifact_manifest — cannot recompute)")

    files = manifest.get("files") or []
    if not files:
        return GateResult(True, 200, "OK (empty manifest)")

    import hashlib as _hl
    current: dict = {}
    mismatches: list = []
    missing: list = []

    for entry in files:
        rel = entry.get("path", "")
        stored_hash = entry.get("sha256", "")
        if not rel:
            continue
        full = os.path.join(workspace_path, rel)
        # Skip META dir (seal files themselves)
        if rel.startswith(".crucibai/") or rel.startswith("META/"):
            continue
        if not os.path.isfile(full):
            missing.append(rel)
            continue
        try:
            raw = Path(full).read_bytes()
            live_hash = _hl.sha256(raw).hexdigest()
        except OSError:
            missing.append(rel)
            continue
        current[rel] = live_hash
        if stored_hash and live_hash != stored_hash:
            mismatches.append(rel)

    if missing or mismatches:
        detail_parts = []
        if mismatches:
            detail_parts.append(f"{len(mismatches)} file(s) changed after seal: {mismatches[:5]}")
        if missing:
            detail_parts.append(f"{len(missing)} file(s) missing from disk: {missing[:5]}")
        logger.warning(
            "delivery_gate: artifact reconciliation FAILED — %s mismatches, %s missing",
            len(mismatches), len(missing),
        )
        return GateResult(
            False, 409,
            "Artifact integrity failure: " + "; ".join(detail_parts) + ". "
            "Files were modified after the build seal. Re-run the build to generate a clean artifact.",
            {"gate": "artifact_reconciliation", "mismatches": mismatches[:10], "missing": missing[:10]},
        )

    return GateResult(True, 200, "OK", {"gate": "artifact_reconciliation", "files_verified": len(current)})


# ── Live proof separation ──────────────────────────────────────────────────────

# Claims that must NOT appear in "Implemented" without verified proof.
_LIVE_CLAIM_PATTERNS = [
    (r"stripe|payment|billing|checkout|webhook", "stripe/payment"),
    (r"twilio|sms|sendgrid|email.*send|smtp", "messaging"),
    (r"oauth|google.*auth|github.*auth|social.*login", "oauth"),
    (r"aws|s3|gcs|azure|cloud.*storage", "cloud-storage"),
    (r"openai|anthropic|gpt|claude|llm.*api", "llm-api"),
    (r"database.*live|postgres.*live|mysql.*live", "live-database"),
]

# Proof verification_class values that satisfy a live claim
_LIVE_PROOF_RANKS = {"behavior_assertion", "negative_test", "state_transition", "e2e", "runtime"}


def check_live_proof_separation(workspace_path: str) -> GateResult:
    """
    Gate 5: Claims labeled as 'Implemented' must have verified proof.

    Parses proof/DELIVERY_CLASSIFICATION.md 'Implemented' section.
    For each live-integration pattern found there (Stripe, OAuth, Twilio, etc.),
    checks that the proof bundle contains at least one non-trivial proof item
    (verification_class >= runtime).

    If a claim is in 'Implemented' but has only presence/syntax proof → block
    and rewrite the section to 'Mocked' in the delivery classification.
    """
    if not workspace_path:
        return GateResult(True, 200, "OK")

    # Read DELIVERY_CLASSIFICATION.md
    dc_path = os.path.join(workspace_path, "proof", "DELIVERY_CLASSIFICATION.md")
    if not os.path.isfile(dc_path):
        return GateResult(True, 200, "OK (no DELIVERY_CLASSIFICATION.md — gate skipped)")

    try:
        dc_text = Path(dc_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return GateResult(True, 200, "OK (cannot read DELIVERY_CLASSIFICATION.md)")

    # Parse 'Implemented' section
    import re as _re
    implemented_match = _re.search(
        r"^##\s+Implemented\s*\n(.*?)(?=^##\s|\Z)", dc_text, _re.M | _re.S | _re.I
    )
    if not implemented_match:
        return GateResult(True, 200, "OK (no Implemented section)")
    implemented_text = implemented_match.group(1).lower()

    # Read proof summary for verification class info
    proof_summary = _read_json(workspace_path, ".crucibai/proof_summary.json") or {}
    # Also try full artifact manifest for proof items
    proof_items_path = os.path.join(workspace_path, "proof", "proof_index.json")
    proof_flat: list = []
    if os.path.isfile(proof_items_path):
        try:
            pi = json.loads(Path(proof_items_path).read_text())
            proof_flat = pi.get("flat") or pi.get("items") or []
        except Exception:
            pass

    # Collect strong proof check names
    strong_checks: set = set()
    for item in proof_flat:
        payload = item.get("payload") or {}
        vc = (payload.get("verification_class") or "presence").lower()
        if vc in _LIVE_PROOF_RANKS:
            strong_checks.add((payload.get("check") or "").lower())
            strong_checks.add((item.get("title") or "").lower())

    # Check each live-claim pattern
    unverified: list = []
    for pattern, label in _LIVE_CLAIM_PATTERNS:
        if _re.search(pattern, implemented_text):
            # This integration is claimed as Implemented.
            # Check if any strong proof item mentions this integration.
            has_strong = any(
                _re.search(pattern, check) for check in strong_checks
            )
            if not has_strong:
                unverified.append(label)

    if not unverified:
        return GateResult(True, 200, "OK", {"gate": "live_proof_separation"})

    # Rewrite DELIVERY_CLASSIFICATION.md — move unverified claims to Mocked
    try:
        _downgrade_delivery_classification(dc_path, dc_text, unverified)
        logger.warning(
            "delivery_gate: live_proof_separation DOWNGRADED %d claim(s) to Mocked: %s",
            len(unverified), unverified,
        )
    except Exception as exc:
        logger.warning("delivery_gate: could not rewrite DELIVERY_CLASSIFICATION: %s", exc)

    # In strict mode: block. In advisory: warn only.
    gate_mode = (os.environ.get("CRUCIBAI_ENFORCEMENT_GATE") or "strict").strip().lower()
    if gate_mode == "strict":
        return GateResult(
            False, 422,
            f"Live integration claim(s) {unverified} appear in Implemented section but have no "
            f"verified proof (behavior_assertion/runtime or stronger). "
            f"Claims have been downgraded to Mocked in DELIVERY_CLASSIFICATION.md. "
            f"Add real integration tests or move claims to Mocked/Unverified.",
            {"gate": "live_proof_separation", "unverified_claims": unverified},
        )
    # Advisory: allow but log
    return GateResult(True, 200, "OK (advisory — live proof gap detected)",
                      {"gate": "live_proof_separation", "advisory_unverified": unverified})


def _downgrade_delivery_classification(
    dc_path: str, dc_text: str, labels: list
) -> None:
    """Move unverified claims from Implemented to Mocked section."""
    import re as _re
    note = "\n".join(
        f"- {label} (auto-downgraded: no verified proof at delivery gate)"
        for label in labels
    )
    if not _re.search(r"^##\s+Mocked", dc_text, _re.M | _re.I):
        dc_text = dc_text.rstrip() + "\n\n## Mocked\n\n" + note + "\n"
    else:
        dc_text = _re.sub(
            r"(^##\s+Mocked\s*\n)",
            r"\1\n" + note + "\n",
            dc_text, flags=_re.M | _re.I, count=1,
        )
    Path(dc_path).write_text(dc_text, encoding="utf-8")

def check_visual_qa(workspace_path: str) -> GateResult:
    """
    Gate 6: Visual QA marker must show passing score.

    Reads .crucibai/visual_qa.json (written by visual_qa.run_visual_qa()).
    If score < 55 → block (not just advisory).
    Orphan count > 10 → block (too many unreachable components).
    """
    if not workspace_path:
        return GateResult(True, 200, "OK")

    vqa = _read_json(workspace_path, ".crucibai/visual_qa.json")
    if vqa is None:
        return GateResult(True, 200, "OK (no VQA marker — gate skipped)")

    score = vqa.get("score", 100)
    orphans = vqa.get("orphans") or []
    issues  = vqa.get("issues") or []
    passed  = vqa.get("passed", True)

    _vqa_min = int(os.environ.get("CRUCIBAI_MIN_VQA_SCORE", "55"))
    _max_orphans = int(os.environ.get("CRUCIBAI_MAX_ORPHANS", "10"))

    if score < _vqa_min:
        return GateResult(
            False, 422,
            f"Visual QA score {score} is below minimum {_vqa_min}. "
            f"Top issues: {'; '.join(str(i) for i in issues[:3]) or 'see build log'}. "
            "Fix component routing and DOM contracts before delivering.",
            {"gate": "visual_qa", "score": score, "required": _vqa_min},
        )

    if len(orphans) > _max_orphans:
        return GateResult(
            False, 422,
            f"Visual QA found {len(orphans)} orphan components not reachable from App.jsx "
            f"(max {_max_orphans} allowed). Move unused components to _drafts/ or import them.",
            {"gate": "visual_qa", "orphan_count": len(orphans), "orphans": orphans[:10]},
        )

    return GateResult(True, 200, "OK", {"gate": "visual_qa", "score": score})


# ── Browser QA gate ────────────────────────────────────────────────────────────

def check_browser_qa(workspace_path: str) -> GateResult:
    """
    Gate 7: Browser QA marker must show passing score.

    Reads .crucibai/browser_qa.json (written by browser_qa.run_browser_qa()).
    Only applied when a dist/ build artifact exists (not source-only workspaces).
    """
    if not workspace_path:
        return GateResult(True, 200, "OK")

    # Only gate if dist/index.html exists
    if not os.path.isfile(os.path.join(workspace_path, "dist", "index.html")):
        return GateResult(True, 200, "OK (no dist — browser QA skipped)")

    bqa = _read_json(workspace_path, ".crucibai/browser_qa.json")
    if bqa is None:
        return GateResult(True, 200, "OK (no browser QA marker — gate skipped)")

    if bqa.get("method") == "skipped":
        return GateResult(True, 200, "OK (browser QA skipped by runner)")

    score  = bqa.get("score", 100)
    passed = bqa.get("passed", True)
    routes_ok    = bqa.get("routes_ok", 0)
    routes_total = bqa.get("routes_total", 0)
    issues = bqa.get("issues") or []

    _bqa_min = int(os.environ.get("CRUCIBAI_MIN_BQA_SCORE", "60"))

    if not passed or score < _bqa_min:
        return GateResult(
            False, 422,
            f"Browser QA failed (score={score}, routes_ok={routes_ok}/{routes_total}). "
            f"Issues: {'; '.join(str(i) for i in issues[:3]) or 'see build log'}. "
            "Built artifact has reachability or DOM contract failures.",
            {"gate": "browser_qa", "score": score, "required": _bqa_min,
             "routes_ok": routes_ok, "routes_total": routes_total},
        )

    return GateResult(True, 200, "OK", {"gate": "browser_qa", "score": score})

# ── Composite gate ─────────────────────────────────────────────────────────────

def run_download_gate(
    workspace_path: str,
    *,
    draft: bool = False,
) -> GateResult:
    """
    Full delivery gate for ZIP downloads and artifact exports.
    draft=True skips the proof score check (user explicitly requested draft).

    Gates (in order):
      1. BIV marker — must have passed
      2. Proof score — non-trivial evidence threshold (skipped in draft mode)
      3. Artifact reconciliation — disk bytes must match sealed manifest
      4. Live proof separation — 'Implemented' claims need verified proof
      5. Visual QA — score and orphan limits
    """
    r = check_biv_marker(workspace_path)
    if not r.passed:
        return r

    if not draft:
        r = check_proof_score(workspace_path)
        if not r.passed:
            return r

    r = check_artifact_reconciliation(workspace_path)
    if not r.passed:
        return r

    if not draft:
        r = check_live_proof_separation(workspace_path)
        if not r.passed:
            return r

    r = check_visual_qa(workspace_path)
    if not r.passed:
        return r

    return GateResult(True, 200, "OK", {"gate": "download", "draft": draft})


def run_publish_gate(workspace_path: str) -> GateResult:
    """
    Full delivery gate for /published/{job_id} serving.

    Gates (in order):
      1. BIV marker
      2. Proof score
      3. dist/index.html exists
      4. Artifact reconciliation
      5. Live proof separation
      6. Visual QA score + orphan limit
      7. Browser QA score
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

    r = check_artifact_reconciliation(workspace_path)
    if not r.passed:
        return r

    r = check_live_proof_separation(workspace_path)
    if not r.passed:
        return r

    r = check_visual_qa(workspace_path)
    if not r.passed:
        return r

    r = check_browser_qa(workspace_path)
    if not r.passed:
        return r

    return GateResult(True, 200, "OK", {"gate": "publish"})
