"""
Base Validator: Abstract base class for all runtime validators.

Validators go BEYOND static analysis — they actually compile, build, and test
generated code by running real subprocess commands against the workspace.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import time
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Structured result from any validation stage."""

    success: bool
    language: str
    validator_type: str  # "syntax", "build", "runtime", "integration"
    errors: List[str]
    warnings: List[str]
    files_checked: int
    duration_ms: int
    build_output: str = ""
    command_used: str = ""
    can_auto_repair: bool = False
    repair_hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "success": self.success,
            "language": self.language,
            "validator_type": self.validator_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "files_checked": self.files_checked,
            "duration_ms": self.duration_ms,
            "build_output": self.build_output,
            "command_used": self.command_used,
            "can_auto_repair": self.can_auto_repair,
            "repair_hints": self.repair_hints,
        }

    def summary(self) -> str:
        """Human-readable one-line summary."""
        status = "PASS" if self.success else "FAIL"
        err_count = len(self.errors)
        warn_count = len(self.warnings)
        return (
            f"[{status}] {self.language}/{self.validator_type} "
            f"files={self.files_checked} errors={err_count} "
            f"warnings={warn_count} duration={self.duration_ms}ms"
        )


class BaseValidator(ABC):
    """
    Abstract base for all language-specific runtime validators.

    Each validator implements four stages:
      1. validate_syntax() — static checks (compile, parse, type-check)
      2. validate_build()  — full build (install deps, compile, bundle)
      3. validate_runtime(port) — start server, health-check, kill
      4. validate_integration(port) — start server, test endpoints, kill

    The base class provides:
      - run_command(): safe subprocess wrapper with timeout
      - validate_all(): runs all four stages and returns a dict
      - find_files(): recursive file finder by extension
      - ensure_workspace(): guards against missing / empty workspaces
    """

    def __init__(self, workspace_path: str, timeout_seconds: int = 60):
        self.workspace_path = workspace_path
        self.timeout_seconds = timeout_seconds
        self._language: str = "unknown"

    # ------------------------------------------------------------------
    # Abstract interface — every subclass MUST implement syntax + build
    # ------------------------------------------------------------------

    @abstractmethod
    def validate_syntax(self) -> ValidationResult:
        """Run syntax / static analysis checks. Must be fast (< 10 s)."""
        ...

    @abstractmethod
    def validate_build(self) -> ValidationResult:
        """Full build: install dependencies, compile / bundle."""
        ...

    # ------------------------------------------------------------------
    # Optional overrides — runtime & integration have safe defaults
    # ------------------------------------------------------------------

    def validate_runtime(self, port: int = None) -> ValidationResult:
        """Default: skip runtime validation unless overridden."""
        return ValidationResult(
            success=True,
            language=self._language,
            validator_type="runtime",
            errors=[],
            warnings=["Runtime validation not implemented for this language"],
            files_checked=0,
            duration_ms=0,
            can_auto_repair=False,
            repair_hints=[],
        )

    def validate_integration(self, port: int = None) -> ValidationResult:
        """Default: skip integration validation unless overridden."""
        return ValidationResult(
            success=True,
            language=self._language,
            validator_type="integration",
            errors=[],
            warnings=["Integration validation not implemented"],
            files_checked=0,
            duration_ms=0,
            can_auto_repair=False,
            repair_hints=[],
        )

    # ------------------------------------------------------------------
    # Convenience: run everything
    # ------------------------------------------------------------------

    def validate_all(self, port: int = None) -> Dict[str, ValidationResult]:
        """Run all four validation stages and return a dict."""
        return {
            "syntax": self.validate_syntax(),
            "build": self.validate_build(),
            "runtime": self.validate_runtime(port),
            "integration": self.validate_integration(port),
        }

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def run_command(
        self,
        cmd: str,
        cwd: str = None,
        env: dict = None,
        timeout: int = None,
    ) -> Tuple[str, str, int, int]:
        """
        Run a shell command safely.

        Returns:
            (stdout, stderr, returncode, elapsed_ms)

        Handles:
          - TimeoutExpired  -> returncode = -1
          - Generic OSError -> returncode = -1
          - Always logs the command
        """
        import subprocess as sp

        _cwd = cwd or self.workspace_path
        _timeout = timeout or self.timeout_seconds
        _env = {**os.environ, **(env or {})}

        logger.info(
            "[validator] RUN cmd=%r cwd=%r timeout=%ds", cmd, _cwd, _timeout
        )

        start = time.monotonic()
        try:
            proc = sp.run(
                cmd,
                shell=True,
                cwd=_cwd,
                capture_output=True,
                text=True,
                timeout=_timeout,
                env=_env,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            rc = proc.returncode
            logger.info(
                "[validator] DONE cmd=%r rc=%d elapsed=%dms", cmd, rc, elapsed
            )
            return proc.stdout, proc.stderr, rc, elapsed
        except sp.TimeoutExpired:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.warning("[validator] TIMEOUT cmd=%r after %dms", cmd, elapsed)
            return "", f"Command timed out after {_timeout}s", -1, elapsed
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error("[validator] ERROR cmd=%r exc=%r", cmd, exc)
            return "", str(exc), -1, elapsed

    def run_background(
        self,
        cmd: str,
        cwd: str = None,
        env: dict = None,
    ) -> "subprocess.Popen[str]":
        """
        Launch a long-running process in the background (for runtime tests).

        Returns a Popen object — caller MUST call .kill() / .terminate()
        when done and optionally .wait() to reap the child.
        """
        import subprocess as sp

        _cwd = cwd or self.workspace_path
        _env = {**os.environ, **(env or {})}

        logger.info("[validator] BG-START cmd=%r cwd=%r", cmd, _cwd)
        return sp.Popen(
            cmd,
            shell=True,
            cwd=_cwd,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            text=True,
            env=_env,
        )

    @staticmethod
    def kill_background(proc: "subprocess.Popen") -> None:
        """Safely kill a background process and reap it."""
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except Exception:
            pass  # already dead

    @staticmethod
    def find_files(
        directory: str, extensions: List[str], recursive: bool = True
    ) -> List[str]:
        """Recursively find files matching any of the given extensions."""
        if not os.path.isdir(directory):
            return []
        matches: List[str] = []
        _walk = os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]
        for root, _dirs, files in _walk:
            for fname in files:
                if any(fname.endswith(ext) for ext in extensions):
                    matches.append(os.path.join(root, fname))
        return sorted(matches)

    def ensure_workspace(self) -> Tuple[bool, Optional[str]]:
        """
        Guard against missing / empty workspace.

        Returns (is_valid, error_message_or_None).
        """
        if not os.path.isdir(self.workspace_path):
            msg = f"Workspace does not exist: {self.workspace_path}"
            logger.error(msg)
            return False, msg

        # Count non-hidden files
        file_count = 0
        for _root, _dirs, files in os.walk(self.workspace_path):
            for f in files:
                if not f.startswith("."):
                    file_count += 1
                    if file_count >= 1:
                        break
            if file_count >= 1:
                break

        if file_count == 0:
            msg = f"Workspace is empty: {self.workspace_path}"
            logger.warning(msg)
            return False, msg

        return True, None

    @staticmethod
    def parse_repair_hints(stderr: str, language: str) -> List[str]:
        """
        Extract structured repair hints from error output.

        Examples:
          - "npm_missing_package:axios"
          - "python_syntax_error:line_42_indentation"
          - "typescript_type_error:Property_x_does_not_exist"
        """
        hints: List[str] = []
        if not stderr:
            return hints

        lines = stderr.strip().splitlines()
        for line in lines[:50]:  # limit to avoid processing huge outputs
            line_lower = line.lower().strip()

            # Python: ModuleNotFoundError
            if "ModuleNotFoundError" in line or "modulenotfounderror" in line_lower:
                import re as _re
                m = _re.search(r"No module named '([^']+)'", line)
                if m:
                    hints.append(f"python_missing_module:{m.group(1)}")

            # Python: SyntaxError with line number
            if "SyntaxError" in line or "syntaxerror" in line_lower:
                import re as _re
                m = _re.search(r"line (\d+)", line)
                if m:
                    hints.append(f"python_syntax_error:line_{m.group(1)}")

            # Python: ImportError
            if "ImportError" in line or "importerror" in line_lower:
                import re as _re
                m = _re.search(r"cannot import name '([^']+)'", line)
                if m:
                    hints.append(f"python_import_error:{m.group(1)}")

            # Node / npm: missing packages
            if "Cannot find module" in line or "cannot find module" in line_lower:
                import re as _re
                m = _re.search(r"Cannot find module '([^']+)'", line)
                if m:
                    hints.append(f"npm_missing_package:{m.group(1)}")

            # TypeScript: type errors
            if "error TS" in line:
                import re as _re
                m = _re.search(r"error TS(\d+)", line)
                if m:
                    # Extract simplified message
                    msg_part = line.split(":")[-1].strip()[:80] if ":" in line else line.strip()[:80]
                    safe_msg = _re.sub(r'[^a-zA-Z0-9_]', '_', msg_part)[:60]
                    hints.append(f"typescript_type_error:TS{m.group(1)}_{safe_msg}")

            # C++: linker errors
            if "undefined reference" in line_lower:
                import re as _re
                m = _re.search(r"undefined reference to `([^`']+)'", line)
                if m:
                    hints.append(f"cpp_linker_error:{m.group(1)}")

            # C++: missing headers
            if "fatal error:" in line_lower and ".h" in line_lower:
                import re as _re
                m = _re.search(r"'([^']+\.h)'", line)
                if m:
                    hints.append(f"cpp_missing_header:{m.group(1)}")

            # Go: compilation errors
            if language == "go" and "undefined:" in line_lower:
                import re as _re
                m = _re.search(r"undefined:\s*(\S+)", line)
                if m:
                    hints.append(f"go_undefined:{m.group(1)}")

            # Rust: compiler errors
            if language == "rust" and "error[E" in line:
                import re as _re
                m = _re.search(r"error\[([^\]]+)\]", line)
                if m:
                    hints.append(f"rust_error:{m.group(1)}")

        return hints
