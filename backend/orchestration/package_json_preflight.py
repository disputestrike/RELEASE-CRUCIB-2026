"""Lightweight package.json checks before npm install (continuity gate)."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def validate_package_json_for_install(pkg: Dict[str, Any]) -> List[str]:
    """Return human-readable issues; empty list means proceed to npm install."""
    issues: List[str] = []
    if not isinstance(pkg, dict):
        return ["package.json root must be a JSON object"]

    name = pkg.get("name")
    if name is not None and not isinstance(name, (str, int, float)):
        issues.append("package.json: invalid package name type")

    for section in ("dependencies", "devDependencies", "peerDependencies"):
        block = pkg.get(section)
        if block is None:
            continue
        if not isinstance(block, dict):
            issues.append(f"package.json: {section} must be an object")
            continue
        for dep_name, ver in block.items():
            if not isinstance(ver, str):
                issues.append(
                    f"package.json: {section}.{dep_name} version must be a string"
                )
                continue
            v = ver.strip()
            if not v:
                issues.append(f"package.json: {section}.{dep_name} has empty version")
                continue
            if v.startswith("file:") or v.startswith("link:") or v.startswith("git+"):
                continue
            if v.startswith("http://") or v.startswith("https://"):
                continue
            if v in ("*", "latest", "x", "X"):
                issues.append(
                    f"package.json: {section}.{dep_name} uses unbounded version {v!r} "
                    "(pin a semver range)"
                )
            if re.match(r"^[0-9]{6,}", v):
                issues.append(
                    f"package.json: {section}.{dep_name} has implausible semver {v[:48]!r}"
                )

    return issues
