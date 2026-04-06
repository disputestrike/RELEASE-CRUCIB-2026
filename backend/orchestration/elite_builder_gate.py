"""
Elite builder delivery gate: classifications, critical keywords, presence-vs-runtime heuristics.

Env:
  CRUCIBAI_ELITE_BUILDER_GATE — strict | advisory | off (default: strict for new DAG).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .verifier import _proof_item, _result

_GATE_ENV = "CRUCIBAI_ELITE_BUILDER_GATE"


def _gate_mode() -> str:
    v = (os.environ.get(_GATE_ENV) or "strict").strip().lower()
    if v in ("strict", "advisory", "off"):
        return v
    return "strict"


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _delivery_classification_ok(text: str) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    required = ("Implemented", "Mocked", "Stubbed", "Unverified")
    for label in required:
        if label not in text:
            issues.append(f"proof/DELIVERY_CLASSIFICATION.md must mention '{label}'")
    if re.search(r"\bproduction[- ]ready\b", text, re.I) and "Unverified" not in text:
        issues.append("Claims production-ready without an Unverified section")
    return len(issues) == 0, issues


def _goal_suggests_critical(goal: str) -> List[str]:
    g = (goal or "").lower()
    tags: List[str] = []
    if any(x in g for x in ("tenant", "multi-tenant", "rls", "row-level")):
        tags.append("tenancy")
    if any(x in g for x in ("stripe", "payment", "checkout")):
        tags.append("payments")
    if any(x in g for x in ("auth", "rbac", "jwt", "oauth", "login")):
        tags.append("auth")
    if any(x in g for x in ("encrypt", "aes", "dek", "kek", "crypto")):
        tags.append("crypto")
    return tags


def _critical_runtime_evidence(text: str, tags: List[str]) -> Tuple[bool, List[str]]:
    """
    Presence-only patterns are insufficient for critical tags: require hints of runtime/test proof.
    """
    if not tags:
        return True, []
    tlow = text.lower()
    issues: List[str] = []
    if "tenancy" in tags:
        ok = any(
            x in tlow
            for x in (
                "tenancy_isolation",
                "pytest",
                "test_",
                "runtime",
                "smoke",
                "isolation",
            )
        )
        if not ok:
            issues.append(
                "Tenancy-related goal: DELIVERY_CLASSIFICATION or TEST_RESULTS should reference "
                "runtime/smoke/pytest evidence — structure-only mention of RLS is insufficient."
            )
    if "payments" in tags:
        ok = "mock" in tlow or "stripe" in tlow and ("webhook" in tlow or "test" in tlow)
        if not ok:
            issues.append("Payments-related goal: document Mocked keys or webhook test path in classification.")
    if "auth" in tags:
        ok = "mock" in tlow or "jwt" in tlow or "demo" in tlow or "stub" in tlow
        if not ok:
            issues.append("Auth-related goal: classify auth as Implemented/Mocked/Stubbed explicitly.")
    return len(issues) == 0, issues


async def verify_elite_builder_workspace(
    workspace_path: str,
    *,
    job_goal: str = "",
) -> Dict[str, Any]:
    mode = _gate_mode()
    proof: List[Dict[str, Any]] = []
    issues: List[str] = []

    if mode == "off":
        return _result(
            True,
            100,
            [],
            [
                _proof_item(
                    "generic",
                    "Elite builder gate off",
                    {"gate": "off"},
                    verification_class="presence",
                )
            ],
        )

    elite_path = os.path.join(workspace_path, "proof", "ELITE_EXECUTION_DIRECTIVE.md")
    elite_txt = _read_text(elite_path) if workspace_path else None
    if not (elite_txt or "").strip():
        issues.append("Missing proof/ELITE_EXECUTION_DIRECTIVE.md — elite execution authority not materialized")
    else:
        proof.append(
            _proof_item(
                "file",
                "Elite directive present",
                {"path": "proof/ELITE_EXECUTION_DIRECTIVE.md", "elite_materialized": True},
                verification_class="presence",
            )
        )

    dc_path = os.path.join(workspace_path, "proof", "DELIVERY_CLASSIFICATION.md")
    dc = _read_text(dc_path) if workspace_path else None
    if not (dc or "").strip():
        issues.append("Missing proof/DELIVERY_CLASSIFICATION.md")
    else:
        ok_dc, dc_issues = _delivery_classification_ok(dc)
        if not ok_dc:
            issues.extend(dc_issues)
        proof.append(
            _proof_item(
                "verification",
                "Delivery classification file",
                {"path": "proof/DELIVERY_CLASSIFICATION.md", "checks": "four_labels"},
                verification_class="syntax",
            )
        )
        crit_tags = _goal_suggests_critical(job_goal)
        ok_crit, crit_issues = _critical_runtime_evidence(dc, crit_tags)
        if not ok_crit:
            issues.extend(crit_issues)
            proof.append(
                _proof_item(
                    "verification",
                    "Critical feature proof depth",
                    {"tags": crit_tags, "presence_only_insufficient": True},
                    verification_class="runtime",
                )
            )

    passed = len(issues) == 0
    if mode == "advisory" and not passed:
        proof.append(
            _proof_item(
                "verification",
                "Elite builder gate (advisory)",
                {"issues": issues, "would_fail_in_strict": True},
                verification_class="runtime",
            )
        )
        return _result(True, 72, [], proof)

    score = 100 if passed else max(0, 100 - len(issues) * 18)
    return _result(passed, score, issues, proof)
