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
        from backend.project_state import WORKSPACE_ROOT
        full = os.path.join(WORKSPACE_ROOT, path.lstrip("/"))
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
        from backend.project_state import WORKSPACE_ROOT
        full = os.path.join(WORKSPACE_ROOT, directory.lstrip("/"))
        entries = []
        for entry in os.scandir(full):
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        return {"directory": directory, "entries": entries, "count": len(entries)}
    except FileNotFoundError:
        return {"error": f"directory not found: {directory}"}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_search_code(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for a pattern in workspace files."""
    query = args.get("query", "")
    max_results = int(args.get("max_results", 20))
    if not query:
        return {"error": "query is required"}
    try:
        import subprocess
        from backend.project_state import WORKSPACE_ROOT
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "-m", str(max_results), query, "."],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.strip().splitlines()[:max_results]
        return {"query": query, "matches": lines, "count": len(lines)}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_inspect_runtime(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect the current runtime state: active tasks, recent events."""
    try:
        from backend.services.runtime.task_manager import task_manager
        from backend.services.events import event_bus
        tasks = list(getattr(task_manager, "tasks", {}).values())[-10:]
        events = [
            {"type": r.event_type, "ts": r.ts}
            for r in event_bus.recent_events(limit=10)
        ]
        return {"active_tasks": tasks, "recent_events": events}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_skill_lookup(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Look up which skill matches a user intent string."""
    text = args.get("text", "")
    try:
        from backend.services.skills import resolve_skill
        skill = resolve_skill(text)
        if skill:
            return {
                "matched": True,
                "skill": skill.name,
                "description": skill.description,
                "allowed_tools": list(skill.allowed_tools),
                "surface": skill.surface,
            }
        return {"matched": False}
    except Exception as exc:
        return {"error": str(exc)}


async def _tool_memory_read(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a value from the agent memory store."""
    key = args.get("key", "")
    scope = args.get("scope", "session")
    if not key:
        return {"error": "key is required"}
    try:
        from backend.services.memory_store import memory_store, MemoryScope
        if memory_store is None:
            return {"error": "memory_store unavailable"}
        ms = MemoryScope(scope) if scope in ("session", "project", "global") else MemoryScope.SESSION
        value = await memory_store.read_memory(key=key, scope=ms)
        return {"key": key, "value": value, "found": value is not None}
    except Exception as exc:
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

_TOOL_REGISTRY: Dict[str, ToolFn] = {
    "read_file": _tool_read_file,
    "list_files": _tool_list_files,
    "search_code": _tool_search_code,
    "inspect_runtime": _tool_inspect_runtime,
    "skill_lookup": _tool_skill_lookup,
    "memory_read": _tool_memory_read,
}


def get_tools() -> Dict[str, ToolFn]:
    """Return the full tool registry available to agentic loops."""
    return dict(_TOOL_REGISTRY)


def register_tool(name: str, fn: ToolFn) -> None:
    """Register a custom tool at runtime."""
    _TOOL_REGISTRY[name] = fn
    logger.debug("[tools] registered tool: %s", name)
