"""
delivery_gate.py — CrucibAI delivery gate checks.

Provides:
  - write_biv_marker / check_biv_marker   : persist BIV result across retries
  - check_artifact_reconciliation          : SHA256 manifest integrity check
  - check_live_proof_separation            : blocks "live" claims without runtime proof
  - check_visual_qa_gate                   : VQA score/orphan blocking (non-advisory)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# BIV marker persistence (FIX 8)
# ─────────────────────────────────────────────────────────────────────────────

def write_biv_marker(workspace_path: str, biv_result: Dict[str, Any]) -> None:
    """Persist BIV result to .crucibai/biv_final.json so gates can check it across retries."""
    marker_dir = os.path.join(workspace_path, ".crucibai")
    os.makedirs(marker_dir, exist_ok=True)
    marker_path = os.path.join(marker_dir, "biv_final.json")
    payload = {
        "timestamp": time.time(),
        "passed": biv_result.get("passed", False),
        "score": biv_result.get("score", 0),
        "profile": biv_result.get("profile", "unknown"),
        "issues": biv_result.get("issues", []),
        "failure_reason": biv_result.get("failure_reason"),
    }
    try:
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("delivery_gate: BIV marker written — passed=%s score=%s", payload["passed"], payload["score"])
    except OSError as e:
        logger.warning("delivery_gate: failed to write BIV marker: %s", e)


def check_biv_marker(workspace_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Return (passed, marker_dict) from persisted BIV result. Returns (False, None) if missing."""
    marker_path = os.path.join(workspace_path, ".crucibai", "biv_final.json")
    if not os.path.isfile(marker_path):
        return False, None
    try:
        with open(marker_path, encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("passed")), data
    except Exception as e:
        logger.warning("delivery_gate: could not read BIV marker: %s", e)
        return False, None


# ─────────────────────────────────────────────────────────────────────────────
# Artifact reconciliation — SHA256 check (FIX 9)
# ─────────────────────────────────────────────────────────────────────────────

def check_artifact_reconciliation(workspace_path: str) -> Dict[str, Any]:
    """
    Read seal.json + artifact_manifest.json; recompute SHA256 of all listed files.
    Returns {"passed": bool, "issues": [...], "mutated": [...], "missing": [...]}.
    Returns passed=True if no manifest found (optional gate).
    """
    issues: List[str] = []
    mutated: List[str] = []
    missing: List[str] = []

    seal_path = os.path.join(workspace_path, ".crucibai", "seal.json")
    manifest_path = os.path.join(workspace_path, ".crucibai", "artifact_manifest.json")

    if not os.path.isfile(manifest_path):
        return {"passed": True, "issues": [], "mutated": [], "missing": [], "note": "no manifest"}

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        return {"passed": False, "issues": [f"Cannot read artifact_manifest.json: {e}"], "mutated": [], "missing": []}

    entries = manifest if isinstance(manifest, list) else manifest.get("files", [])
    for entry in entries:
        rel = entry.get("path") or entry.get("rel")
        expected_sha = entry.get("sha256") or entry.get("hash")
        if not rel or not expected_sha:
            continue
        full = os.path.join(workspace_path, rel)
        if not os.path.isfile(full):
            missing.append(rel)
            issues.append(f"Manifest file missing from disk: {rel}")
            continue
        try:
            with open(full, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            if actual_sha != expected_sha:
                mutated.append(rel)
                issues.append(f"SHA256 mismatch for {rel} (manifest vs disk)")
        except OSError as e:
            issues.append(f"Cannot read {rel} for SHA256 check: {e}")

    passed = len(issues) == 0
    logger.info("delivery_gate: reconciliation — passed=%s mutated=%d missing=%d", passed, len(mutated), len(missing))
    return {"passed": passed, "issues": issues, "mutated": mutated, "missing": missing}


# ─────────────────────────────────────────────────────────────────────────────
# Live proof separation (FIX 10)
# ─────────────────────────────────────────────────────────────────────────────

_LIVE_CLAIM_PATTERNS = re.compile(
    r"\b(stripe payments? live|live payments?|payments? (are |is )?live|"
    r"real (stripe|braintree)|production payments?)\b",
    re.IGNORECASE,
)

def check_live_proof_separation(workspace_path: str) -> Dict[str, Any]:
    """
    Scan proof/DELIVERY_CLASSIFICATION.md for "live" payment/provider claims.
    If found, verify proof_index.json has runtime-level evidence.
    Returns {"passed": bool, "issues": [...], "rewritten": bool}.
    """
    issues: List[str] = []
    dc_path = os.path.join(workspace_path, "proof", "DELIVERY_CLASSIFICATION.md")
    if not os.path.isfile(dc_path):
        return {"passed": True, "issues": [], "rewritten": False}

    try:
        with open(dc_path, encoding="utf-8") as f:
            dc_text = f.read()
    except OSError:
        return {"passed": True, "issues": [], "rewritten": False}

    live_claims = _LIVE_CLAIM_PATTERNS.findall(dc_text)
    if not live_claims:
        return {"passed": True, "issues": [], "rewritten": False}

    # Check proof_index.json for runtime evidence
    proof_index_path = os.path.join(workspace_path, "proof", "proof_index.json")
    has_runtime_proof = False
    if os.path.isfile(proof_index_path):
        try:
            with open(proof_index_path, encoding="utf-8") as f:
                proof_index = json.load(f)
            entries = proof_index if isinstance(proof_index, list) else proof_index.get("entries", [])
            has_runtime_proof = any(
                e.get("level") in ("runtime", "live", "production")
                for e in entries
            )
        except Exception:
            pass

    if not has_runtime_proof:
        # Auto-rewrite claims from "live" → "Mocked"
        rewritten = _LIVE_CLAIM_PATTERNS.sub(
            lambda m: m.group(0).replace("live", "Mocked").replace("Live", "Mocked").replace("real", "mocked"),
            dc_text,
        )
        try:
            with open(dc_path, "w", encoding="utf-8") as f:
                f.write(rewritten)
            logger.warning("delivery_gate: rewrote %d live claim(s) → Mocked in DELIVERY_CLASSIFICATION.md", len(live_claims))
        except OSError:
            pass
        issues.append(
            f"Delivery classification claimed {len(live_claims)} live payment(s) but no runtime proof found — rewritten to Mocked"
        )
        return {"passed": False, "issues": issues, "rewritten": True}

    return {"passed": True, "issues": [], "rewritten": False}


# ─────────────────────────────────────────────────────────────────────────────
# Visual QA gate — blocking (FIX 11)
# ─────────────────────────────────────────────────────────────────────────────

VQA_MIN_SCORE = 55
VQA_MAX_ORPHANS = 10

def check_visual_qa_gate(vqa_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate VQA result and return gate decision.
    Previously advisory-only — now blocks completion when score < 55 or orphans > 10.
    """
    score = vqa_result.get("score", 100)
    orphans = vqa_result.get("orphan_count", 0)
    issues: List[str] = []

    if score < VQA_MIN_SCORE:
        issues.append(f"Visual QA score {score} is below minimum {VQA_MIN_SCORE}")
    if orphans > VQA_MAX_ORPHANS:
        issues.append(f"Visual QA found {orphans} orphaned components (max {VQA_MAX_ORPHANS})")

    passed = len(issues) == 0
    if not passed:
        logger.warning("delivery_gate: VQA gate FAILED — score=%s orphans=%s", score, orphans)
    return {
        "passed": passed,
        "issues": issues,
        "score": score,
        "orphan_count": orphans,
        "failure_reason": "visual_qa" if not passed else None,
    }
