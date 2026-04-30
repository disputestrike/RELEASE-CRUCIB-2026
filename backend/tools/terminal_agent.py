"""
Terminal Agent - execute shell commands in sandboxed environments.
Can run tests, git commands, builds, and development workflows with actual effects.
Security: Commands are validated and executed in workspace context only.
"""

import asyncio
import logging
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from ....agents.base_agent import BaseAgent
logger = logging.getLogger(__name__)

# Whitelist of safe commands for execution
SAFE_COMMANDS = {
    "python": True,
    "pip": True,
    "npm": True,
    "yarn": True,
    "git": True,
    "pytest": True,
    "node": True,
    "make": True,
    "docker": True,
    "curl": True,
    "ls": True,
    "pwd": True,
    "echo": True,
    "cat": True,
    "grep": True,
    "find": True,
    "which": True,
    "cd": True,
    "mkdir": True,
}

# Blacklist of dangerous commands
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "dd if=/dev/",
    ":(){ :|:& };:",  # Fork bomb
    "curl | bash",
    "sh -c",
    "exec /",
]


class TerminalAgent(BaseAgent):
    """Shell command execution agent with safety constraints"""

    def __init__(self, llm_client: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, db: Optional[Any] = None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "TerminalAgent"
        self.workspace = Path(config.get("workspace", "./workspace")).resolve() if config else Path.cwd()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_timeout = int(os.environ.get("TERMINAL_AGENT_TIMEOUT", "30"))
        self.active_processes: Dict[str, subprocess.Popen] = {}

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute shell commands safely.

        Expected context:
        {
            "action": "execute|run_test|git_command|build|check_status",
            "command": "command to run",
            "cwd": "working directory (optional, defaults to workspace)",
            "timeout": 30 (optional),
            "background": false (optional, run in background),
        }
        """
        action = context.get("action", "execute")
        command = context.get("command", "")
        cwd = context.get("cwd", str(self.workspace))
        timeout = context.get("timeout", self.max_timeout)
        background = context.get("background", False)

        try:
            # Validate command
            validation = self._validate_command(command)
            if not validation["safe"]:
                return {
                    "success": False,
                    "error": validation["reason"],
                    "stdout": "",
                    "stderr": "",
                    "exit_code": 1,
                }

            # Ensure cwd is within workspace
            cwd_path = Path(cwd).resolve()
            try:
                cwd_path.relative_to(self.workspace)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Working directory outside workspace: {cwd}",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": 1,
                }

            if action == "execute":
                result = await self._execute_command(command, str(cwd_path), timeout, background)
            elif action == "run_test":
                result = await self._run_test(command, str(cwd_path), timeout)
            elif action == "git_command":
                result = await self._git_command(command, str(cwd_path), timeout)
            elif action == "build":
                result = await self._build(command, str(cwd_path), timeout)
            elif action == "check_status":
                result = self._check_process_status(command)
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}

            if self.performance:
                status = "success" if result.get("success") else "error"
                self.performance.track_execution(self.name, status, len(command))

            return result

        except Exception as e:
            logger.error(f"{self.name} execution error: {str(e)}")
            if self.performance:
                self.performance.track_execution(self.name, "error", 0)
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": 1,
            }

    async def _execute_command(self, command: str, cwd: str, timeout: int, background: bool) -> Dict[str, Any]:
        """Execute arbitrary shell command"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            if background:
                process_id = f"process_{int(time.time())}"
                self.active_processes[process_id] = process
                return {
                    "success": True,
                    "process_id": process_id,
                    "message": f"Command running in background: {command[:50]}...",
                }

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s",
                    "stdout": "",
                    "stderr": f"Process killed due to timeout",
                    "exit_code": -1,
                }

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode,
                "command": command,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
            }

    async def _run_test(self, test_spec: str, cwd: str, timeout: int) -> Dict[str, Any]:
        """Run tests with proper error parsing"""
        command = f"pytest {test_spec} -v --tb=short"
        result = await self._execute_command(command, cwd, timeout, False)

        # Parse pytest output for failures
        if result["success"]:
            return {
                **result,
                "test_status": "all_passed",
            }
        else:
            return {
                **result,
                "test_status": "failed",
                "needs_debugging": True,
            }

    async def _git_command(self, git_cmd: str, cwd: str, timeout: int) -> Dict[str, Any]:
        """Execute git commands safely"""
        # Whitelist git subcommands
        allowed_git_ops = ["status", "log", "diff", "branch", "checkout", "pull", "push", "clone"]
        
        first_arg = git_cmd.split()[0] if git_cmd else ""
        if first_arg not in allowed_git_ops:
            return {
                "success": False,
                "error": f"Unsafe git operation: {first_arg}",
                "stdout": "",
                "stderr": "",
                "exit_code": 1,
            }

        command = f"git {git_cmd}"
        return await self._execute_command(command, cwd, timeout, False)

    async def _build(self, build_cmd: str, cwd: str, timeout: int) -> Dict[str, Any]:
        """Run build commands (make, npm build, etc.)"""
        allowed_builders = ["make", "npm", "yarn", "python"]
        first_arg = build_cmd.split()[0] if build_cmd else ""

        if first_arg not in allowed_builders:
            return {
                "success": False,
                "error": f"Unsupported builder: {first_arg}",
                "stdout": "",
                "stderr": "",
                "exit_code": 1,
            }

        return await self._execute_command(build_cmd, cwd, min(timeout, 120), False)

    def _check_process_status(self, process_id: str) -> Dict[str, Any]:
        """Check status of background process"""
        if process_id not in self.active_processes:
            return {
                "success": False,
                "error": f"Process not found: {process_id}",
                "status": "not_found",
            }

        process = self.active_processes[process_id]
        return_code = process.poll()

        if return_code is None:
            return {
                "success": True,
                "status": "running",
                "process_id": process_id,
            }
        else:
            # Process finished
            del self.active_processes[process_id]
            return {
                "success": return_code == 0,
                "status": "completed",
                "process_id": process_id,
                "exit_code": return_code,
            }

    def _validate_command(self, command: str) -> Dict[str, Any]:
        """Validate command for safety"""
        # Check dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command:
                return {"safe": False, "reason": f"Dangerous command pattern detected: {pattern}"}

        # Check if command starts with a whitelisted command
        tokens = shlex.split(command)
        if not tokens:
            return {"safe": False, "reason": "Empty command"}

        first_cmd = tokens[0]
        # Handle path-based executables
        if "/" in first_cmd or "\\" in first_cmd:
            first_cmd = Path(first_cmd).name

        if first_cmd not in SAFE_COMMANDS:
            return {"safe": False, "reason": f"Command not whitelisted: {first_cmd}"}

        return {"safe": True}
