"""
Zero-Placeholder Enforcer (ZPE) — Phase 1 of CrucibAI Master Plan 2026.

Every line of generated code must be production-ready. No scaffolds,
stubs, mocks, or hardcoded dummy values escape the build pipeline.

This module is intentionally strict. If something looks unfinished,
it is rejected and queued for repair before the user ever sees it.

Usage:
    from backend.agents.validators.zero_placeholder_enforcer import ZeroPlaceholderEnforcer
    report = ZeroPlaceholderEnforcer(workspace_path).scan()
    if not report["passed"]:
        # route to repair agent
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# File extensions treated as source code (checked for placeholders)
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml",
    ".sql", ".sh", ".toml", ".env.example",
}

# Directories to skip during scanning
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".next", "coverage", ".pytest_cache",
    "migrations",  # auto-generated Alembic files OK
}

# Max file size to scan (bytes) — skip large binaries
MAX_FILE_BYTES = 500_000


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

@dataclass
class PlaceholderRule:
    """A single detection rule."""
    id: str
    severity: str          # "blocker" | "warning"
    description: str
    pattern: re.Pattern
    skip_extensions: set = field(default_factory=set)
    skip_if_comment: bool = False  # skip if whole match is inside a comment
    example: str = ""


def _r(pattern: str, flags: int = re.IGNORECASE) -> re.Pattern:
    return re.compile(pattern, flags)


PLACEHOLDER_RULES: List[PlaceholderRule] = [
    # ── Unfinished implementation markers ──────────────────────────────────
    PlaceholderRule(
        id="todo_replace",
        severity="blocker",
        description="TODO / FIXME marked for replacement in production code",
        pattern=_r(r"\b(TODO|FIXME|HACK|XXX)\s*:?\s*(replace|implement|add|fix|complete|finish|fill|insert|put|change|update)\b"),
        example="# TODO: replace with real auth logic",
    ),
    PlaceholderRule(
        id="not_implemented",
        severity="blocker",
        description="raise NotImplementedError without overriding comment",
        pattern=_r(r"raise\s+NotImplementedError\b"),
        skip_extensions={".md"},
        example="raise NotImplementedError",
    ),
    PlaceholderRule(
        id="placeholder_string",
        severity="blocker",
        description="Literal placeholder/stub/scaffold string in code",
        pattern=_r(
            r"""['"](your[_\- ]?(api[_\- ]?key|secret|token|password|domain|email|name|company)[_\- ]?here|"""
            r"""placeholder[_\- ]?(value|text|content)|"""
            r"""insert[_\- ]?(your|here)|"""
            r"""change[_\- ]?this|"""
            r"""example\.(com|org|io|net)['"]\s*(?:#|//|<!--|$)|"""  # example.com only suspicious at EOL/comment
            r"""REPLACE_ME|CHANGEME|YOUR_[A-Z_]+_HERE)['"]"""
        ),
        example='"your_api_key_here"',
    ),
    PlaceholderRule(
        id="scaffold_comment",
        severity="blocker",
        description="Scaffold / generated module placeholder comment",
        pattern=_r(
            r"""(crucib_incomplete|"""
            r"""generated module placeholder|"""
            r"""TODO:\s*replace this with real|"""
            r"""your_app_name_here|"""
            r"""configure cmd for your app|"""
            r"""real test placeholder|"""
            r"""application is being generated\.\s*please wait|"""
            r"""sample team page|"""
            r"""included in the scaffold|"""
            r"""\"_placeholder\":\s*\"generated\")"""
        ),
        example="# crucib_incomplete",
    ),

    # ── Hardcoded dummy credentials ────────────────────────────────────────
    PlaceholderRule(
        id="dummy_credential",
        severity="blocker",
        description="Hardcoded dummy/test credential in non-test source file",
        pattern=_r(
            r"""(password\s*[=:]\s*['"](password|Password123|admin|1234|test|dummy|fake|secret|pass123|changeme|letmein)['"]|"""
            r"""secret_key\s*[=:]\s*['"](secret|supersecret|dev-secret|change-me|your-secret-key|changethis|devsecret)['"]|"""
            r"""api_key\s*[=:]\s*['"](fake|dummy|test|placeholder|your.api.key|XXXXXXXX)['"])"""
        ),
        skip_extensions={".md", ".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.py"},
        example='password = "password123"',
    ),
    PlaceholderRule(
        id="localhost_hardcoded",
        severity="warning",
        description="Hardcoded localhost URL in non-config source file",
        pattern=_r(r"""['"](https?://localhost(:\d+)?(/[^'"]*)?|http://127\.0\.0\.1(:\d+)?(/[^'"]*)?)['"]"""),
        skip_extensions={".md", ".env", ".env.example", ".test.js", ".test.ts", ".spec.js", ".spec.ts"},
        example='"http://localhost:3000"',
    ),

    # ── Mock / dummy data patterns ─────────────────────────────────────────
    PlaceholderRule(
        id="mock_data_production",
        severity="warning",
        description="Mock/fake/dummy data object used outside test files",
        pattern=_r(
            r"""(const|let|var|=)\s*(mockData|fakeData|dummyData|sampleData|testData|MOCK_[A-Z_]+)\s*[=:]"""
        ),
        skip_extensions={".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.py", ".test.jsx", ".test.tsx"},
        example="const mockData = { ... }",
    ),

    # ── Empty/pass-only implementations ───────────────────────────────────
    PlaceholderRule(
        id="pass_stub",
        severity="warning",
        description="Function body is only 'pass' (likely stub)",
        pattern=_r(r"""def\s+\w+\([^)]*\)\s*(?:->\s*\w+)?\s*:\s*\n\s+pass\s*$""", re.MULTILINE),
        skip_extensions={".md"},
        example="def process():\n    pass",
    ),
    PlaceholderRule(
        id="empty_catch_block",
        severity="warning",
        description="Empty catch/except block that swallows errors silently",
        pattern=_r(r"""(except\s*(?:\w+\s*)?:\s*\n\s+pass\s*$|catch\s*\([^)]*\)\s*\{\s*\})""", re.MULTILINE),
        skip_extensions={".md"},
        example="except Exception:\n    pass",
    ),

    # ── Incomplete deploy / CI artifacts ──────────────────────────────────
    PlaceholderRule(
        id="placeholder_deploy",
        severity="blocker",
        description="Placeholder command in deploy/CI configuration",
        pattern=_r(
            r"""(echo\s+["']?(your[_\- ]?deploy[_\- ]?command|add your|configure this|replace this|todo|fixme)["']?|"""
            r"""<YOUR[_\- ]?[A-Z_]+>|"""
            r"""\$\{YOUR_[A-Z_]+\})"""
        ),
        example='echo "your deploy command here"',
    ),
]


# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    rule_id: str
    severity: str       # "blocker" | "warning"
    file_path: str
    line_number: int
    line_content: str
    description: str
    match_text: str


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class ZeroPlaceholderEnforcer:
    """
    Scans a generated workspace for placeholder patterns.

    Args:
        workspace_path: Root of the generated project.
        strict:         If True, warnings are also treated as blockers.
    """

    def __init__(self, workspace_path: str, strict: bool = False):
        self.workspace_path = workspace_path
        self.strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> Dict[str, Any]:
        """
        Scan workspace and return a structured report.

        Returns:
            {
                "passed": bool,
                "blockers": List[Violation],
                "warnings": List[Violation],
                "files_scanned": int,
                "duration_ms": int,
                "summary": str,
            }
        """
        start = time.monotonic()
        blockers: List[Violation] = []
        warnings: List[Violation] = []
        files_scanned = 0

        for filepath in self._iter_source_files():
            ext = Path(filepath).suffix.lower()
            basename = Path(filepath).name.lower()
            # Skip test/spec files for blocker rules (already checked per-rule)
            content = self._read_safe(filepath)
            if content is None:
                continue
            files_scanned += 1
            for rule in PLACEHOLDER_RULES:
                if ext in rule.skip_extensions:
                    continue
                if any(basename.endswith(s) for s in rule.skip_extensions):
                    continue
                self._apply_rule(rule, filepath, content, blockers, warnings)

        if self.strict:
            blockers.extend(warnings)
            warnings = []

        duration_ms = int((time.monotonic() - start) * 1000)
        passed = len(blockers) == 0
        summary = self._build_summary(passed, blockers, warnings, files_scanned, duration_ms)

        return {
            "passed": passed,
            "blockers": [self._violation_dict(v) for v in blockers],
            "warnings": [self._violation_dict(v) for v in warnings],
            "files_scanned": files_scanned,
            "duration_ms": duration_ms,
            "summary": summary,
        }

    def scan_single_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """Scan a single file's content (used by streaming generators)."""
        blockers: List[Violation] = []
        warnings: List[Violation] = []
        ext = Path(filepath).suffix.lower()
        for rule in PLACEHOLDER_RULES:
            if ext in rule.skip_extensions:
                continue
            self._apply_rule(rule, filepath, content, blockers, warnings)
        passed = len(blockers) == 0
        return {
            "passed": passed,
            "blockers": [self._violation_dict(v) for v in blockers],
            "warnings": [self._violation_dict(v) for v in warnings],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_source_files(self):
        """Yield all scannable source files in the workspace."""
        root = Path(self.workspace_path)
        if not root.is_dir():
            return
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            # Skip excluded directories
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in SOURCE_EXTENSIONS and path.name not in {
                "Dockerfile", "Procfile", "Makefile"
            }:
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            yield str(path)

    def _read_safe(self, filepath: str) -> Optional[str]:
        """Read file content, return None on error."""
        try:
            return open(filepath, encoding="utf-8", errors="replace").read()
        except Exception:
            return None

    def _apply_rule(
        self,
        rule: PlaceholderRule,
        filepath: str,
        content: str,
        blockers: List[Violation],
        warnings: List[Violation],
    ) -> None:
        """Apply one rule to file content and append violations."""
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            m = rule.pattern.search(line)
            if not m:
                continue
            v = Violation(
                rule_id=rule.id,
                severity=rule.severity,
                file_path=filepath,
                line_number=i,
                line_content=line.strip()[:120],
                description=rule.description,
                match_text=m.group(0)[:80],
            )
            if rule.severity == "blocker":
                blockers.append(v)
            else:
                warnings.append(v)

    @staticmethod
    def _violation_dict(v: Violation) -> Dict[str, Any]:
        rel = str(v.file_path)
        return {
            "rule_id": v.rule_id,
            "severity": v.severity,
            "file": rel,
            "line": v.line_number,
            "content": v.line_content,
            "description": v.description,
            "match": v.match_text,
        }

    @staticmethod
    def _build_summary(
        passed: bool,
        blockers: List[Violation],
        warnings: List[Violation],
        files_scanned: int,
        duration_ms: int,
    ) -> str:
        status = "PASS ✓" if passed else f"FAIL ✗ ({len(blockers)} blocker(s))"
        return (
            f"[ZPE] {status} | "
            f"files={files_scanned} blockers={len(blockers)} "
            f"warnings={len(warnings)} duration={duration_ms}ms"
        )


# ---------------------------------------------------------------------------
# Convenience wrapper used by executor.py
# ---------------------------------------------------------------------------

def enforce_zero_placeholders(
    workspace_path: str,
    strict: bool = False,
) -> Tuple[bool, str, List[Dict]]:
    """
    Run ZPE scan and return (passed, summary, blocker_list).

    Args:
        workspace_path: Path to the generated project directory.
        strict:         Treat warnings as blockers too.

    Returns:
        (passed: bool, summary: str, blockers: list[dict])
    """
    report = ZeroPlaceholderEnforcer(workspace_path, strict=strict).scan()
    return report["passed"], report["summary"], report["blockers"]
