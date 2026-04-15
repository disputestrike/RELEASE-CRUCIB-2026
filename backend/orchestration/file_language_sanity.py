"""
Early gates: obvious extension vs content mismatches on files a step claims to have written.

Does not replace full compile verification — catches cheap cross-language pollution early.
"""

from __future__ import annotations

import json
import re
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

_PY_FROM_IMPORT = re.compile(r"^from\s+[a-zA-Z_][\w.]*\s+import\s+\w")
_PY_SINGLE_IMPORT = re.compile(r"^import\s+[a-zA-Z_]\w*\s*$")


def _safe_path(workspace_root: str, rel: str) -> Path | None:
    raw = (rel or "").strip().replace("\\", "/").lstrip("/")
    if not raw or ".." in raw.split("/"):
        return None
    root = Path(workspace_root).resolve()
    full = (root / raw).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None
    return full


def sniff_touched_files_language_mismatch(
    workspace_root: str, rel_paths: List[str], *, max_files: int = 60
) -> List[str]:
    """Return human-readable issues for touched paths (cap max_files)."""
    issues: List[str] = []
    if not workspace_root or not rel_paths:
        return issues

    seen: set[str] = set()
    for rel in rel_paths[:max_files]:
        norm = rel.strip().replace("\\", "/")
        if not norm or norm in seen:
            continue
        seen.add(norm)
        path = _safe_path(workspace_root, norm)
        if path is None or not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            data = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.debug("file_language_sanity: skip read %s: %s", path, e)
            continue

        head = data[:12000].lstrip()

        if suffix in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
            if head.startswith('"""') or head.startswith("'''"):
                issues.append(
                    f"{norm}: {suffix} file starts with Python-style triple quotes — "
                    "remove prose/docstring wrappers so the file is valid JS/TS."
                )
                continue
            first_line = head.split("\n", 1)[0].strip()
            if _PY_FROM_IMPORT.match(first_line) and "{" not in first_line:
                issues.append(
                    f"{norm}: top line looks like a Python `from … import` in a {suffix} file."
                )
                continue
            if (
                _PY_SINGLE_IMPORT.match(first_line)
                and " from " not in first_line
                and not first_line.endswith(";")
            ):
                # `import foo` Python one-liner (rare in TS); allow `import type X`
                if not first_line.startswith("import type ") and "{" not in first_line:
                    issues.append(
                        f"{norm}: top line looks like a bare Python `import module` in a {suffix} file."
                    )
                continue

        elif suffix == ".json":
            try:
                if data.strip():  # skip empty JSON files — not a syntax error
                    json.loads(data)
            except json.JSONDecodeError as e:
                issues.append(f"{norm}: invalid JSON ({e.msg} at char {e.pos}).")

        elif suffix == ".sql":
            if head.startswith('"""') or head.startswith("'''"):
                issues.append(
                    f"{norm}: SQL file starts with triple-quoted text (Python-style), not SQL."
                )
            else:
                line0 = head.split("\n", 1)[0].strip()
                if _PY_FROM_IMPORT.match(line0):
                    issues.append(
                        f"{norm}: SQL file starts with a Python `from … import` line."
                    )
                elif line0.startswith("def ") or line0.startswith("class "):
                    issues.append(
                        f"{norm}: SQL file starts with Python def/class — likely wrong language in file."
                    )

        if len(issues) >= 24:
            break

    return issues
