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

_JS_TS_SUFFIXES = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})
# Lines that look like top-level JSON object keys (package.json leak into JSX/TS).
_JSON_MANIFEST_LINE = re.compile(r'^\s*"[^"]+"\s*:\s*')
_PY_ES_MODULE_BRACE = re.compile(r"import\s*\{[^}]+\}\s*from\s*['\"]")
_PY_FROM_EXPRESS = re.compile(r"from\s+['\"]express['\"]", re.I)
_PY_REQUIRE_EXPRESS = re.compile(r"require\s*\(\s*['\"]express['\"]\s*\)", re.I)


def _has_markdown_tree_leak(snippet: str) -> bool:
    """LLMs often paste `├──` directory listings into JSX by mistake."""
    if "├──" in snippet or "└──" in snippet:
        return True
    if "├─" in snippet or "└─" in snippet:
        return True
    for line in snippet.split("\n")[:160]:
        s = line.strip()
        if not s:
            continue
        first = next((c for c in s if c not in " \t"), "")
        if first in "│├└":
            return True
    return False


def _early_line_looks_like_js_ts(line: str) -> bool:
    s = line.strip()
    return bool(
        s.startswith("import ")
        or s.startswith("export ")
        or s.startswith("function ")
        or s.startswith("const ")
        or s.startswith("let ")
        or s.startswith("var ")
        or s.startswith("type ")
        or s.startswith("interface ")
        or s.startswith("enum ")
        or s.startswith("class ")
        or s.startswith("/**")
        or s.startswith("/*")
        or s.startswith("#!")
        or s.startswith("<")
        or s.startswith("use ")
    )


def _meaningful_lines_head(data: str, max_lines: int = 42) -> List[str]:
    out: List[str] = []
    for line in data.split("\n"):
        st = line.strip()
        if not st:
            continue
        if st.startswith("//"):
            continue
        out.append(line)
        if len(out) >= max_lines:
            break
    return out


def _looks_like_package_json_fragment_in_js(meaningful_lines: List[str]) -> bool:
    """Detect JSON manifest lines with no JS/TS preamble (common copy-paste bug)."""
    if len(meaningful_lines) < 2:
        return False
    head = meaningful_lines[:28]
    for ln in head:
        if _early_line_looks_like_js_ts(ln):
            return False
    json_keys = 0
    for ln in head:
        sm = ln.strip()
        if _JSON_MANIFEST_LINE.match(sm):
            json_keys += 1
    return json_keys >= 2


def _file_content_pollution_issues(norm: str, suffix: str, data: str) -> List[str]:
    """Deep scan for wrong-kind-of-text (OpsLedger-class failures)."""
    snippet = data[:24000]
    issues: List[str] = []
    low = suffix.lower()

    if low in _JS_TS_SUFFIXES:
        if _has_markdown_tree_leak(snippet):
            issues.append(
                f"{norm}: JS/TS contains markdown/tree listing characters (├/│/└) — invalid source."
            )
        ml = _meaningful_lines_head(snippet)
        if _looks_like_package_json_fragment_in_js(ml):
            issues.append(
                f"{norm}: JS/TS looks like pasted JSON/manifest (e.g. package.json), not React/TS code."
            )

    elif low == ".py":
        head = snippet[:14000]
        if _PY_ES_MODULE_BRACE.search(head):
            issues.append(
                f"{norm}: Python file contains ES-module `import {{}} from \"…\"` syntax."
            )
        if _PY_FROM_EXPRESS.search(head) or _PY_REQUIRE_EXPRESS.search(head):
            issues.append(
                f"{norm}: Python file references Node `express` — wrong language in `.py`."
            )

    return issues


def detect_write_time_violations(rel: str, content: str) -> List[str]:
    """Guardrails for executor `_safe_write`: reject obvious cross-language blobs."""
    norm = (rel or "").strip().replace("\\", "/")
    if not norm:
        return []
    suf = Path(norm).suffix.lower()
    return _file_content_pollution_issues(norm, suf, content or "")


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

        if suffix in _JS_TS_SUFFIXES or suffix == ".py":
            for msg in _file_content_pollution_issues(norm, suffix, data):
                issues.append(msg)

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
