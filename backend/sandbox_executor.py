"""
CrucibAI Sandbox Executor
===========================
Provides safe, isolated code execution for generated code.
Uses subprocess with resource limits — NO Docker dependency.

Railway doesn't support Docker-in-Docker, so this uses process-level
isolation with timeouts, memory limits, and restricted imports.

Usage:
    from sandbox_executor import SandboxExecutor

    executor = SandboxExecutor()
    result = await executor.execute("print('hello')", language="python", timeout=30)
"""

import asyncio
import subprocess
import sys
import tempfile
import os
import logging
import shutil
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Dangerous imports that should be blocked in sandbox
BLOCKED_IMPORTS = {
    "subprocess",
    "os.system",
    "shutil.rmtree",
    "importlib",
    "__import__",
    "eval(",
    "exec(",
    "compile(",
    "open('/etc",
    "open('/proc",
    "open('/sys",
}

# Resource limits (defaults; override in production via CRUCIBAI_SANDBOX_* — see get_sandbox_resource_limits)
MAX_OUTPUT_SIZE = 100_000  # bytes
MAX_FILE_SIZE = 500_000  # bytes
MAX_MEMORY_MB = 512  # MB
MAX_CPU_SECONDS = 30  # seconds
SANDBOX_DIR = "/tmp/crucibai_sandbox"


def _env_int_bounded(name: str, default: int, *, lo: int, hi: int) -> int:
    try:
        v = int(os.environ.get(name, str(default)))
        return max(lo, min(hi, v))
    except (ValueError, TypeError):
        return default


def get_sandbox_resource_limits() -> Dict[str, int]:
    """
    Effective rlimits for the sandbox child (Linux preexec_fn).
    Env: CRUCIBAI_SANDBOX_MAX_MEMORY_MB, CRUCIBAI_SANDBOX_CPU_SECONDS,
    CRUCIBAI_SANDBOX_MAX_NPROC, CRUCIBAI_SANDBOX_MAX_FSIZE_MB.
    """
    return {
        "max_memory_mb": _env_int_bounded(
            "CRUCIBAI_SANDBOX_MAX_MEMORY_MB", MAX_MEMORY_MB, lo=16, hi=8192
        ),
        "max_cpu_seconds": _env_int_bounded(
            "CRUCIBAI_SANDBOX_CPU_SECONDS", MAX_CPU_SECONDS, lo=1, hi=7200
        ),
        "max_nproc": _env_int_bounded("CRUCIBAI_SANDBOX_MAX_NPROC", 10, lo=1, hi=512),
        "max_fsize_mb": _env_int_bounded(
            "CRUCIBAI_SANDBOX_MAX_FSIZE_MB", 50, lo=1, hi=4096
        ),
    }


def _set_resource_limits():
    """
    Set resource limits for sandboxed child processes.
    Called via preexec_fn in subprocess — runs in the child before exec.
    """
    try:
        import resource as _res
    except ImportError:
        return  # Windows: no resource module

    limits = get_sandbox_resource_limits()
    mem_bytes = limits["max_memory_mb"] * 1024 * 1024
    try:
        _res.setrlimit(_res.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ValueError, OSError):
        pass  # Some systems don't support RLIMIT_AS

    cpu = limits["max_cpu_seconds"]
    try:
        _res.setrlimit(_res.RLIMIT_CPU, (cpu, cpu))
    except (ValueError, OSError):
        pass

    nproc = limits["max_nproc"]
    try:
        _res.setrlimit(_res.RLIMIT_NPROC, (nproc, nproc))
    except (ValueError, OSError):
        pass

    file_limit = limits["max_fsize_mb"] * 1024 * 1024
    try:
        _res.setrlimit(_res.RLIMIT_FSIZE, (file_limit, file_limit))
    except (ValueError, OSError):
        pass


class SandboxExecutor:
    """
    Process-level sandbox for executing generated code.
    Uses subprocess with resource limits instead of Docker.
    Compatible with Railway, Render, Fly.io, and any Linux host.
    """

    def __init__(self, work_dir: Optional[str] = None):
        self._work_dir = work_dir or SANDBOX_DIR
        os.makedirs(self._work_dir, exist_ok=True)

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        project_id: str = "",
    ) -> Dict[str, Any]:
        """
        Execute code in a sandboxed subprocess with resource limits.

        Args:
            code: Source code to execute
            language: Programming language (python, node, bash)
            timeout: Maximum execution time in seconds
            project_id: Project identifier for tracking

        Returns:
            Dict with success, stdout, stderr, exit_code, execution_time
        """
        # Security check
        security_issues = self._security_scan(code, language)
        if security_issues:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Security violation: {'; '.join(security_issues)}",
                "exit_code": -1,
                "execution_time": 0,
                "blocked": True,
            }

        # Create isolated temp directory for this execution
        exec_dir = tempfile.mkdtemp(
            prefix=f"crucibai_exec_{project_id}_",
            dir=self._work_dir,
        )

        try:
            result = await self._run_in_subprocess(code, language, timeout, exec_dir)
            return result
        finally:
            try:
                shutil.rmtree(exec_dir, ignore_errors=True)
            except Exception:
                pass

    async def _run_in_subprocess(
        self,
        code: str,
        language: str,
        timeout: int,
        exec_dir: str,
    ) -> Dict[str, Any]:
        """Run code in a subprocess with resource limits."""

        # Write code to temp file
        ext = {"python": ".py", "node": ".js", "bash": ".sh"}.get(language, ".py")
        code_file = os.path.join(exec_dir, f"main{ext}")

        with open(code_file, "w") as f:
            f.write(code)

        # Build command
        cmd = self._build_command(language, code_file)
        if not cmd:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Unsupported language: {language}",
                "exit_code": -1,
                "execution_time": 0,
            }

        start = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=exec_dir,
                preexec_fn=_set_resource_limits,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "HOME": exec_dir,
                    "TMPDIR": exec_dir,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUNBUFFERED": "1",
                    "NODE_ENV": "sandbox",
                },
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout}s",
                    "exit_code": -1,
                    "execution_time": timeout,
                    "timed_out": True,
                }

            elapsed = round(time.monotonic() - start, 2)

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE],
                "stderr": stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE],
                "exit_code": process.returncode,
                "execution_time": elapsed,
            }

        except Exception as e:
            elapsed = round(time.monotonic() - start, 2)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "execution_time": elapsed,
            }

    def _build_command(self, language: str, code_file: str) -> list:
        """Build the execution command for the given language."""
        py = sys.executable or "python"
        commands = {
            "python": [py, "-u", code_file],
            "node": ["node", code_file],
            "bash": ["bash", code_file],
        }
        return commands.get(language, [])

    def _security_scan(self, code: str, language: str) -> List[str]:
        """
        Scan code for dangerous patterns.
        Returns list of security issues found.
        """
        issues = []
        code_lower = code.lower()

        for blocked in BLOCKED_IMPORTS:
            if blocked.lower() in code_lower:
                issues.append(f"Blocked pattern: {blocked}")

        # Check for network access attempts
        if language == "python":
            if "socket" in code_lower and "import socket" in code_lower:
                issues.append("Direct socket access not allowed")

        # Check code size
        if len(code) > MAX_FILE_SIZE:
            issues.append(f"Code exceeds maximum size ({MAX_FILE_SIZE} bytes)")

        return issues

    async def validate_generated_code(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Validate generated code without executing it.
        Checks syntax, imports, and basic structure.
        """
        if language == "python":
            try:
                import ast as _ast

                _ast.parse(code)
                return {"valid": True, "language": language, "issues": []}
            except SyntaxError as e:
                return {
                    "valid": False,
                    "language": language,
                    "issues": [f"Syntax error at line {e.lineno}: {e.msg}"],
                }

        security_issues = self._security_scan(code, language)
        return {
            "valid": len(security_issues) == 0,
            "language": language,
            "issues": security_issues,
        }

    def cleanup(self):
        """Clean up all sandbox directories."""
        try:
            if os.path.exists(self._work_dir):
                shutil.rmtree(self._work_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Sandbox cleanup failed: {e}")


# Singleton instance
sandbox = SandboxExecutor()
