"""
Production sketch gate — cheap static checks before deploy steps (not full SAST).
"""
from __future__ import annotations

import os
import re
from typing import List, Tuple

# High-confidence patterns only (avoid flagging docs that say "sk_live_...")
_SECRET_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"sk_live_[0-9a-zA-Z]{20,}"), "Stripe live secret key material"),
    (re.compile(r"rk_live_[0-9a-zA-Z]{20,}"), "Stripe live restricted key material"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"ghp_[0-9a-zA-Z]{30,}"), "GitHub personal access token"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z-]{20,}"), "Slack token pattern"),
]

_SKIP_NAMES = {".env", ".pem", ".p12", ".key"}
_SKIP_SUFFIX = (".png", ".jpg", ".woff", ".woff2", ".ico", ".map")


def scan_workspace_for_credential_patterns(
    workspace_path: str,
    *,
    max_files: int = 60,
    max_bytes: int = 12000,
) -> List[str]:
    """
    Walk workspace text files; return human-readable hit lines (no secret values echoed).
    """
    issues: List[str] = []
    if not workspace_path or not os.path.isdir(workspace_path):
        return issues
    skip_dir = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    n = 0
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in skip_dir]
        for name in files:
            if n >= max_files:
                return issues
            low = name.lower()
            if any(low.endswith(s) for s in _SKIP_SUFFIX):
                continue
            if low in _SKIP_NAMES or name.startswith(".env"):
                continue
            if not low.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".sql", ".yml", ".yaml", ".toml")):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    text = fh.read(max_bytes)
            except OSError:
                continue
            n += 1
            for rx, label in _SECRET_PATTERNS:
                if rx.search(text):
                    issues.append(f"{label} pattern matched in {rel} — remove before production")
                    break
    return issues
