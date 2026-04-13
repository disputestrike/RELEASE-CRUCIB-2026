"""
P1 — Per-step workspace fingerprint diff for job_events (telemetry).

Emits structured added / removed / modified path lists without hashing file bodies
(size + mtime only). Uses the same directory pruning as workspace manifests.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from .workspace_assembly import SKIP_ZIP_DIRS

# Paths are repo-relative under workspace root. Cap walk size for huge trees.
_MAX_SNAPSHOT_FILES = 8000

Fingerprint = Dict[str, Tuple[int, float]]  # rel path -> (size_bytes, mtime_ns)


def snapshot_workspace_fingerprints(workspace_root: Path) -> Fingerprint:
    """Build path → (size, mtime_ns) for regular files under root (pruned)."""
    root = workspace_root.resolve()
    out: Fingerprint = {}
    if not root.is_dir():
        return out
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_ZIP_DIRS
            and not d.startswith(".tmp")
            and not (d.startswith(".") and d not in (".", ".."))
        ]
        for fn in filenames:
            if count >= _MAX_SNAPSHOT_FILES:
                return out
            if fn.startswith(".") and fn not in (".env.example",):
                continue
            p = Path(dirpath) / fn
            try:
                rel = p.resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            if rel.startswith("META/"):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            out[rel] = (
                int(st.st_size),
                float(getattr(st, "st_mtime_ns", st.st_mtime * 1e9)),
            )
            count += 1
    return out


def diff_fingerprints(before: Fingerprint, after: Fingerprint) -> Dict[str, List[str]]:
    added = sorted(p for p in after if p not in before)
    removed = sorted(p for p in before if p not in after)
    modified: List[str] = []
    for p in after:
        if p in before and before[p] != after[p]:
            modified.append(p)
    modified.sort()
    return {"added": added, "removed": removed, "modified": modified}


def cap_delta(d: Dict[str, List[str]], cap: int = 200) -> Dict[str, object]:
    total = sum(len(d.get(k) or []) for k in ("added", "removed", "modified"))
    return {
        "added": (d.get("added") or [])[:cap],
        "removed": (d.get("removed") or [])[:cap],
        "modified": (d.get("modified") or [])[:cap],
        "truncated": total > 3 * cap,
        "added_total": len(d.get("added") or []),
        "removed_total": len(d.get("removed") or []),
        "modified_total": len(d.get("modified") or []),
    }
