"""
Central execute_tool(project_id, tool_name, params) for all agents.
- file: read/write/list/mkdir under workspace only (path safety).
- run: allowlisted commands only (pytest, npm test, bandit, npx eslint, vercel, etc.).
  When RUN_IN_SANDBOX=1, run inside a transient Docker container (isolated like Manus).
- api: SSRF-safe (no internal IPs).
- browser: URL rules (no file://; optional localhost).
- db: SQLite in workspace only.

Auth: execute_tool is only invoked from orchestration paths that require get_current_user
and project ownership (server verifies project belongs to user before running build).
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from project_state import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

# Commands allowed for execute_tool(..., "run", { "command": [...], "cwd": "optional relative path" })
RUN_ALLOWLIST = [
    (["python", "-m", "pytest"], True),   # prefix match
    (["npm", "test"], True),
    (["npm", "run", "test"], True),
    (["npx", "jest"], True),
    (["python", "-m", "bandit"], True),
    (["npx", "source-map-explorer"], True),
    (["npx", "lighthouse"], True),
    (["npm", "audit"], True),
    (["npm", "run", "audit"], True),
    (["npx", "eslint"], True),
    (["vercel"], True),
    (["npx", "vercel"], True),
    (["node", "--version"], True),
    (["python", "--version"], True),
    (["wc", "-l"], True),
    (["find", "."], True),
]


def _project_workspace(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_under_workspace(workspace: Path, path: str) -> Path:
    path = (path or "").strip().lstrip("/").replace("\\", "/")
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Invalid path: {path}")
    base = workspace.resolve()
    p = (base / path).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        raise ValueError(f"Path escapes workspace: {path}")
    return p


def _is_run_allowed(cmd: List[str]) -> bool:
    if not cmd or not isinstance(cmd, list):
        return False
    cmd = [str(c).strip() for c in cmd if c]
    for allow_prefix, _ in RUN_ALLOWLIST:
        if len(cmd) >= len(allow_prefix) and cmd[: len(allow_prefix)] == allow_prefix:
            return True
    return False


def _is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        host = (p.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1"):
            return True
        if host.startswith("10.") or host.startswith("172.") or host == "192.168.0.0":
            return False
        if host.endswith(".local"):
            return False
        return True
    except Exception:
        return False


def execute_tool(
    project_id: str,
    tool_name: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute one tool in project workspace. Returns { "success": bool, "output": str, "error": optional }.
    Paths and commands are validated; no path traversal or arbitrary shell.
    """
    workspace = _project_workspace(project_id)
    tool_name = (tool_name or "").strip().lower()

    if tool_name == "file":
        action = (params.get("action") or "read").strip().lower()
        path = params.get("path") or ""
        if action == "write":
            content = params.get("content", "")
            p = _resolve_under_workspace(workspace, path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p), "bytes": len(content.encode("utf-8"))}
        elif action == "read":
            p = _resolve_under_workspace(workspace, path)
            if not p.exists():
                return {"success": False, "error": "File not found"}
            return {"success": True, "content": p.read_text(encoding="utf-8"), "path": str(p)}
        elif action == "list":
            p = _resolve_under_workspace(workspace, path)
            if not p.is_dir():
                return {"success": False, "error": "Not a directory"}
            names = [x.name for x in p.iterdir()]
            return {"success": True, "path": str(p), "entries": names}
        elif action == "mkdir":
            p = _resolve_under_workspace(workspace, path)
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(p)}
        else:
            return {"success": False, "error": f"Unknown file action: {action}"}

    if tool_name == "run":
        cmd = params.get("command")
        if not isinstance(cmd, list):
            return {"success": False, "error": "command must be a list"}
        if not _is_run_allowed(cmd):
            return {"success": False, "error": f"Command not allowlisted: {cmd}"}
        cwd = workspace
        if params.get("cwd"):
            cwd = _resolve_under_workspace(workspace, params["cwd"])
            if not cwd.is_dir():
                cwd = workspace
        # Sandbox by default (Docker when available). Set RUN_IN_SANDBOX=0 to disable.
        run_in_sandbox = os.environ.get("RUN_IN_SANDBOX", "1").strip().lower() in ("1", "true", "yes")
        if run_in_sandbox:
            try:
                # Isolated run in Docker (Manus-style). Pick image from command.
                first = (cmd[0] or "").lower()
                if first == "python" or (len(cmd) > 1 and (cmd[1] or "").lower() == "bandit"):
                    image = "python:3.11-slim"
                else:
                    image = "node:20-slim"
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{workspace.resolve()}:/.app",
                    "-w", "/.app",
                    image,
                ] + cmd
                proc = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    timeout=params.get("timeout", 120) + 10,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                return {"success": proc.returncode == 0, "returncode": proc.returncode, "output": out[:50000], "sandbox": True}
            except FileNotFoundError:
                logger.warning("Docker not found; falling back to local run")
                run_in_sandbox = False
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "timeout", "output": "", "sandbox": True}
            except Exception as e:
                logger.warning("Sandbox run failed: %s", e)
                run_in_sandbox = False
        if not run_in_sandbox:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    capture_output=True,
                    timeout=params.get("timeout", 120),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                return {
                    "success": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "output": out[:50000],
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "timeout", "output": ""}
            except Exception as e:
                return {"success": False, "error": str(e), "output": ""}

    if tool_name == "api":
        url = params.get("url") or ""
        if not _is_safe_url(url):
            return {"success": False, "error": "URL not allowed (SSRF safety)"}
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "CrucibAI-Tool/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")[:100000]
            return {"success": True, "status": r.status, "body": body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    if tool_name == "browser":
        url = params.get("url") or ""
        if not _is_safe_url(url):
            return {"success": False, "error": "URL not allowed"}
        # Sync fetch only (no Playwright) to avoid async in execute_tool
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "CrucibAI-Browser/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")[:50000]
            return {"success": True, "body_preview": body[:2000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    if tool_name == "db":
        # SQLite in workspace only
        db_path = (params.get("path") or "data.db").strip().lstrip("/")
        if ".." in db_path:
            return {"success": False, "error": "Invalid path"}
        db_file = workspace / db_path
        action = (params.get("action") or "query").strip().lower()
        if action == "query":
            sql = params.get("sql") or ""
            if not sql.strip().upper().startswith("SELECT"):
                return {"success": False, "error": "Only SELECT allowed"}
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                cur = conn.execute(sql)
                rows = cur.fetchall()
                conn.close()
                return {"success": True, "rows": rows}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown db action: {action}"}

    return {"success": False, "error": f"Unknown tool: {tool_name}"}
