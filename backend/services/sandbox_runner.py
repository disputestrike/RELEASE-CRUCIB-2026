"""Isolated code-execution sandbox.

Tries E2B (https://e2b.dev) first when ``E2B_API_KEY`` is set, then falls
back to a strict in-process executor with tight resource limits.

Public API
----------
::

    from services.sandbox_runner import run_code

    result = await run_code(
        language="python",
        code="print('hello')",
        files={"utils.py": "def add(a, b): return a + b"},
        timeout=30,
    )
    # result = {"stdout": "hello\\n", "stderr": "", "exit_code": 0, "files": {}}
"""
from __future__ import annotations

import asyncio
import logging
import os
import resource
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_E2B_API_KEY: Optional[str] = os.environ.get("E2B_API_KEY")

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class SandboxResult:
    __slots__ = ("stdout", "stderr", "exit_code", "files", "timed_out")

    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        files: Optional[dict] = None,
        timed_out: bool = False,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.files = files or {}
        self.timed_out = timed_out

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "files": self.files,
            "timed_out": self.timed_out,
        }


# ---------------------------------------------------------------------------
# E2B backend
# ---------------------------------------------------------------------------

async def _run_via_e2b(
    language: str,
    code: str,
    files: dict,
    timeout: int,
) -> SandboxResult:
    """Execute code inside an E2B cloud sandbox.

    Requires: ``pip install e2b-code-interpreter`` and ``E2B_API_KEY`` env var.
    """
    try:
        from e2b_code_interpreter import AsyncSandbox  # type: ignore[import]
    except ImportError:
        raise RuntimeError("e2b-code-interpreter is not installed.  pip install e2b-code-interpreter")

    sandbox = await AsyncSandbox.create(api_key=_E2B_API_KEY, timeout=timeout)
    try:
        # Upload helper files first
        for rel_path, content in (files or {}).items():
            await sandbox.filesystem.write(
                f"/code/{rel_path}",
                content if isinstance(content, bytes) else content.encode(),
            )

        exec_result = await sandbox.run_code(code, language=_normalise_language(language))

        stdout = "\n".join(str(o.line) for o in (exec_result.logs.stdout or []))
        stderr = "\n".join(str(o.line) for o in (exec_result.logs.stderr or []))
        exit_code = 0 if not exec_result.error else 1
        if exec_result.error:
            stderr = (stderr + "\n" + str(exec_result.error)).strip()

        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
    finally:
        await sandbox.kill()


def _normalise_language(lang: str) -> str:
    mapping = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
    }
    return mapping.get(lang.lower(), lang.lower())


# ---------------------------------------------------------------------------
# Fallback: restricted in-process subprocess executor
# ---------------------------------------------------------------------------

_LANG_CMD: dict[str, list[str]] = {
    "python": [sys.executable, "-c"],
    "javascript": ["node", "-e"],
    "typescript": ["npx", "ts-node", "-e"],
    "bash": ["bash", "-c"],
    "sh": ["sh", "-c"],
}

_OUTPUT_LIMIT = 256 * 1024  # 256 KB


async def _run_subprocess(
    language: str,
    code: str,
    files: dict,
    timeout: int,
) -> SandboxResult:
    """Restricted subprocess executor used when E2B is unavailable.

    Runs code in a temporary directory with a wall-clock timeout and capped
    output.  Does **not** provide container isolation — use only when E2B is
    unavailable.
    """
    lang_key = _normalise_language(language)
    cmd_prefix = _LANG_CMD.get(lang_key)
    if not cmd_prefix:
        return SandboxResult(
            stderr=f"Unsupported language: {language}",
            exit_code=1,
        )

    with tempfile.TemporaryDirectory(prefix="crucibai_sandbox_") as tmpdir:
        tmp = Path(tmpdir)
        # Write helper files
        for rel_path, content in (files or {}).items():
            dest = (tmp / rel_path).resolve()
            if not str(dest).startswith(tmpdir):
                continue  # path traversal guard
            dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                dest.write_bytes(content)
            else:
                dest.write_text(content, encoding="utf-8", errors="replace")

        cmd = cmd_prefix + [code]

        def _set_limits():
            # CPU: 30 s, address space: 512 MB
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
                resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            except Exception:
                pass

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
                preexec_fn=_set_limits,
            )
            try:
                raw_stdout, raw_stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                timed_out = False
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raw_stdout = b""
                raw_stderr = b"Execution timed out"
                timed_out = True

            stdout = raw_stdout[:_OUTPUT_LIMIT].decode("utf-8", errors="replace")
            stderr = raw_stderr[:_OUTPUT_LIMIT].decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Subprocess sandbox error: %s\n%s", exc, tb)
            return SandboxResult(stderr=f"Sandbox error: {exc}", exit_code=1)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_code(
    language: str,
    code: str,
    files: Optional[dict] = None,
    timeout: int = 30,
) -> dict:
    """Execute *code* in an isolated sandbox and return a result dict.

    Parameters
    ----------
    language:
        ``"python"``, ``"javascript"``, ``"typescript"``, ``"bash"`` …
    code:
        Source code to run.
    files:
        Optional mapping of ``relative/path`` → ``str | bytes`` for helper
        files that should be available alongside the executed code.
    timeout:
        Wall-clock seconds before the sandbox is killed.

    Returns
    -------
    dict with keys ``stdout``, ``stderr``, ``exit_code``, ``files``,
    ``timed_out``.
    """
    files = files or {}
    timeout = max(1, min(timeout, 120))

    if _E2B_API_KEY:
        try:
            result = await _run_via_e2b(language, code, files, timeout)
            logger.debug(
                "E2B sandbox: lang=%s exit=%d", language, result.exit_code
            )
            return result.to_dict()
        except Exception as exc:
            logger.warning("E2B sandbox failed (%s), falling back to subprocess", exc)

    # Subprocess fallback
    result = await _run_subprocess(language, code, files, timeout)
    logger.debug(
        "Subprocess sandbox: lang=%s exit=%d", language, result.exit_code
    )
    return result.to_dict()
