"""
P4 — Minimal directory layout contracts keyed by `stack_profile` / `recommended_build_target`.

Used for golden validation and future UI hints; does not enforce at runtime yet.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Required paths must exist as files OR directories under workspace root.
_DIRECTORY_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "vite_react": {
        "label": "Vite + React sketch",
        "required_any_of": [["package.json", "index.html"]],
        "required_all_of": [["src"]],
    },
    "api_backend": {
        "label": "Python API sketch",
        "required_any_of": [],
        "required_all_of": [["server.py"]],
    },
    "full_system_generator": {
        "label": "Workspace build (multi-stack)",
        "required_any_of": [["package.json"], ["pyproject.toml"], ["requirements.txt"]],
        "required_all_of": [],
    },
    "next_js": {
        "label": "Next.js (App Router or Pages)",
        "required_any_of": [["package.json"]],
        "required_all_of": [],
        "must_have_subdir_one_of": ["app", "src/app", "pages"],
    },
}


def stack_profile_from_contract(contract: Optional[Dict[str, Any]]) -> str:
    c = contract or {}
    return (
        str(
            c.get("stack_profile") or c.get("recommended_build_target") or "vite_react"
        ).strip()
        or "vite_react"
    )


def directory_profile_from_contract(contract: Optional[Dict[str, Any]]) -> str:
    """P4 — Layout contract profile (Next vs Vite vs API-only)."""
    c = contract or {}
    dp = str(c.get("directory_profile") or "").strip()
    if dp:
        return dp
    return stack_profile_from_contract(c)


def validate_directory_contract(workspace_root: Path, profile: str) -> Dict[str, Any]:
    """
    Returns { "ok": bool, "profile": str, "violations": [str], "checked": [...] }.
    """
    spec = _DIRECTORY_CONTRACTS.get(profile) or _DIRECTORY_CONTRACTS["vite_react"]
    root = workspace_root.resolve()
    violations: List[str] = []
    checked: List[str] = []

    def exists(rel: str) -> bool:
        p = root / rel.replace("/", os.sep)
        checked.append(rel)
        return p.is_file() or p.is_dir()

    for group in spec.get("required_all_of") or []:
        for rel in group:
            if not exists(rel):
                violations.append(f"missing required: {rel}")

    any_of_groups = spec.get("required_any_of") or []
    if any_of_groups:
        for options in any_of_groups:
            if not any(exists(o) for o in options):
                violations.append(f"need one of: {', '.join(options)}")

    subdirs = spec.get("must_have_subdir_one_of") or []
    if subdirs:
        if not any((root / d.replace("/", os.sep)).is_dir() for d in subdirs):
            violations.append(f"need one of directories: {', '.join(subdirs)}")

    return {
        "ok": len(violations) == 0,
        "profile": profile,
        "label": spec.get("label", profile),
        "violations": violations,
        "checked_paths": checked,
    }
