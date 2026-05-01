"""
Terminal Executor — sandboxed subprocess execution for CrucibAI.

Provides:
- execute()        : run a command, return full result dict
- stream_execute() : run a command, yield output line-by-line
- validate_command(): block dangerous shell patterns
- get_history()    : recent command history

CrucibAI uses this to run npm install, npm run build, pytest, tsc, etc.
inside the project sandbox. Every result is structured so RepairEngine can
parse it without additional massaging.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Absolute maximum output we will buffer (10 MB).
_MAX_OUTPUT_BYTES = 10 * 1024 * 1024

# Shell patterns that are always blocked regardless of caller.
_DANGEROUS_PATTERNS: List[str] = [
    "rm -rf /",
    "dd if=/dev/zero",
    ":(){:|:&",  # fork bomb
    "cat /etc/shadow",
    "cat /etc/passwd",
    "> /dev/sda",
    "mkfs.",
    "chmod -R 777 /",
]

# Commands that are allowed to run in any CWD (even outside sandbox).
_SAFE_COMMANDS = {"npm", "npx", "node", "python", "python3", "pytest", "tsc",
                  "eslint", "prettier", "pip", "pip3", "git", "cargo", "go",
                  "make", "mvn", "gradle"}


class TerminalExecutorError(Exception):
    """Raised for validation failures before the subprocess is even spawned."""


class TerminalExecutor:
    """Execute shell commands safely inside a sandboxed project root."""

    def __init__(self, default_cwd: str = "/tmp/crucib-workspace") -> None:
        self.default_cwd = default_cwd
        os.makedirs(default_cwd, exist_ok=True)
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Run *command* and return a fully structured result dict.

        Return shape::

            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "return_code": int,
                "command": str,
                "cwd": str,
                "duration_ms": float,
                "timestamp": float,
                "timeout": bool,          # only present when timed out
                "exception": str,         # only present on unexpected error
            }
        """
        cwd = cwd or self.default_cwd
        self._validate_command(command)

        start = time.time()
        merged_env = {**os.environ, **(env or {})}

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=merged_env,
                limit=_MAX_OUTPUT_BYTES,
            )

            try:
                raw_stdout, raw_stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                result: Dict[str, Any] = {
                    "success": proc.returncode == 0,
                    "stdout": raw_stdout.decode("utf-8", errors="replace"),
                    "stderr": raw_stderr.decode("utf-8", errors="replace"),
                    "return_code": proc.returncode,
                    "command": command,
                    "cwd": cwd,
                    "duration_ms": (time.time() - start) * 1000,
                    "timestamp": start,
                }
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                result = {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout}s",
                    "return_code": -1,
                    "command": command,
                    "cwd": cwd,
                    "duration_ms": (time.time() - start) * 1000,
                    "timestamp": start,
                    "timeout": True,
                }

        except TerminalExecutorError:
            raise
        except Exception as exc:
            result = {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "return_code": -1,
                "command": command,
                "cwd": cwd,
                "duration_ms": (time.time() - start) * 1000,
                "timestamp": start,
                "exception": type(exc).__name__,
            }

        self._history.append(result)
        _icon = "✅" if result["success"] else "❌"
        logger.info("terminal [%s] %s  rc=%s  %.0fms",
                    _icon, command[:80], result["return_code"], result["duration_ms"])
        return result

    async def stream_execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run *command* and **yield** output events as they arrive.

        Each yielded dict has one of these shapes::

            {"type": "stdout", "line": str, "timestamp": float}
            {"type": "stderr", "line": str, "timestamp": float}
            {"type": "complete", "return_code": int, "success": bool, "duration_ms": float}
            {"type": "error",   "message": str, "duration_ms": float}
        """
        cwd = cwd or self.default_cwd
        self._validate_command(command)
        merged_env = {**os.environ, **(env or {})}
        start = time.time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=merged_env,
            )
        except Exception as exc:
            yield {"type": "error", "message": str(exc), "duration_ms": 0.0}
            return

        async def _read(stream: asyncio.StreamReader, stream_type: str):
            while True:
                try:
                    line = await asyncio.wait_for(stream.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    yield {"type": "error", "message": "readline timed out",
                           "duration_ms": (time.time() - start) * 1000}
                    break
                if not line:
                    break
                yield {
                    "type": stream_type,
                    "line": line.decode("utf-8", errors="replace").rstrip(),
                    "timestamp": time.time(),
                }

        async for event in _read(proc.stdout, "stdout"):
            yield event
        async for event in _read(proc.stderr, "stderr"):
            yield event

        await proc.wait()
        duration_ms = (time.time() - start) * 1000
        yield {
            "type": "complete",
            "return_code": proc.returncode,
            "success": proc.returncode == 0,
            "duration_ms": duration_ms,
        }
        self._history.append({
            "success": proc.returncode == 0,
            "return_code": proc.returncode,
            "command": command,
            "cwd": cwd,
            "duration_ms": duration_ms,
            "timestamp": start,
            "streamed": True,
        })

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent *limit* command results."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_command(command: str) -> None:
        """Raise TerminalExecutorError for known-dangerous patterns."""
        for pattern in _DANGEROUS_PATTERNS:
            if pattern in command:
                raise TerminalExecutorError(
                    f"Blocked dangerous command pattern: {pattern!r}"
                )


# Module-level singleton — used by RepairEngine and RuntimeEngine.
terminal = TerminalExecutor()
