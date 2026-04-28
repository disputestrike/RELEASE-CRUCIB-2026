from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


_BUILD_ERROR_PATTERNS = (
    re.compile(
        r"(?P<file>(?:[A-Za-z]:)?[^\n\r:()]+?\.(?:jsx|tsx|js|ts)):(?P<line>\d+):(?P<col>\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<file>[^\n\r()]+?\.(?:jsx|tsx|js|ts))\s*\((?P<line>\d+):(?P<col>\d+)\)",
        re.IGNORECASE,
    ),
)

_CODE_STARTERS = (
    "import ",
    "export ",
    "const ",
    "let ",
    "var ",
    "function ",
    "class ",
    "async function ",
    "type ",
    "interface ",
)


def parse_build_error_location(log: str, workspace_path: str) -> Optional[Dict[str, Any]]:
    """Extract the first build-error file/line/column from Vite/esbuild output."""
    ws = Path(workspace_path).resolve()
    for pattern in _BUILD_ERROR_PATTERNS:
        for match in pattern.finditer(log or ""):
            raw_file = match.group("file").strip().strip("'\"")
            path = Path(raw_file.replace("\\", "/"))
            if not path.is_absolute():
                path = ws / path
            try:
                resolved = path.resolve()
                resolved.relative_to(ws)
            except Exception:
                continue
            if resolved.exists() and resolved.is_file():
                return {
                    "path": resolved,
                    "relative_path": resolved.relative_to(ws).as_posix(),
                    "line": int(match.group("line")),
                    "column": int(match.group("col")),
                }
    return None


def _strip_markdown_fences(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().lower().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _strip_prose_preamble(text: str) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        lowered = stripped.lower()
        if stripped.startswith(("/", "*", "{", "<")) or lowered.startswith(_CODE_STARTERS):
            return "\n".join(lines[idx:]) + ("\n" if text.endswith("\n") else "")
    return text


def _remove_ts_annotations_from_js(text: str) -> str:
    """Remove common TypeScript annotations that break .js/.jsx generated files."""
    out = text
    out = re.sub(
        r"\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*[^=;\n]+=",
        r"\1 \2 =",
        out,
    )
    out = re.sub(
        r"([,(]\s*[A-Za-z_$][\w$]*)\s*:\s*[^,)=\n]+",
        r"\1",
        out,
    )
    out = re.sub(
        r"(\)\s*):\s*[^={;\n]+(\s*(?:=>|\{))",
        r"\1\2",
        out,
    )
    return out


def _repair_expected_semicolon_colon(text: str, line_no: int) -> str:
    lines = text.splitlines()
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return text
    line = lines[idx]
    repaired = re.sub(
        r"\b(const|let|var)\s+([A-Za-z_$][\w$]*)\s*:\s*([^=;\n]+)=",
        r"\1 \2 =",
        line,
        count=1,
    )
    if repaired != line:
        lines[idx] = repaired
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text


def repair_npm_build_failure(workspace_path: str, log: str) -> Dict[str, Any]:
    """Apply deterministic, bounded repairs for common generated JS/JSX build errors."""
    location = parse_build_error_location(log, workspace_path)
    if not location:
        return {"changed_files": [], "reason": "no_parseable_error_location"}

    path: Path = location["path"]
    if path.suffix.lower() not in {".js", ".jsx"}:
        return {"changed_files": [], "reason": "unsupported_file_type", "location": _public_location(location)}

    before = path.read_text(encoding="utf-8", errors="replace")
    after = _strip_markdown_fences(before)
    after = _strip_prose_preamble(after)
    after = _remove_ts_annotations_from_js(after)
    if "Expected \";\" but found \":\"" in (log or "") or "Expected ';' but found ':'" in (log or ""):
        after = _repair_expected_semicolon_colon(after, int(location["line"]))

    if after == before:
        return {"changed_files": [], "reason": "no_deterministic_repair_available", "location": _public_location(location)}

    path.write_text(after, encoding="utf-8")
    return {
        "changed_files": [location["relative_path"]],
        "reason": "deterministic_jsx_repair",
        "location": _public_location(location),
    }


def _public_location(location: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "relative_path": location.get("relative_path"),
        "line": location.get("line"),
        "column": location.get("column"),
    }
