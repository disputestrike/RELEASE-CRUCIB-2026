"""
verification.behavior — tenancy isolation + payment webhook idempotency + RBAC smoke in one bundle.

Also invoked from verification.security so every Auto-Runner job runs behavioral gates without extra DAG nodes.
"""

from __future__ import annotations

from typing import Any, Dict, List


def merge_verification_results(parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []
    for p in parts:
        issues.extend(p.get("issues") or [])
        proof.extend(p.get("proof") or [])
    passed = all(bool(p.get("passed")) for p in parts)
    scores = [int(p.get("score") or 0) for p in parts]
    score = min(scores) if passed else max(25, min(scores) if scores else 0)
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


async def verify_behavior_bundle_workspace(workspace_path: str) -> Dict[str, Any]:
    from .verification_rbac import verify_rbac_enforcement_workspace
    from .verification_payment_replay import verify_payment_replay_workspace
    from .verification_tenancy_smoke import verify_tenancy_smoke_workspace

    payment_webhook = verify_payment_replay_workspace(workspace_path or "")
    tenancy = await verify_tenancy_smoke_workspace(workspace_path or "")
    rbac = await verify_rbac_enforcement_workspace(workspace_path or "")
    return merge_verification_results([payment_webhook, tenancy, rbac])
