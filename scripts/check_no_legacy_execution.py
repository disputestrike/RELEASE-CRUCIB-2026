#!/usr/bin/env python3
"""Fail fast if legacy execution modules or symbols reappear.

This script is intended for CI/pre-merge enforcement.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

DELETED_FILES = {
    Path("backend/orchestration/dag_engine.py"),
    Path("backend/orchestration/auto_runner.py"),
    Path("backend/orchestration/agent_orchestrator.py"),
    Path("backend/agent_orchestrator.py"),
}

FORBIDDEN_MODULES = {
    "backend.orchestration.dag_engine",
    "backend.orchestration.auto_runner",
    "backend.orchestration.agent_orchestrator",
    "backend.agent_orchestrator",
    "orchestration.dag_engine",
    "orchestration.auto_runner",
    "orchestration.agent_orchestrator",
    "agent_orchestrator",
}

FORBIDDEN_SYMBOLS = {
    "build_dag_from_plan",
    "run_job_to_completion",
    "run_auto_runner",
    "_background_auto_runner_job",
    "is_runtime_active",
}

TEXT_FORBIDDEN = {
    "agent_orchestrator",
    "auto_runner",
    "dag_engine",
    "build_dag_from_plan",
    "run_job_to_completion",
    "run_auto_runner",
    "_background_auto_runner_job",
}

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".pytest_cache_backend",
    ".venv",
    "venv",
}

SKIP_FILE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".wav",
    ".sqlite",
    ".db",
    ".pyc",
}

ENFORCED_PATH_PREFIXES = (
    Path("backend"),
    Path("scripts"),
    Path(".github/workflows"),
)

ENFORCED_BASENAMES = {
    "mypy.ini",
}

# This file intentionally names forbidden symbols; skip it for text scans.
SELF_PATH = Path("scripts/check_no_legacy_execution.py")

# Execution-critical modules expected to use centralized authority guard.
REQUIRED_AUTHORITY_FILES = {
    Path("backend/tool_executor.py"),
    Path("backend/agents/base_agent.py"),
    Path("backend/services/llm_service.py"),
    Path("backend/services/runtime/runtime_engine.py"),
}


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        if path.suffix.lower() in SKIP_FILE_SUFFIXES:
            continue
        yield path


def _is_enforced_path(rel: Path) -> bool:
    if rel.name in ENFORCED_BASENAMES:
        return True
    return any(rel == prefix or prefix in rel.parents for prefix in ENFORCED_PATH_PREFIXES)


def _scan_python_ast(path: Path, text: str, violations: list[str]) -> None:
    rel = path.relative_to(ROOT)
    try:
        tree = ast.parse(text, filename=str(rel))
    except SyntaxError as exc:
        violations.append(f"{rel}: parse error during guard scan: {exc}")
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES:
                    violations.append(
                        f"{rel}:{getattr(node, 'lineno', '?')}: forbidden import {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_MODULES:
                violations.append(
                    f"{rel}:{getattr(node, 'lineno', '?')}: forbidden from-import {mod}"
                )
            for alias in node.names:
                if alias.name in FORBIDDEN_SYMBOLS:
                    violations.append(
                        f"{rel}:{getattr(node, 'lineno', '?')}: forbidden symbol import {alias.name}"
                    )
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_SYMBOLS:
                violations.append(
                    f"{rel}:{getattr(node, 'lineno', '?')}: forbidden symbol {node.id}"
                )


def main() -> int:
    violations: list[str] = []

    for rel in DELETED_FILES:
        if (ROOT / rel).exists():
            violations.append(f"{rel}: deleted legacy module exists")

    for req in REQUIRED_AUTHORITY_FILES:
        full = ROOT / req
        if not full.exists():
            violations.append(f"{req}: required authority file missing")
            continue
        text = full.read_text(encoding="utf-8", errors="replace")
        if "require_runtime_authority" not in text:
            violations.append(f"{req}: missing require_runtime_authority usage")

    for path in _iter_files(ROOT):
        rel = path.relative_to(ROOT)
        if not _is_enforced_path(rel):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")

        if rel == SELF_PATH:
            # AST scan still applies for self to prevent accidental bad imports.
            if path.suffix == ".py":
                _scan_python_ast(path, text, violations)
            continue

        if path.suffix == ".py":
            _scan_python_ast(path, text, violations)

        lowered = text.lower()
        for token in TEXT_FORBIDDEN:
            if token in lowered:
                violations.append(f"{rel}: forbidden text reference '{token}'")

    if violations:
        print("LEGACY EXECUTION GUARD: FAIL")
        for item in sorted(set(violations)):
            print(f" - {item}")
        return 1

    print("LEGACY EXECUTION GUARD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
