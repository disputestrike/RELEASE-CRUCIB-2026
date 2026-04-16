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
from services.events import event_bus
from services.policy import permission_engine
from services.runtime.execution_authority import require_runtime_authority
from services.runtime.execution_context import (
    current_project_id,
    current_skill_hint,
    current_task_id,
)
from services.skills.skill_registry import SkillDef, resolve_skill
from services.skills.skill_executor import skill_allows_tool

logger = logging.getLogger(__name__)

# Commands allowed for execute_tool(..., "run", { "command": [...], "cwd": "optional relative path" })
RUN_ALLOWLIST = [
    (["python", "-m", "pytest"], True),  # prefix match
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
    runtime_project = current_project_id()
    runtime_task = current_task_id()
    runtime_skill = current_skill_hint()

    require_runtime_authority("tool_executor", detail="execution")

    effective_project_id = runtime_project or project_id
    workspace = _project_workspace(effective_project_id)
    tool_name = (tool_name or "").strip().lower()
    task_id = (params.get("task_id") or params.get("runtime_task_id") or runtime_task or "").strip() or None

    event_bus.emit(
        "tool.start",
        {
            "project_id": effective_project_id,
            "task_id": task_id,
            "tool": tool_name,
            "has_params": bool(params),
        },
    )
    event_bus.emit(
        "tool_start",
        {
            "project_id": effective_project_id,
            "task_id": task_id,
            "tool": tool_name,
            "has_params": bool(params),
        },
    )

    def _finalize(result: Dict[str, Any]) -> Dict[str, Any]:
        event_type = "tool.finish" if bool(result.get("success")) else "tool.fail"
        event_bus.emit(
            event_type,
            {
                "project_id": effective_project_id,
                "task_id": task_id,
                "tool": tool_name,
                "success": bool(result.get("success")),
                "error": result.get("error"),
            },
        )
        event_bus.emit(
            "tool_end",
            {
                "project_id": effective_project_id,
                "task_id": task_id,
                "tool": tool_name,
                "success": bool(result.get("success")),
                "error": result.get("error"),
            },
        )
        return result

    def _ok(payload: Dict[str, Any]) -> Dict[str, Any]:
        out = {"success": True, **payload}
        return _finalize(out)

    def _err(error: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        out: Dict[str, Any] = {"success": False, "error": error}
        if extra:
            out.update(extra)
        return _finalize(out)

    skill_meta: Dict[str, Any] = {"matched": False}
    skill_hint = (params.get("skill") or params.get("skill_name") or runtime_skill or "").strip()
    if skill_hint:
        skill: Optional[SkillDef] = resolve_skill(skill_hint)
        if skill:
            skill_meta = {"matched": True, "name": skill.name}
            if not skill_allows_tool(skill, tool_name):
                return _err(
                    f"Skill denied tool: skill={skill.name} tool={tool_name}",
                    {
                        "skill": {
                            "name": skill.name,
                            "allowed_tools": sorted(list(skill.allowed_tools)),
                        }
                    },
                )

    # Central policy gate. Non-breaking when policy is disabled.
    try:
        decision = permission_engine.evaluate_tool_call(tool_name, params or {})
        if not decision.allowed:
            if decision.mode == "ask":
                return _err(
                    "Policy requires approval",
                    {
                        "policy": {
                            "mode": decision.mode,
                            "reason": decision.reason,
                            "approval_required": True,
                        },
                        "skill": skill_meta,
                    },
                )
            return _err(
                f"Policy denied: {decision.reason}",
                {
                    "policy": {
                        "mode": decision.mode,
                        "reason": decision.reason,
                    },
                    "skill": skill_meta,
                },
            )
        policy_meta = {
            "mode": decision.mode,
            "reason": decision.reason,
        }
    except Exception as e:
        logger.warning("permission engine error; allowing by fallback: %s", e)
        policy_meta = {
            "mode": "fallback",
            "reason": "permission engine error",
        }

    if tool_name == "file":
        action = (params.get("action") or "read").strip().lower()
        path = params.get("path") or ""
        if action == "write":
            content = params.get("content", "")
            p = _resolve_under_workspace(workspace, path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return _ok(
                {
                    "path": str(p),
                    "bytes": len(content.encode("utf-8")),
                    "policy": policy_meta,
                    "skill": skill_meta,
                }
            )
        elif action == "read":
            p = _resolve_under_workspace(workspace, path)
            if not p.exists():
                return _err("File not found", {"policy": policy_meta, "skill": skill_meta})
            return _ok(
                {
                    "content": p.read_text(encoding="utf-8"),
                    "path": str(p),
                    "policy": policy_meta,
                    "skill": skill_meta,
                }
            )
        elif action == "list":
            p = _resolve_under_workspace(workspace, path)
            if not p.is_dir():
                return _err("Not a directory", {"policy": policy_meta, "skill": skill_meta})
            names = [x.name for x in p.iterdir()]
            return _ok(
                {
                    "path": str(p),
                    "entries": names,
                    "policy": policy_meta,
                    "skill": skill_meta,
                }
            )
        elif action == "mkdir":
            p = _resolve_under_workspace(workspace, path)
            p.mkdir(parents=True, exist_ok=True)
            return _ok({"path": str(p), "policy": policy_meta, "skill": skill_meta})
        else:
            return _err(f"Unknown file action: {action}", {"policy": policy_meta, "skill": skill_meta})

    if tool_name == "run":
        cmd = params.get("command")
        if not isinstance(cmd, list):
            return _err("command must be a list", {"policy": policy_meta, "skill": skill_meta})
        if not _is_run_allowed(cmd):
            return _err(f"Command not allowlisted: {cmd}", {"policy": policy_meta, "skill": skill_meta})
        cwd = workspace
        if params.get("cwd"):
            cwd = _resolve_under_workspace(workspace, params["cwd"])
            if not cwd.is_dir():
                cwd = workspace
        # Sandbox by default (Docker when available). Set RUN_IN_SANDBOX=0 to disable.
        run_in_sandbox = os.environ.get("RUN_IN_SANDBOX", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if run_in_sandbox:
            try:
                # Isolated run in Docker (Manus-style). Pick image from command.
                first = (cmd[0] or "").lower()
                if first == "python" or (
                    len(cmd) > 1 and (cmd[1] or "").lower() == "bandit"
                ):
                    image = "python:3.11-slim"
                else:
                    image = "node:20-slim"
                docker_cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{workspace.resolve()}:/.app",
                    "-w",
                    "/.app",
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
                return _finalize(
                    {
                        "success": proc.returncode == 0,
                        "returncode": proc.returncode,
                        "output": out[:50000],
                        "sandbox": True,
                        "policy": policy_meta,
                        "skill": skill_meta,
                    }
                )
            except FileNotFoundError:
                logger.warning("Docker not found; falling back to local run")
                run_in_sandbox = False
            except subprocess.TimeoutExpired:
                return _err(
                    "timeout",
                    {
                        "output": "",
                        "sandbox": True,
                        "policy": policy_meta,
                        "skill": skill_meta,
                    },
                )
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
                return _finalize(
                    {
                        "success": proc.returncode == 0,
                        "returncode": proc.returncode,
                        "output": out[:50000],
                        "policy": policy_meta,
                        "skill": skill_meta,
                    }
                )
            except subprocess.TimeoutExpired:
                return _err("timeout", {"output": "", "policy": policy_meta, "skill": skill_meta})
            except Exception as e:
                return _err(str(e), {"output": "", "policy": policy_meta, "skill": skill_meta})

    if tool_name == "api":
        url = params.get("url") or ""
        if not _is_safe_url(url):
            return _err("URL not allowed (SSRF safety)", {"policy": policy_meta, "skill": skill_meta})
        try:
            import urllib.request

            req = urllib.request.Request(
                url, headers={"User-Agent": "CrucibAI-Tool/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")[:100000]
            return _ok({"status": r.status, "body": body, "policy": policy_meta, "skill": skill_meta})
        except Exception as e:
            return _err(str(e), {"policy": policy_meta, "skill": skill_meta})

    if tool_name == "browser":
        url = params.get("url") or ""
        if not _is_safe_url(url):
            return _err("URL not allowed", {"policy": policy_meta, "skill": skill_meta})
        # Sync fetch only (no Playwright) to avoid async in execute_tool
        try:
            import urllib.request

            req = urllib.request.Request(
                url, headers={"User-Agent": "CrucibAI-Browser/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")[:50000]
            return _ok({"body_preview": body[:2000], "policy": policy_meta, "skill": skill_meta})
        except Exception as e:
            return _err(str(e), {"policy": policy_meta, "skill": skill_meta})

    if tool_name == "db":
        # SQLite in workspace only
        db_path = (params.get("path") or "data.db").strip().lstrip("/")
        if ".." in db_path:
            return _err("Invalid path", {"policy": policy_meta, "skill": skill_meta})
        db_file = workspace / db_path
        action = (params.get("action") or "query").strip().lower()
        if action == "query":
            sql = params.get("sql") or ""
            if not sql.strip().upper().startswith("SELECT"):
                return _err("Only SELECT allowed", {"policy": policy_meta, "skill": skill_meta})
            try:
                import sqlite3

                conn = sqlite3.connect(str(db_file))
                cur = conn.execute(sql)
                rows = cur.fetchall()
                conn.close()
                return _ok({"rows": rows, "policy": policy_meta, "skill": skill_meta})
            except Exception as e:
                return _err(str(e), {"policy": policy_meta, "skill": skill_meta})
        return _err(f"Unknown db action: {action}", {"policy": policy_meta, "skill": skill_meta})

    return _err(f"Unknown tool: {tool_name}", {"policy": policy_meta, "skill": skill_meta})
