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

logger = logging.getLogger(__name__)

# Max time for a single command
TERMINAL_CMD_TIMEOUT = 120


@dataclass
class TerminalSession:
    session_id: str
    project_path: str
    shell: str
    columns: int = 80
    rows: int = 24


def _run_command_sync(cwd: Path, command: str, timeout_sec: int = TERMINAL_CMD_TIMEOUT) -> tuple[int, str, str]:
    """Run command in cwd with shell=True; returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=min(timeout_sec, TERMINAL_CMD_TIMEOUT),
            shell=True,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        logger.warning("terminal run in %s: %s", cwd, e)
        return -1, "", str(e)


class TerminalManager:
    _sessions: Dict[str, TerminalSession] = {}

    async def create_terminal(self, project_path: str, shell: str = "/bin/bash") -> TerminalSession:
        session_id = str(uuid.uuid4())
        s = TerminalSession(session_id=session_id, project_path=project_path, shell=shell)
        self._sessions[session_id] = s
        return s

    async def close_terminal(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
        return True

    async def resize_terminal(self, session_id: str, columns: int, rows: int) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].columns = columns
            self._sessions[session_id].rows = rows
        return True

    async def execute(self, session_id: str, command: str, timeout: int = TERMINAL_CMD_TIMEOUT) -> Dict[str, Any]:
        """Run command in the session's project path. Returns { returncode, stdout, stderr }. Full implementation."""
        if session_id not in self._sessions:
            return {"returncode": -1, "stdout": "", "stderr": "Session not found"}
        path = Path(self._sessions[session_id].project_path)
        if not path.exists():
            return {"returncode": -1, "stdout": "", "stderr": "Project path does not exist"}
        returncode, stdout, stderr = await asyncio.to_thread(_run_command_sync, path, command, timeout)
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}


terminal_manager = TerminalManager()
