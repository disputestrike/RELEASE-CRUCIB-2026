"""
Terminal integration for CrucibAI — real command execution in project workspace.
Sessions are keyed by project path; execute runs commands via subprocess in that path.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
import subprocess
import uuid
import logging
import os
import shutil

logger = logging.getLogger(__name__)

# Max time for a single command
TERMINAL_CMD_TIMEOUT = 120


@dataclass
class TerminalSession:
    session_id: str
    project_path: str
    shell: str
    user_id: str
    project_id: str
    columns: int = 80
    rows: int = 24


def _command_args_for_shell(shell: str, command: str) -> List[str]:
    """Build an explicit shell invocation without using subprocess shell=True."""
    requested = (shell or "").strip()
    if os.name == "nt":
        lower = requested.lower()
        if "powershell" in lower or "pwsh" in lower:
            exe = requested if shutil.which(requested) else (shutil.which("pwsh") or shutil.which("powershell") or "powershell")
            return [exe, "-NoProfile", "-Command", command]
        cmd_exe = os.environ.get("COMSPEC") or "cmd.exe"
        return [cmd_exe, "/d", "/s", "/c", command]

    if not requested:
        requested = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"
    shell_name = Path(requested).name.lower()
    if shell_name in {"bash", "sh", "zsh"}:
        return [requested, "-lc", command]
    if shell_name in {"pwsh", "powershell"}:
        return [requested, "-NoProfile", "-Command", command]
    fallback = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"
    return [fallback, "-lc", command]


def _run_command_sync(cwd: Path, shell: str, command: str, timeout_sec: int = TERMINAL_CMD_TIMEOUT) -> tuple[int, str, str]:
    """Run command in cwd via an explicit shell executable; returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            _command_args_for_shell(shell, command),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=min(timeout_sec, TERMINAL_CMD_TIMEOUT),
            shell=False,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        logger.warning("terminal run in %s: %s", cwd, e)
        return -1, "", str(e)


class TerminalManager:
    _sessions: Dict[str, TerminalSession] = {}

    async def create_terminal(self, project_path: str, shell: str = "/bin/bash", user_id: str = "", project_id: str = "") -> TerminalSession:
        session_id = str(uuid.uuid4())
        s = TerminalSession(session_id=session_id, project_path=project_path, shell=shell, user_id=user_id, project_id=project_id)
        self._sessions[session_id] = s
        return s

    async def close_terminal(self, session_id: str, user_id: str = "") -> bool:
        session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            del self._sessions[session_id]
            return True
        return False

    async def resize_terminal(self, session_id: str, columns: int, rows: int) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].columns = columns
            self._sessions[session_id].rows = rows
        return True

    async def execute(self, session_id: str, command: str, timeout: int = TERMINAL_CMD_TIMEOUT, user_id: str = "") -> Dict[str, Any]:
        """Run command in the session's project path. Returns { returncode, stdout, stderr }. Full implementation."""
        if session_id not in self._sessions:
            return {"returncode": -1, "stdout": "", "stderr": "Session not found"}
        session = self._sessions[session_id]
        if session.user_id != user_id:
            return {"returncode": -1, "stdout": "", "stderr": "Session not found"}
        path = Path(session.project_path)
        if not path.exists():
            return {"returncode": -1, "stdout": "", "stderr": "Project path does not exist"}
        returncode, stdout, stderr = await asyncio.to_thread(_run_command_sync, path, session.shell, command, timeout)
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}


terminal_manager = TerminalManager()
