"""
Extract workspace-relative file paths from verification issue strings so repair
(CodeRepairAgent, self-repair) can target the right sources (especially verification.compile).
"""

from __future__ import annotations

import os
import re
from typing import List

# esbuild: "esbuild failed src/App.jsx: ..."
_RE_ESBUILD = re.compile(
    r"esbuild failed\s+([^\s:]+\.(?:jsx?|tsx?|m?js|cjs))\s*:", re.IGNORECASE
)
# Prose: "Prose preamble detected in rel: ..."
_RE_PROSE = re.compile(
    r"prose preamble detected in\s+([^:\s][^:]*?)\s*:", re.IGNORECASE
)
# Python: "Python syntax error in path: ..." / "py_compile failed path: ..."
_RE_PY = re.compile(
    r"(?:python syntax error in|py_compile failed|py_compile error)\s+([^:\s]+\.py)\s*[:]",
    re.IGNORECASE,
)
# Generic "in path/to/file.ext" tail
_RE_IN_FILE = re.compile(
    r"\b(?:in|for)\s+((?:[\w.-]+/)*[\w.-]+\.(?:jsx?|tsx?|py|json|css|mjs|cjs))\b",
    re.IGNORECASE,
)
# Esbuild stderr lines: src/layouts/SEO.jsx:3:0: ERROR ...
_RE_STDERR_LINE_COL = re.compile(
    r"\b([\w./-]+\.(?:jsx?|tsx?|mjs|cjs|js|ts))\s*:\s*\d+(?:\s*:\s*\d+)?\s*:?",
    re.IGNORECASE,
)
# Python tracebacks: File "backend/auth.py", line 42
_RE_PY_TRACE_FILE = re.compile(
    r'File\s+"([^"]+\.py)"', re.IGNORECASE
)
# Python: Sorry: SyntaxError: ... (bad.py, line 9)
_RE_PY_PAREN_FILE = re.compile(
    r"\(([^\s()]+\.py),\s*line\s+\d+\)",
    re.IGNORECASE,
)


def _extract_paths_from_issue_text(blob: str) -> List[str]:
    """Pull every plausible workspace-relative path out of compile/py_compile stderr."""
    found: List[str] = []
    if not blob:
        return found

    def _push(raw: str) -> None:
        rel = raw.strip().replace("\\", "/").lstrip("/")
        if rel and rel not in found:
            found.append(rel)

    for m in _RE_STDERR_LINE_COL.finditer(blob):
        _push(m.group(1))
    for m in _RE_PY_TRACE_FILE.finditer(blob):
        _push(m.group(1))
    for m in _RE_PY_PAREN_FILE.finditer(blob):
        _push(m.group(1))

    return found


def candidate_files_from_verification_issues(
    issues: List[str],
    workspace_path: str,
    *,
    max_files: int = 24,
) -> List[str]:
    """Return posix-ish relative paths that exist under workspace_path."""
    if not workspace_path or not os.path.isdir(workspace_path) or not issues:
        return []
    found: List[str] = []
    blob = " ".join(str(i) for i in issues if i)

    for issue in issues:
        s = str(issue)
        for rx in (_RE_ESBUILD, _RE_PROSE, _RE_PY, _RE_IN_FILE):
            for m in rx.finditer(s):
                rel = m.group(1).strip().replace("\\", "/").lstrip("/")
                if rel and rel not in found:
                    found.append(rel)
        # Deep scan: stderr often lists secondary files (imports / reexports).
        for rel in _extract_paths_from_issue_text(s):
            if rel not in found:
                found.append(rel)

    # If tooling missing, bias toward common entries when issues mention esbuild/npx
    low = blob.lower()
    if ("npx" in low or "esbuild" in low) and not found:
        for guess in (
            "src/App.jsx",
            "src/App.tsx",
            "src/main.jsx",
            "src/main.tsx",
            "App.jsx",
            "App.tsx",
        ):
            full = os.path.normpath(os.path.join(workspace_path, *guess.split("/")))
            if full.startswith(os.path.normpath(workspace_path)) and os.path.isfile(full):
                found.append(guess.replace("\\", "/"))

    out: List[str] = []
    root = os.path.normpath(workspace_path)
    for rel in found:
        if ".." in rel or rel.startswith("/"):
            continue
        full = os.path.normpath(os.path.join(workspace_path, *rel.split("/")))
        if not full.startswith(root):
            continue
        if os.path.isfile(full) and rel not in out:
            out.append(rel)
        if len(out) >= max_files:
            break
    return out
