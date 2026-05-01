"""
Repair Engine — iterative detect → fix → rerun loop.

This is the core of CrucibAI's self-healing capability.  When a build or
test command fails the RepairEngine:

  1. Parses the error output into a structured ErrorDetail
  2. Reads the failing file(s) from the VirtualFS
  3. Asks the LLM (via llm_client capability routing) to produce a fix
  4. Writes the fix back to disk
  5. Reruns the original command
  6. Repeats until the command passes OR max_attempts is reached
  7. Returns a RepairResult describing every attempt

The loop is Cursor-grade: it never stops at one attempt and it passes the
full error context (including previous failed attempts) to the LLM so each
iteration benefits from what was tried before.

Usage::

    from backend.services.repair_engine import repair_engine

    result = await repair_engine.detect_and_fix(
        command="npm run build",
        command_result=failed_result,
        project_root="/tmp/crucib-workspace/my-project",
        conversation_history=[...],
        on_attempt=lambda attempt: emit_event("repair_attempt", attempt),
    )
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

from backend.services.terminal_executor import terminal as default_terminal
from backend.services.test_parser import parser as test_parser

logger = logging.getLogger(__name__)

# Maximum repair iterations before giving up.
_DEFAULT_MAX_ATTEMPTS = 5
# Maximum characters of error output forwarded to the LLM.
_MAX_ERROR_CHARS = 3000
# Maximum characters of file content forwarded to the LLM.
_MAX_FILE_CHARS = 8000


# --------------------------------------------------------------------------- #
#  Result types                                                                #
# --------------------------------------------------------------------------- #

class RepairAttempt:
    """One iteration of the repair loop."""

    __slots__ = ("iteration", "error_parsed", "file_patched", "fix_snippet",
                 "rerun_result", "success", "timestamp")

    def __init__(
        self,
        iteration: int,
        error_parsed: Dict[str, Any],
        file_patched: str,
        fix_snippet: str,
        rerun_result: Dict[str, Any],
    ) -> None:
        self.iteration    = iteration
        self.error_parsed = error_parsed
        self.file_patched = file_patched
        self.fix_snippet  = fix_snippet[:500]  # truncate for logs
        self.rerun_result = rerun_result
        self.success      = rerun_result.get("success", False)
        self.timestamp    = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration":    self.iteration,
            "file_patched": self.file_patched,
            "success":      self.success,
            "return_code":  self.rerun_result.get("return_code"),
            "duration_ms":  self.rerun_result.get("duration_ms"),
            "timestamp":    self.timestamp,
        }


class RepairResult:
    """Aggregated outcome of the full repair run."""

    def __init__(
        self,
        status: str,
        attempts: List[RepairAttempt],
        final_result: Optional[Dict[str, Any]],
        original_error: str,
    ) -> None:
        self.status         = status          # "already_passing" | "fixed" | "max_attempts_reached" | "no_file_found"
        self.attempts       = attempts
        self.final_result   = final_result
        self.original_error = original_error
        self.fixed          = status == "fixed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":        self.status,
            "fixed":         self.fixed,
            "iterations":    len(self.attempts),
            "attempts":      [a.to_dict() for a in self.attempts],
            "final_success": (self.final_result or {}).get("success", False),
        }


# --------------------------------------------------------------------------- #
#  RepairEngine                                                                #
# --------------------------------------------------------------------------- #

class RepairEngine:
    """
    Iterative build/test repair.

    Parameters
    ----------
    max_attempts:
        Maximum LLM→rerun cycles before declaring failure.
    terminal:
        TerminalExecutor instance (defaults to module singleton).
    call_llm:
        Async callable ``(prompt: str, task_type: str) -> str``.
        By default uses llm_client.call_llm_simple() which respects
        capability routing (repair_patch_generation → Cerebras).
    """

    def __init__(
        self,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        terminal=None,
        call_llm: Optional[Callable[..., Coroutine[Any, Any, str]]] = None,
    ) -> None:
        self.max_attempts = max_attempts
        self._terminal = terminal or default_terminal
        self._call_llm = call_llm or _default_llm_caller

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def detect_and_fix(
        self,
        command: str,
        command_result: Dict[str, Any],
        project_root: str,
        *,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        on_attempt: Optional[Callable[[RepairAttempt], Any]] = None,
    ) -> RepairResult:
        """
        Main entry point.

        If *command_result* already succeeded this returns immediately with
        status "already_passing".

        Otherwise it enters the repair loop, calling the LLM and rerunning
        *command* up to *max_attempts* times.
        """
        if command_result.get("success"):
            return RepairResult(
                status="already_passing",
                attempts=[],
                final_result=command_result,
                original_error="",
            )

        error_output = (
            command_result.get("stderr") or command_result.get("stdout") or ""
        )
        logger.info("[RepairEngine] starting repair loop  command=%s", command[:80])

        # Parse the initial error
        parsed = _parse_error(error_output, project_root)
        if parsed["file"] == "unknown":
            logger.warning("[RepairEngine] cannot locate failing file — aborting repair")
            return RepairResult(
                status="no_file_found",
                attempts=[],
                final_result=command_result,
                original_error=error_output,
            )

        attempts: List[RepairAttempt] = []
        current_result = command_result
        current_error  = error_output

        for iteration in range(1, self.max_attempts + 1):
            logger.info("[RepairEngine] attempt %d/%d", iteration, self.max_attempts)

            # Read the current content of the failing file
            file_path = os.path.join(project_root, parsed["file"])
            original_content = _read_file(file_path)

            # Build a focused LLM prompt
            prompt = _build_prompt(
                parsed       = parsed,
                file_content = original_content,
                error_output = current_error,
                command      = command,
                iteration    = iteration,
                attempts     = attempts,
                history      = conversation_history or [],
            )

            # Ask the LLM for a fix
            try:
                llm_response = await self._call_llm(prompt, "repair_patch_generation")
            except Exception as exc:
                logger.error("[RepairEngine] LLM call failed on attempt %d: %s", iteration, exc)
                # Don't give up — maybe the next iteration recovers
                attempts.append(RepairAttempt(
                    iteration    = iteration,
                    error_parsed = parsed,
                    file_patched = parsed["file"],
                    fix_snippet  = f"[LLM error: {exc}]",
                    rerun_result = {"success": False, "stderr": str(exc), "return_code": -1},
                ))
                continue

            # Extract the code block the LLM returned
            fixed_code = _extract_code_block(llm_response)
            if not fixed_code:
                logger.warning("[RepairEngine] no code block in LLM response (attempt %d)", iteration)
                continue

            # Apply the fix
            _write_file(file_path, fixed_code)

            # Rerun the original command
            rerun = await self._terminal.execute(
                command, cwd=project_root, timeout=300
            )

            attempt = RepairAttempt(
                iteration    = iteration,
                error_parsed = parsed,
                file_patched = parsed["file"],
                fix_snippet  = fixed_code,
                rerun_result = rerun,
            )
            attempts.append(attempt)

            if on_attempt:
                try:
                    cb = on_attempt(attempt)
                    if asyncio.iscoroutine(cb):
                        await cb
                except Exception:
                    pass

            if rerun.get("success"):
                logger.info("[RepairEngine] ✅ fixed in %d attempt(s)", iteration)
                return RepairResult(
                    status       = "fixed",
                    attempts     = attempts,
                    final_result = rerun,
                    original_error = error_output,
                )

            # Update context for next iteration
            current_result = rerun
            current_error  = rerun.get("stderr") or rerun.get("stdout") or ""
            parsed = _parse_error(current_error, project_root)

        logger.warning("[RepairEngine] ❌ max_attempts=%d reached without fix", self.max_attempts)
        return RepairResult(
            status       = "max_attempts_reached",
            attempts     = attempts,
            final_result = current_result,
            original_error = error_output,
        )


# --------------------------------------------------------------------------- #
#  Internal helpers                                                            #
# --------------------------------------------------------------------------- #

def _parse_error(output: str, project_root: str) -> Dict[str, Any]:
    """Extract file + line from error output."""

    # pytest / Python traceback:  '  File "src/api.py", line 42, in ...'
    m = re.search(r'File\s+"?([^">\n]+\.py)"?,\s+line\s+(\d+)', output)
    if m:
        return {"file": _rel(m.group(1), project_root), "line": int(m.group(2)),
                "message": output.splitlines()[0][:200]}

    # pytest FAILED line:  'FAILED tests/test_api.py::test_foo'
    m = re.search(r'FAILED\s+([\w/.\-]+\.py)(?:::(\S+))?', output)
    if m:
        return {"file": m.group(1), "line": None,
                "message": output.splitlines()[0][:200]}

    # TypeScript:  'src/api.ts(42,5): error TS2304'
    m = re.search(r'([\w/.\-]+\.tsx?)\((\d+),\d+\)', output)
    if m:
        return {"file": m.group(1), "line": int(m.group(2)),
                "message": output.splitlines()[0][:200]}

    # Generic:  'api.py:42' or 'api.js line 42'
    m = re.search(r'([\w/.\-]+\.\w+)[:\s]+(\d+)', output)
    if m:
        return {"file": _rel(m.group(1), project_root), "line": int(m.group(2)),
                "message": output.splitlines()[0][:200]}

    return {"file": "unknown", "line": None, "message": output[:200]}


def _rel(path: str, root: str) -> str:
    """Convert absolute path to relative if it's under root."""
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def _read_file(full_path: str) -> str:
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(_MAX_FILE_CHARS + 1)
        if len(content) > _MAX_FILE_CHARS:
            return content[:_MAX_FILE_CHARS] + "\n# [truncated]"
        return content
    except OSError:
        return "# [file not readable]"


def _write_file(full_path: str, content: str) -> None:
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _extract_code_block(response: str) -> Optional[str]:
    """Pull the first fenced code block out of an LLM response."""
    m = re.search(
        r"```(?:python|typescript|tsx?|jsx?|javascript|js)?\n(.*?)\n```",
        response,
        re.DOTALL,
    )
    if m:
        return m.group(1)
    # Fallback: no fence at all — return entire response if it looks like code
    stripped = response.strip()
    if stripped and not stripped.startswith("#") and len(stripped) > 20:
        return stripped
    return None


def _build_prompt(
    *,
    parsed: Dict[str, Any],
    file_content: str,
    error_output: str,
    command: str,
    iteration: int,
    attempts: List[RepairAttempt],
    history: List[Dict[str, Any]],
) -> str:
    prev = ""
    if attempts:
        prev_lines = [
            f"  Attempt {a.iteration}: {'✅ passed' if a.success else '❌ failed'}"
            for a in attempts
        ]
        prev = "PREVIOUS ATTEMPTS:\n" + "\n".join(prev_lines) + "\n\n"

    return f"""You are an expert software engineer fixing a failing build/test.

COMMAND THAT FAILED:
{command}

FAILING FILE: {parsed['file']}  (line {parsed['line'] or 'unknown'})

ERROR OUTPUT:
{error_output[:_MAX_ERROR_CHARS]}

CURRENT FILE CONTENT:
```
{file_content}
```

{prev}ITERATION: {iteration} of {_DEFAULT_MAX_ATTEMPTS}

Instructions:
1. Identify the root cause from the error output.
2. Apply the minimal targeted fix to the file.
3. Return ONLY the complete corrected file content inside a single code block.
4. Do NOT include any explanation outside the code block.
5. Do NOT introduce new bugs or change unrelated logic.
"""


async def _default_llm_caller(prompt: str, task_type: str) -> str:
    """
    Fallback LLM caller when no custom call_llm is injected.
    Uses llm_client's capability routing so repair tasks go to Cerebras.
    """
    try:
        from backend.llm_client import call_llm_simple
        return await call_llm_simple(prompt, task_type=task_type)
    except Exception as exc:
        raise RuntimeError(f"Default LLM caller failed: {exc}") from exc


# Module-level singleton.
repair_engine = RepairEngine()
