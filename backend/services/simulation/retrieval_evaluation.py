"""Post-hoc checks tying retrieval_debug, sources, and Output Answer together (evaluation / CI hooks)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


_URL_RE = re.compile(r"https?://[^\s\)\]\>\"<>]+", re.I)


def extract_urls_from_text(text: str) -> List[str]:
    if not text:
        return []
    return list(dict.fromkeys(_URL_RE.findall(text)))


def source_urls_retrieved(sources: Sequence[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for s in sources or []:
        u = str(s.get("url") or "").strip()
        if u.startswith("http"):
            out.append(u)
    return list(dict.fromkeys(out))


def coherence_violations(
    *,
    output_answer: Dict[str, Any],
    retrieval_debug: Dict[str, Any],
    sources: Sequence[Dict[str, Any]],
    require_url_citation_when_gate_passes: bool = True,
) -> List[str]:
    """
    Returns human-readable violation strings (empty list => OK for the checks enabled).

    These are guardrail signals for golden-run evaluation—not hard API failures.
    """
    violations: List[str] = []
    gate = (retrieval_debug or {}).get("gate") or {}
    exploratory = bool((output_answer or {}).get("exploratory"))
    gate_passed = bool(gate.get("passed", True))
    direct = str((output_answer or {}).get("direct_answer") or "")

    if not gate_passed and not exploratory:
        violations.append("gate_failed_but_output_answer_not_marked_exploratory")

    retrieved = source_urls_retrieved(sources)
    cited = set(extract_urls_from_text(direct))
    overlap = cited.intersection(set(retrieved))

    if (
        require_url_citation_when_gate_passes
        and gate_passed
        and not exploratory
        and retrieved
        and not overlap
        and "http" not in direct.lower()
    ):
        violations.append("gate_passed_non_exploratory_but_no_retrieved_source_url_in_direct_answer")

    return violations
