"""
backend/services/tools.py
─────────────────────────
Tool registry for the agentic loops (ReAct, observe-act-inspect-review, etc.).

Provides ``get_tools()`` which returns a dict of callable async tool functions
keyed by tool name.  Each tool follows the signature::

    async def tool_fn(name: str, args: dict) -> Any

Tools here are lightweight wrappers that delegate to the RuntimeEngine's
controlled execution surface so that all tool calls remain within the
permission boundary.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

ToolFn = Callable[[str, Dict[str, Any]], Any]


# ─────────────────────────────────────────────────────────────────────────────
# Built-in tool implementations
# ─────────────────────────────────────────────────────────────────────────────

async def _tool_read_file(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a file from the workspace and return its contents."""
    path = args.get("path", "")
    if not path:
        return {"error": "path is required"}
    try:
        from .project_state import WORKSPACE_ROOT  # type: ignore[import]
    except Exception:
        try:
            from ..project_state import WORKSPACE_ROOT  # type: ignore[import]
        except Exception:
            WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/tmp/workspace")
    try:
        full = os.path.join(str(WORKSPACE_ROOT), path.lstrip("/"))
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        return {"path": path, "content": content, "size": len(content)}
    except FileNotFoundError:
        return {"error": f"file not found: {path}"}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_list_files(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """List files in a workspace directory."""
    directory = args.get("directory", ".")
    try:
        from .project_state import WORKSPACE_ROOT  # type: ignore[import]
    except Exception:
        try:
            from ..project_state import WORKSPACE_ROOT  # type: ignore[import]
        except Exception:
            WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/tmp/workspace")
    try:
        full = os.path.join(str(WORKSPACE_ROOT), directory.lstrip("/"))
        entries = []
        for entry in os.scandir(full):
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        return {"directory": directory, "entries": entries}
    except FileNotFoundError:
        return {"error": f"directory not found: {directory}"}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_search_files(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for a pattern in workspace files."""
    import fnmatch
    pattern = args.get("pattern", "")
    glob = args.get("glob", "**/*")
    if not pattern:
        return {"error": "pattern is required"}
    try:
        from .project_state import WORKSPACE_ROOT  # type: ignore[import]
    except Exception:
        try:
            from ..project_state import WORKSPACE_ROOT  # type: ignore[import]
        except Exception:
            WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/tmp/workspace")
    try:
        import pathlib
        root = pathlib.Path(str(WORKSPACE_ROOT))
        matches = []
        for p in root.rglob("*"):
            if p.is_file() and fnmatch.fnmatch(p.name, glob.split("/")[-1] if "/" in glob else glob):
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if pattern in line:
                            matches.append({
                                "file": str(p.relative_to(root)),
                                "line": i,
                                "content": line.strip(),
                            })
                            if len(matches) >= 50:
                                break
                except Exception:
                    pass
            if len(matches) >= 50:
                break
        return {"pattern": pattern, "matches": matches}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_write_file(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Write content to a file in the workspace."""
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return {"error": "path is required"}
    try:
        from .project_state import WORKSPACE_ROOT  # type: ignore[import]
    except Exception:
        try:
            from ..project_state import WORKSPACE_ROOT  # type: ignore[import]
        except Exception:
            WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/tmp/workspace")
    try:
        import pathlib
        full = pathlib.Path(str(WORKSPACE_ROOT)) / path.lstrip("/")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8"))}
    except Exception as exc:
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Public registry
# ─────────────────────────────────────────────────────────────────────────────

_BUILTIN_TOOLS: Dict[str, ToolFn] = {
    "read_file": _tool_read_file,
    "list_files": _tool_list_files,
    "search_files": _tool_search_files,
    "write_file": _tool_write_file,
}


def get_tools(extra: Dict[str, ToolFn] | None = None) -> Dict[str, ToolFn]:
    """Return the full tool registry, optionally merged with caller-supplied extras.

    Args:
        extra: Additional tools to merge in (override builtins if names clash).

    Returns:
        Dict mapping tool name → async callable.
    """
    tools = dict(_BUILTIN_TOOLS)
    if extra:
        tools.update(extra)
    return tools
