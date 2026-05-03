"""Hard completion enforcement: critical features, claims, classifications; optional strict block."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

from .claim_parser import merge_claims, read_workspace_claim_corpus
from .critical_registry import CRITICAL_REGISTRY_VERSION, matching_features
from .proof_hierarchy import (
    PROOF_RULESET_VERSION,
    RANK,
    min_rank_for_feature,
    strength_for_flat_item,
)
from .test_signals import critical_skip_violations, skip_checks_from_flat

logger = logging.getLogger(__name__)

ENFORCEMENT_LAYER_VERSION = "1.0.0"
_ENV_GATE = "CRUCIBAI_ENFORCEMENT_GATE"


def _gate_mode() -> str:
    # Default strict — enforcement is a hard gate, not advisory.
    # Override with CRUCIBAI_ENFORCEMENT_GATE=advisory (dev only) or =off (never in prod).
    v = (os.environ.get(_ENV_GATE) or "strict").strip().lower()
    if v in ("strict", "advisory", "off"):
        return v
    return "strict"


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def parse_delivery_sections(workspace_path: str) -> Dict[str, str]:
    if not workspace_path:
        return {}
    p = os.path.join(workspace_path, "proof", "DELIVERY_CLASSIFICATION.md")
    raw = _read_text(p)
    if not raw.strip():
        return {}
    sections: Dict[str, str] = {}
    cur: Optional[str] = None
    buf: List[str] = []
    header_re = re.compile(r"^##\s+(Implemented|Mocked|Stubbed|Unverified)\s*$", re.I)
    for line in raw.splitlines():
        m = header_re.match(line.strip())
        if m:
            if cur:
                sections[cur] = "\n".join(buf).lower()
            cur = m.group(1).lower()
            buf = []
        else:
            buf.append(line)
    if cur:
        sections[cur] = "\n".join(buf).lower()
    return sections


def mocked_claimed_as_implemented(
    sections: Dict[str, str], flat: List[Dict[str, Any]]
) -> List[str]:
    issues: List[str] = []
    impl = sections.get("implemented") or ""
    mocked = sections.get("mocked") or ""
    skips = skip_checks_from_flat(flat)
    payment_verification_skipped = "payment_webhook_replay_skipped" in skips
    if (
        "paypal" in impl or "payment" in impl
    ) and payment_verification_skipped:
        issues.append(
            "Implemented mentions payment integration but webhook verification was skipped - classify as Mocked/Unverified"
        )
    if re.search(r"\breal\s+(paypal|payments?)\b", impl) and (
        "mock" in mocked or payment_verification_skipped
    ):
        issues.append(
            "Implemented claims real payments but evidence shows mock or skipped verification"
        )
    if "auth" in impl and "production" in impl and "rbac_smoke_skipped" in skips:
        issues.append("Production auth claimed but RBAC smoke was skipped")
    return issues


def _evaluate_feature(
    feat, flat: List[Dict[str, Any]], bundle: Dict[str, List]
) -> Dict[str, Any]:
    sat_set = {c.lower() for c in feat.satisfying_checks}
    neg_set = {c.lower() for c in feat.negative_checks}
    max_r = 0
    max_name = "presence"
    sat = False
    neg = False

    for item in flat:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        check = (payload.get("check") or "").lower()
        title = (item.get("title") or "").lower()
        st_name, rank = strength_for_flat_item(item)
        relevant = False
        if check in sat_set or check in neg_set:
            relevant = True
        if feat.id == "core_api_behavior" and check in (
            "health_endpoint",
            "health_path_literal",
        ):
            relevant = True
        if feat.id == "tenant_isolation" and check == "tenancy_isolation_proven":
            relevant = True
        if feat.id in ("auth", "rbac") and check in (
            "rbac_anonymous_blocked",
            "rbac_escalation_blocked",
        ):
            relevant = True
        if (
            feat.id == "integration_behavior"
            and check
            in ("payment_webhook_idempotency_proven",)
        ):
            relevant = True
        if feat.id == "security_controls" and check == "npm_audit":
            relevant = True
            if payload.get("skipped") is True:
                rank = min(rank, RANK.get("syntax", 2))
        if feat.presence_hint_substrings and any(
            h in title for h in feat.presence_hint_substrings
        ):
            relevant = True

        if relevant and rank > max_r:
            max_r = rank
            max_name = st_name
        if check in sat_set or (
            feat.id == "core_api_behavior" and check == "health_endpoint"
        ):
            sat = True
        if check in neg_set:
            neg = True

    issues: List[str] = []
    skip_checks = {c.lower() for c in feat.skip_signal_checks}
    flat_skips = skip_checks_from_flat(flat)
    skipped_hit = bool(skip_checks & flat_skips)

    if skipped_hit and not feat.allow_skipped:
        issues.append(
            f"{feat.name}: verification path skipped (proof contains *_skipped for this area)"
        )

    if not skipped_hit:
        if feat.must_have_runtime_execution and max_r < RANK["runtime"]:
            issues.append(
                f"{feat.name}: requires runtime-level proof (max strength {max_name} rank {max_r}, need >= runtime)"
            )
        if feat.must_have_negative_test and not neg:
            issues.append(f"{feat.name}: requires negative/denial proof (none found)")
        req = min_rank_for_feature(feat.required_proof_classes)
        if max_r < req:
            issues.append(
                f"{feat.name}: proof strength below required (rank {max_r}, need >= {req})"
            )

    if feat.id == "core_api_behavior":
        routes = bundle.get("routes") or []
        if len(routes) >= 1 and not any(
            (it.get("payload") or {}).get("check")
            in ("health_endpoint", "health_path_literal")
            for it in flat
        ):
            issues.append(
                "core_api_behavior: routes recorded without health/API execution proof"
            )

    passed = len(issues) == 0
    return {
        "id": feat.id,
        "name": feat.name,
        "passed": passed,
        "issues": issues,
        "max_proof_rank": max_r,
        "max_proof_name": max_name,
        "satisfying_hit": sat,
        "negative_hit": neg,
        "skipped_signal": skipped_hit,
        "classification": "Implemented" if passed else "Unverified",
    }


def _claim_blocks(
    claims: List[str], flat: List[Dict[str, Any]], scoped_ids: Set[str]
) -> List[str]:
    issues: List[str] = []
    checks = {((item.get("payload") or {}).get("check") or "").lower() for item in flat}
    if "production_ready" in claims:
        if (
            "tenant_isolation" in scoped_ids
            and "tenancy_isolation_proven" not in checks
        ):
            issues.append("Claim production-ready: tenant isolation not proven")
        if "auth" in scoped_ids and "rbac_anonymous_blocked" not in checks:
            issues.append("Claim production-ready: anonymous auth boundary not proven")
    if "tenant_safe" in claims and "tenancy_isolation_proven" not in checks:
        issues.append("Claim tenant-safe: missing tenancy_isolation_proven")
    if "integration_complete" in claims and "integration_behavior" in scoped_ids:
        if (
            "payment_webhook_idempotency_proven" not in checks
        ):
            issues.append(
                "Claim integration complete: missing webhook/idempotency proof"
            )
    if "secure_auth" in claims and ("auth" in scoped_ids or "rbac" in scoped_ids):
        if (
            "rbac_anonymous_blocked" not in checks
            and "rbac_escalation_blocked" not in checks
        ):
            issues.append("Claim secure auth: missing RBAC negative proof")
    return issues


def evaluate_enforcement(
    workspace_path: str,
    goal: str,
    flat: List[Dict[str, Any]],
    bundle: Dict[str, List],
) -> Dict[str, Any]:
    mode = _gate_mode()
    corpus = read_workspace_claim_corpus(workspace_path or "")
    claims = merge_claims(goal or "", corpus)
    feats = matching_features(goal or "", claims, bundle or {})
    scoped_ids = {f.id for f in feats}

    feature_skip_map = {f.id: {c.lower() for c in f.skip_signal_checks} for f in feats}
    skip_issues = critical_skip_violations(flat, workspace_path or "", feature_skip_map)

    sections = parse_delivery_sections(workspace_path or "")
    class_issues = mocked_claimed_as_implemented(sections, flat)
    if not sections and feats:
        class_issues.append(
            "Missing proof/DELIVERY_CLASSIFICATION.md — cannot validate classifications"
        )

    per_feature = [_evaluate_feature(f, flat, bundle or {}) for f in feats]
    feat_issues = [i for pf in per_feature for i in pf["issues"]]
    claim_issues = _claim_blocks(claims, flat, scoped_ids)
    all_issues = skip_issues + class_issues + claim_issues + feat_issues

    # Merge UX audit issues — always block regardless of mode
    if ux_audit_issues:
        all_issues = ux_audit_issues + all_issues
        advisory_would_block = True

    advisory_would_block = len(all_issues) > 0
    if mode == "off":
        blocked = False
    elif mode == "advisory":
        blocked = bool(ux_audit_issues)  # UX hallucination always blocks even in advisory
    else:
        blocked = advisory_would_block

    return {
        "enforcement_layer_version": ENFORCEMENT_LAYER_VERSION,
        "critical_registry_version": CRITICAL_REGISTRY_VERSION,
        "proof_ruleset_version": PROOF_RULESET_VERSION,
        "gate_mode": mode,
        "blocked": blocked,
        "advisory_would_block": advisory_would_block,
        "issues": all_issues,
        "claims_detected": claims,
        "features_in_scope": sorted(scoped_ids),
        "per_feature": per_feature,
        "delivery_sections_present": bool(sections),
        "downgraded_claims": False,
    }


def write_enforcement_artifacts(workspace_path: str, result: Dict[str, Any]) -> None:
    if not workspace_path or not os.path.isdir(workspace_path):
        return
    proof_dir = os.path.join(workspace_path, "proof")
    os.makedirs(proof_dir, exist_ok=True)
    md_path = os.path.join(proof_dir, "ENFORCEMENT_REPORT.md")
    js_path = os.path.join(proof_dir, "ENFORCEMENT_REPORT.json")
    lines = [
        "# Enforcement report",
        "",
        f"- Layer: `{result.get('enforcement_layer_version')}` | Registry: `{result.get('critical_registry_version')}`",
        f"- Gate mode: **{result.get('gate_mode')}** | CRITICAL BLOCK: **{'YES' if result.get('blocked') else 'NO'}**",
        f"- Would block (advisory signal): **{'YES' if result.get('advisory_would_block') else 'NO'}**",
        "",
        "## Claims",
        "",
    ]
    for c in result.get("claims_detected") or []:
        lines.append(f"- {c}")
    if not result.get("claims_detected"):
        lines.append("- (none)")
    lines.extend(["", "## Features in scope", ""])
    for fid in result.get("features_in_scope") or []:
        lines.append(f"- {fid}")
    if not result.get("features_in_scope"):
        lines.append("- (none)")
    lines.extend(["", "## Per feature", ""])
    for pf in result.get("per_feature") or []:
        st = "PASS" if pf.get("passed") else "FAIL"
        lines.append(f"### {pf.get('name')} — {st}")
        lines.append(
            f"- Strength: `{pf.get('max_proof_name')}` (rank {pf.get('max_proof_rank')})"
        )
        for iss in pf.get("issues") or []:
            lines.append(f"- {iss}")
        lines.append("")
    lines.extend(["## All issues", ""])
    for iss in result.get("issues") or []:
        lines.append(f"- {iss}")
    if not result.get("issues"):
        lines.append("- (none)")
    try:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        serializable = {k: v for k, v in result.items() if k != "metadata"}
        with open(js_path, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, default=str)
    except OSError as e:
        logger.warning("enforcement: write failed: %s", e)




def _check_ux_audit_grounding(workspace_path: str) -> List[str]:
    """Detect hallucinated UX audits — audits written without reading generated code.
    
    A grounded audit MUST reference actual source file paths. An audit that says
    "I'll assume" or "since the specification doesn't contain any frontend code"
    is fictional and should block delivery.
    """
    issues: List[str] = []
    if not workspace_path:
        return issues
    
    audit_path = os.path.join(workspace_path, "proof", "UX_AUDIT.md")
    if not os.path.exists(audit_path):
        return issues
    
    try:
        with open(audit_path, encoding="utf-8", errors="replace") as fh:
            audit_text = fh.read().lower()
    except OSError:
        return issues
    
    HALLUCINATION_PHRASES = [
        "i'll assume",
        "i will assume",
        "since the specification",
        "since no frontend code",
        "code is not available",
        "assuming the",
        "based on the specification",
        "i cannot see the actual",
        "without access to the code",
        "the specification doesn't contain",
    ]
    
    for phrase in HALLUCINATION_PHRASES:
        if phrase in audit_text:
            issues.append(
                f"UX_AUDIT_HALLUCINATION: UX audit contains '{phrase}' — "
                f"auditor did not read actual generated files. Audit score is invalid."
            )
    
    # Audit must reference at least one source file path
    import re as _re
    has_file_ref = bool(_re.search(r"(src/|client/src/|frontend/src/).+\.(jsx|tsx|js|ts)", audit_text))
    if not has_file_ref and len(audit_text) > 200:
        issues.append(
            "UX_AUDIT_UNGROUNDED: UX audit contains no source file path references. "
            "The auditor must read actual generated code before scoring."
        )
    
    return issues

async def run_completion_enforcement_gate(
    *,
    job_id: str,
    workspace_path: str,
    goal: str,
    db_pool=None,
    job_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # UX audit grounding check — must run before any other evaluation
    ux_audit_issues = _check_ux_audit_grounding(workspace_path)

    flat: List[Dict[str, Any]] = []
    bundle: Dict[str, List] = {
        k: []
        for k in ("files", "routes", "database", "verification", "deploy", "generic")
    }
    if db_pool is not None and job_id:
        try:
            from backend.proof import proof_service

            proof_service.set_pool(db_pool)
            data = await proof_service.get_proof(job_id)
            b = data.get("bundle") or {}
            for k in bundle:
                bundle[k] = b.get(k) or []
            for lst in bundle.values():
                for row in lst or []:
                    flat.append(row)
        except Exception:
            logger.exception("enforcement gate: get_proof failed")

    result = evaluate_enforcement(workspace_path or "", goal or "", flat, bundle)
    write_enforcement_artifacts(workspace_path or "", result)

    meta: Dict[str, Any] = {
        "enforcement_layer_version": ENFORCEMENT_LAYER_VERSION,
        "critical_registry_version": CRITICAL_REGISTRY_VERSION,
        "proof_ruleset_version": PROOF_RULESET_VERSION,
        "enforcement_gate_mode": result.get("gate_mode"),
        "hard_gate_blocked": result.get("blocked"),
        "advisory_would_block": result.get("advisory_would_block"),
    }
    try:
        from backend.orchestration.execution_authority import (
            attach_elite_context_to_job,
            elite_job_metadata,
        )

        jd = dict(job_dict or {})
        attach_elite_context_to_job(jd, workspace_path or "")
        meta.update(elite_job_metadata(jd))
    except Exception:
        meta["elite_mode_active"] = None
        meta["elite_prompt_sha16"] = None

    result["metadata"] = meta
    return result

