"""
Weighted verification truth: Presence 10%, Syntax 20%, Runtime 40%, Experience 30%.
Trust score penalizes missing classes and claims without evidence.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple

# Weights from approved roadmap
W_PRESENCE = 0.10
W_SYNTAX = 0.20
W_RUNTIME = 0.40
W_EXPERIENCE = 0.30


def _class_counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"presence": 0, "syntax": 0, "runtime": 0, "experience": 0, "unknown": 0}
    for it in items:
        payload = it.get("payload") if isinstance(it.get("payload"), dict) else {}
        vc = (payload.get("verification_class") or "unknown").lower()
        if vc in counts:
            counts[vc] += 1
        else:
            counts["unknown"] += 1
    return counts


def _normalized_coverage(counts: Dict[str, int], total: int) -> Dict[str, float]:
    if total <= 0:
        return {k: 0.0 for k in ("presence", "syntax", "runtime", "experience")}
    return {
        "presence": min(1.0, counts["presence"] / max(1, total * 0.15)),
        "syntax": min(1.0, counts["syntax"] / max(1, total * 0.12)),
        "runtime": min(1.0, counts["runtime"] / max(1, total * 0.10)),
        "experience": min(1.0, counts["experience"] / max(1, total * 0.08)),
    }


def compute_trust_metrics(
    items: List[Dict[str, Any]],
    *,
    has_screenshot_proof: bool = False,
    has_live_deploy_url: bool = False,
) -> Dict[str, Any]:
    """
    items: list of dicts with keys payload (dict), proof_type, title.
    """
    total = len(items)
    counts = _class_counts(items)
    cov = _normalized_coverage(counts, total)

    class_weighted = round(
        100
        * (
            W_PRESENCE * cov["presence"]
            + W_SYNTAX * cov["syntax"]
            + W_RUNTIME * cov["runtime"]
            + W_EXPERIENCE * cov["experience"]
        ),
        2,
    )

    penalties = 0
    if not has_screenshot_proof and counts["experience"] < 1:
        penalties += 15
    if not has_live_deploy_url:
        penalties += 5

    trust_score = max(0.0, float(class_weighted) - penalties)

    truth_status = {
        "preview_visual_evidence": has_screenshot_proof,
        "deploy_live_evidence": has_live_deploy_url,
        "claims_verified_only_with_proof": True,
        "weights": {
            "presence": W_PRESENCE,
            "syntax": W_SYNTAX,
            "runtime": W_RUNTIME,
            "experience": W_EXPERIENCE,
        },
    }

    return {
        "verification_class_counts": counts,
        "class_coverage": cov,
        "class_weighted_score": class_weighted,
        "trust_score": round(trust_score, 2),
        "penalties_applied": penalties,
        "truth_status": truth_status,
    }


def sha256_file_preview(path: str, max_bytes: int = 65536) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(max_bytes))
        return h.hexdigest()[:32]
    except OSError:
        return ""
