"""Permission rule linter — detects shadowed / redundant allow rules.

Adapted from claude-code-source-code/src/utils/permissions/shadowedRuleDetection.ts.

A rule `Bash(npm:*)` shadows `Bash(npm install:*)` — the broader rule already
permits everything the narrower one does, so the narrower one is dead code.
Flagging these at authoring time prevents surprising-but-legal commands from
slipping past policy review.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class Shadowed:
    shadowed: str
    by: str
    reason: str


def lint_rules(rules: Sequence[str]) -> List[Shadowed]:
    """Return the list of rules that are made redundant by another rule.

    Rule syntax mirrors the TS original: `Tool(prefix[:pattern])`, where patterns
    use `*` for match-anything. Exact strings shadow nothing. A wildcard rule
    shadows any stricter rule that starts with the same prefix.
    """
    findings: List[Shadowed] = []
    parsed = [(_parse(r), r) for r in rules]
    for i, ((tool_a, match_a, wild_a), src_a) in enumerate(parsed):
        if not wild_a:
            continue
        for j, ((tool_b, match_b, wild_b), src_b) in enumerate(parsed):
            if i == j or tool_a != tool_b:
                continue
            if match_b.startswith(match_a) and match_b != match_a:
                findings.append(Shadowed(shadowed=src_b, by=src_a,
                                         reason=f"{src_a} already permits {src_b}'s prefix"))
    return findings


def _parse(rule: str) -> tuple[str, str, bool]:
    """Split rule "Tool(match)" into (tool, match-without-wildcards, is_wildcard)."""
    if "(" in rule and rule.endswith(")"):
        tool, inner = rule.split("(", 1)
        inner = inner[:-1]
    else:
        tool, inner = "", rule
    is_wild = inner.endswith(":*") or inner.endswith("*")
    match = inner.rstrip("*").rstrip(":").strip()
    return tool.strip(), match, is_wild
