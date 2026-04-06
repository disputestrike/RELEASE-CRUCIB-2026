"""Detect skipped / deferred critical tests from proof payloads and workspace stubs."""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Set

_SKIP_RE = re.compile(r"\bSKIPPED\b|\bskip(ped)?\b|\bxfail\b|\bnot\s+configured\b|\bmanual\s+only\b|\bdeferred\b", re.I)


def skip_checks_from_flat(flat: List[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for item in flat:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        check = (payload.get("check") or "").lower()
        if check.endswith("_skipped"):
            out.add(check)
        reason = str(payload.get("reason") or "")
        if check and "skip" in reason.lower():
            out.add(check)
    return out


def parse_test_results_file(workspace_path: str) -> List[str]:
    """Lines from proof/TEST_RESULTS.md mentioning skips for critical areas."""
    if not workspace_path:
        return []
    p = os.path.join(workspace_path, "proof", "TEST_RESULTS.md")
    if not os.path.isfile(p):
        return []
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    flagged: List[str] = []
    keywords = ("rbac", "tenant", "tenancy", "auth", "stripe", "webhook", "approval", "isolation")
    for line in lines:
        if not _SKIP_RE.search(line):
            continue
        low = line.lower()
        if any(k in low for k in keywords):
            flagged.append(line.strip()[:200])
    return flagged


def critical_skip_violations(
    flat: List[Dict[str, Any]],
    workspace_path: str,
    feature_skip_checks: Dict[str, Set[str]],
) -> List[str]:
    """
    feature_id -> set of skip check names that imply that feature's verification was skipped.
    """
    from_flat = skip_checks_from_flat(flat)
    issues: List[str] = []
    for feat_id, checks in feature_skip_checks.items():
        for c in checks:
            if c.lower() in from_flat:
                issues.append(f"Critical feature '{feat_id}': verification signaled skip ({c})")
    for line in parse_test_results_file(workspace_path):
        issues.append(f"TEST_RESULTS skip line: {line}")
    return issues
