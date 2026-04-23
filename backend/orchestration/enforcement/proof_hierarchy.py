"""
Proof strength hierarchy (weakest → strongest).

Used to score features and to enforce: presence/syntax alone cannot satisfy critical features.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

PROOF_RULESET_VERSION = "1.0.0"

# Ordered weakest → strongest (1 = weakest)
STRENGTH_ORDER: Tuple[str, ...] = (
    "presence",
    "syntax",
    "static_scan",
    "runtime",
    "behavior_assertion",
    "negative_test",
    "state_transition",
    "e2e",
)

RANK = {name: i + 1 for i, name in enumerate(STRENGTH_ORDER)}


def rank_for_name(name: Optional[str]) -> int:
    if not name:
        return 0
    return RANK.get(name.lower(), 0)


# Map verifier payload.check → minimum strength name it represents
CHECK_STRENGTH: Dict[str, str] = {
    "rls_policies_in_migrations": "presence",
    "tenancy_sql_sketch": "presence",
    "router_mount": "presence",
    "package_json_present": "presence",
    "rls_syntax_valid": "syntax",
    "migrations_read": "syntax",
    "npm_audit": "static_scan",
    "health_path_literal": "syntax",
    "health_endpoint": "runtime",
    "tenancy_smoke_skipped": "presence",
    "rbac_smoke_skipped": "presence",
    "stripe_replay_skipped": "presence",
    "tenancy_isolation_proven": "negative_test",
    "rbac_anonymous_blocked": "negative_test",
    "rbac_escalation_blocked": "negative_test",
    "stripe_webhook_idempotency_proven": "behavior_assertion",
    "stripe_idempotency_sql": "syntax",
    "cors_wildcard": "static_scan",
    "observability_pack_present": "presence",
    "multiregion_terraform_sketch_present": "presence",
}


def strength_for_flat_item(item: Dict[str, Any]) -> Tuple[str, int]:
    """
    Returns (strength_name, rank). Uses payload.verification_class and payload.check.
    """
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    check = (payload.get("check") or "").lower()
    if check in CHECK_STRENGTH:
        name = CHECK_STRENGTH[check]
        return name, RANK[name]
    vc = (payload.get("verification_class") or "").lower()
    if vc in RANK:
        return vc, RANK[vc]
    title = (item.get("title") or "").lower()
    if "api smoke" in title or "smoke test" in title:
        return "runtime", RANK["runtime"]
    if "playwright" in title or "e2e" in title:
        return "e2e", RANK["e2e"]
    pt = (item.get("proof_type") or item.get("type") or "").lower()
    if pt == "compile":
        return "syntax", RANK["syntax"]
    if pt == "test":
        return "behavior_assertion", RANK["behavior_assertion"]
    if pt == "file":
        return "presence", RANK["presence"]
    return "presence", RANK["presence"]


def max_strength_rank_for_feature(
    flat: List[Dict[str, Any]],
    feat_id: str,
    satisfying_checks: Tuple[str, ...],
    negative_checks: Tuple[str, ...],
    presence_hints: Tuple[str, ...],
) -> Tuple[int, str, bool, bool]:
    """
    Returns (max_rank, max_name, has_satisfying_check, has_negative_check).
    """
    max_r = 0
    max_n = "presence"
    sat = False
    neg = False
    sat_set = {c.lower() for c in satisfying_checks}
    neg_set = {c.lower() for c in negative_checks}

    for item in flat:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        check = (payload.get("check") or "").lower()
        title = (item.get("title") or "").lower()
        name, rank = strength_for_flat_item(item)

        if check in sat_set or any(s in title for s in sat_set):
            sat = True
        if check in neg_set or any(n in title for n in neg_set):
            neg = True
        # Scoped relevance: title/hints match feature family
        hint_hit = any(h in title for h in presence_hints)
        generic_strong = rank >= RANK["runtime"] and (
            hint_hit
            or not presence_hints
            or feat_id in ("core_api_behavior", "tenant_isolation", "rbac", "auth")
        )
        if feat_id == "core_api_behavior" and check in (
            "health_endpoint",
            "health_path_literal",
        ):
            generic_strong = True
        if feat_id == "tenant_isolation" and check == "tenancy_isolation_proven":
            generic_strong = True
        if feat_id in ("auth", "rbac") and check in (
            "rbac_anonymous_blocked",
            "rbac_escalation_blocked",
        ):
            generic_strong = True
        if (
            feat_id == "integration_behavior"
            and check == "stripe_webhook_idempotency_proven"
        ):
            generic_strong = True

        if generic_strong or (hint_hit and rank > max_r):
            if rank > max_r:
                max_r = rank
                max_n = name

    return max_r, max_n, sat, neg


def min_rank_for_feature(requirements: Tuple[str, ...]) -> int:
    """required_proof_classes from CriticalFeature → minimum rank required."""
    if not requirements:
        return RANK["runtime"]
    names = [r for r in requirements if r in RANK]
    if not names:
        return RANK["runtime"]
    return max(RANK[n] for n in names)


def presence_syntax_only(max_rank: int) -> bool:
    return max_rank <= max(RANK["syntax"], RANK["static_scan"])
