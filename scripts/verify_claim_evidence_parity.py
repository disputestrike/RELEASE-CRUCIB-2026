"""Fail CI when public copy drifts beyond BUILD_EVIDENCE_MATRIX.md.

This is intentionally conservative. It does not prove every sentence on the
site; it blocks the exact overclaim classes that the evidence matrix marks as
partial or not claimable.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "BUILD_EVIDENCE_MATRIX.md"
PUBLIC_PATHS = [
    ROOT / "frontend" / "src" / "pages",
    ROOT / "frontend" / "src" / "components",
]
SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".md"}


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    allowed_if: tuple[re.Pattern[str], ...] = ()

    def allowed(self, line: str) -> bool:
        return any(pattern.search(line) for pattern in self.allowed_if)


CONDITIONAL_DEPLOY = re.compile(
    r"configured|conditional|provider|token|target|promised where|proof gates|/one-click/",
    re.I,
)
CONDITIONAL_MOBILE = re.compile(
    r"not claimable|requires|guidance|guide|expo source|store proof|credentials|signing|metadata validation",
    re.I,
)
CONDITIONAL_A11Y = re.compile(
    r"roadmap|not claimable|when .*evidence|validator report|where supported|only when",
    re.I,
)

RULES = (
    Rule("unsupported exact agent count", re.compile(r"\b(?:100\+|241)\s+agents?\b", re.I)),
    Rule("unsupported full transparency", re.compile(r"\b(?:fully transparent|no black boxes|every agent decision)\b", re.I)),
    Rule("unsupported universal guarantee", re.compile(r"\b(?:always produces|always runnable|any build|import any code)\b", re.I)),
    Rule("unconditional one-click deploy", re.compile(r"\bone-click deploy(?:ment)?\b", re.I), (CONDITIONAL_DEPLOY,)),
    Rule("automatic store submission", re.compile(r"\b(?:App Store|Google Play|signed IPA|signed AAB)\b", re.I), (CONDITIONAL_MOBILE,)),
    Rule("unproven accessibility check", re.compile(r"\baccessibility check(?:s)?\b", re.I), (CONDITIONAL_A11Y,)),
    Rule("unsupported production-ready claim", re.compile(r"\bproduction-ready\b", re.I), (re.compile(r"not .*production-ready|proof-gated", re.I),)),
    Rule("unsupported enterprise-grade claim", re.compile(r"\benterprise-grade\b", re.I)),
)

SKIP_FILES = {
    ROOT / "frontend" / "src" / "components" / "CompactButton.jsx",
}


def iter_public_files() -> Iterable[Path]:
    for base in PUBLIC_PATHS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in SUFFIXES and path not in SKIP_FILES:
                yield path


def main() -> int:
    if not MATRIX.exists():
        print(f"Missing evidence matrix: {MATRIX}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for path in iter_public_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            failures.append(f"{path}: unable to read: {exc}")
            continue
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                or "{/*" in stripped
            ):
                continue
            for rule in RULES:
                if rule.pattern.search(line) and not rule.allowed(line):
                    rel = path.relative_to(ROOT).as_posix()
                    failures.append(f"{rel}:{lineno}: {rule.name}: {line.strip()[:220]}")

    if failures:
        print("Public claim/evidence parity failed.")
        print("Update copy to match docs/BUILD_EVIDENCE_MATRIX.md or add proof first.")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Public claim/evidence parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
