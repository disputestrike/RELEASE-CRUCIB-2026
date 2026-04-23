"""Extract capability claims from goal and workspace text; match against proof."""

from __future__ import annotations

import re
from typing import Dict, List, Set

# id -> regex (case insensitive)
CLAIM_PATTERNS: Dict[str, re.Pattern] = {
    "production_ready": re.compile(
        r"\bproduction[-\s]?ready\b|\bship(ping)?\s+to\s+prod\b",
        re.I,
    ),
    "tenant_safe": re.compile(
        r"\btenant[-\s]?safe\b|\bdata\s+isolation\b|\bno\s+cross[-\s]?tenant\b",
        re.I,
    ),
    "secure_auth": re.compile(
        r"\bsecure\s+auth\b|\benterprise\s+auth\b|\bmfa\b|\bstrong\s+authentication\b",
        re.I,
    ),
    "policy_enforced": re.compile(
        r"\bpolicy\s+enforced\b|\benforced\s+by\s+rbac\b|\brbac\s+enforced\b",
        re.I,
    ),
    "integration_complete": re.compile(
        r"\bintegration\s+complete\b|\breal\s+stripe\b|\blive\s+payments\b",
        re.I,
    ),
    "deployment_ready": re.compile(
        r"\bdeployment\s+ready\b|\bready\s+to\s+deploy\b",
        re.I,
    ),
}


def active_claim_ids(text: str) -> List[str]:
    if not (text or "").strip():
        return []
    out: List[str] = []
    for cid, rx in CLAIM_PATTERNS.items():
        if rx.search(text):
            out.append(cid)
    return out


def merge_claims(*texts: str) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for t in texts:
        for cid in active_claim_ids(t or ""):
            if cid not in seen:
                seen.add(cid)
                ordered.append(cid)
    return ordered


def read_workspace_claim_corpus(workspace_path: str, max_chars: int = 120_000) -> str:
    """Concatenate goal-relevant files for claim scanning."""
    import os

    if not workspace_path or not os.path.isdir(workspace_path):
        return ""
    parts: List[str] = []
    rels = [
        "README.md",
        "readme.md",
        "proof/DELIVERY_CLASSIFICATION.md",
        "proof/STATUS.md",
    ]
    for rel in rels:
        p = os.path.join(workspace_path, rel.replace("/", os.sep))
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    parts.append(fh.read())
            except OSError:
                pass
        if sum(len(x) for x in parts) >= max_chars:
            break
    blob = "\n\n".join(parts)
    return blob[:max_chars]
