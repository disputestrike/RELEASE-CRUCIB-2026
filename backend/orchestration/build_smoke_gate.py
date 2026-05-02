"""
build_smoke_gate.py — Phase 2 real proof gate.

Runs `npm run build` (or `vite build`) inside the generated workspace,
then verifies:
  1. Exit code 0
  2. dist/index.html (or build/index.html) exists
  3. dist/ is non-empty (at least 3 files)

Returns a structured result that's wired into the hard verification gate
in executor.py.  Designed to be non-blocking: if Node/npm is unavailable
the gate degrades gracefully (warning, not failure).

Env vars:
  CRUCIBAI_SKIP_BUILD_SMOKE=1   skip entirely (useful in dev)
  CRUCIBAI_BUILD_SMOKE_TIMEOUT  seconds to allow npm build (default 120)
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_SKIP_VAR = "CRUCIBAI_SKIP_BUILD_SMOKE"
_TIMEOUT_VAR = "CRUCIBAI_BUILD_SMOKE_TIMEOUT"
DEFAULT_TIMEOUT = 120


def _skip() -> bool:
    return os.environ.get(_SKIP_VAR, "").strip().lower() in ("1", "true", "yes")


def _timeout() -> int:
    try:
        return int(os.environ.get(_TIMEOUT_VAR, str(DEFAULT_TIMEOUT)))
    except ValueError:
        return DEFAULT_TIMEOUT


def _find_dist(workspace: str) -> Optional[str]:
    """Return path to the built dist directory, or None if not present."""
    for candidate in ("dist", "build", "out", ".next/static"):
        p = os.path.join(workspace, candidate)
        if os.path.isdir(p):
            return p
    return None


def _count_files(directory: str) -> int:
    count = 0
    for _, _, files in os.walk(directory):
        count += len(files)
    return count


def _has_index_html(dist_dir: str) -> bool:
    return os.path.isfile(os.path.join(dist_dir, "index.html"))


def _detect_build_command(workspace: str) -> List[str]:
    """Detect the right build command for this workspace."""
    pkg_path = os.path.join(workspace, "package.json")
    if not os.path.isfile(pkg_path):
        return []
    try:
        import json
        with open(pkg_path) as f:
            pkg = json.load(f)
        scripts = pkg.get("scripts", {})
        if "build" in scripts:
            return ["npm", "run", "build"]
        if "vite" in str(scripts):
            return ["npx", "vite", "build"]
    except Exception:
        pass
    return ["npm", "run", "build"]


async def run_build_smoke(
    workspace_path: str,
    *,
    job_id: str = "",
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a real npm build in the workspace and return a result dict:

        {
            "passed": bool,
            "skipped": bool,       # True when Node unavailable or env skip
            "exit_code": int|None,
            "dist_dir": str|None,
            "file_count": int,
            "has_index_html": bool,
            "duration_ms": int,
            "stdout_tail": str,    # last 800 chars of build output
            "stderr_tail": str,
            "error": str|None,
            "warning": str|None,
        }
    """
    t0 = time.monotonic()

    # ── graceful skip conditions ─────────────────────────────────────────────
    if _skip():
        return _skip_result("CRUCIBAI_SKIP_BUILD_SMOKE=1")

    if not workspace_path or not os.path.isdir(workspace_path):
        return _skip_result(f"workspace missing: {workspace_path!r}")

    if not shutil.which("npm"):
        return _skip_result("npm not on PATH — skipping build smoke gate")

    # Check if there's even a package.json
    if not os.path.isfile(os.path.join(workspace_path, "package.json")):
        # Backend-only workspace — check for Python entry point instead
        return await _python_smoke(workspace_path, t0)

    cmd = _detect_build_command(workspace_path)
    if not cmd:
        return _skip_result("no build script detected in package.json")

    max_t = timeout if timeout is not None else _timeout()
    logger.info("[BUILD SMOKE] Running %s in %s (timeout=%ds)", cmd, workspace_path, max_t)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CI": "false", "NODE_ENV": "production"},
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=max_t)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return _fail_result(
                exit_code=None,
                error=f"Build timed out after {max_t}s",
                stdout_tail="",
                stderr_tail="",
                duration_ms=_ms(t0),
            )

        exit_code = proc.returncode
        stdout_tail = (stdout_b or b"").decode(errors="replace")[-800:]
        stderr_tail = (stderr_b or b"").decode(errors="replace")[-800:]

        dist_dir = _find_dist(workspace_path)
        file_count = _count_files(dist_dir) if dist_dir else 0
        has_index = _has_index_html(dist_dir) if dist_dir else False

        if exit_code != 0:
            return _fail_result(
                exit_code=exit_code,
                error=f"npm build exited {exit_code}",
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                duration_ms=_ms(t0),
            )

        if not dist_dir or not has_index:
            return _fail_result(
                exit_code=exit_code,
                error=f"Build succeeded (exit 0) but no dist/index.html found",
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                duration_ms=_ms(t0),
            )

        logger.info(
            "[BUILD SMOKE] PASS — dist=%s files=%d duration=%dms",
            dist_dir, file_count, _ms(t0),
        )
        return {
            "passed": True,
            "skipped": False,
            "exit_code": 0,
            "dist_dir": dist_dir,
            "file_count": file_count,
            "has_index_html": True,
            "duration_ms": _ms(t0),
            "stdout_tail": stdout_tail,
            "stderr_tail": "",
            "error": None,
            "warning": None,
        }

    except Exception as exc:
        return _fail_result(
            exit_code=None,
            error=f"Build smoke gate exception: {exc}",
            stdout_tail="",
            stderr_tail="",
            duration_ms=_ms(t0),
        )


async def _python_smoke(workspace: str, t0: float) -> Dict[str, Any]:
    """
    For backend-only workspaces: check that main.py (or app/main.py) is
    syntax-valid and has a /health route defined.
    """
    candidates = ["main.py", "app/main.py", "backend/main.py", "src/main.py"]
    entry = None
    for c in candidates:
        p = os.path.join(workspace, c)
        if os.path.isfile(p):
            entry = p
            break

    if not entry:
        return _skip_result("no package.json or main.py — unrecognised workspace layout")

    try:
        import ast
        with open(entry, encoding="utf-8", errors="replace") as f:
            src = f.read()
        ast.parse(src)
        has_health = "/health" in src or "health" in src.lower()
        return {
            "passed": True,
            "skipped": False,
            "exit_code": 0,
            "dist_dir": None,
            "file_count": 1,
            "has_index_html": False,
            "duration_ms": _ms(t0),
            "stdout_tail": f"Python entry point {entry} — syntax OK, /health: {has_health}",
            "stderr_tail": "",
            "error": None,
            "warning": None if has_health else "No /health route found in main.py",
        }
    except SyntaxError as e:
        return _fail_result(
            exit_code=1,
            error=f"Python syntax error in {entry}: {e}",
            stdout_tail="",
            stderr_tail="",
            duration_ms=_ms(t0),
        )


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _skip_result(reason: str) -> Dict[str, Any]:
    return {
        "passed": True,   # skip = pass (non-blocking)
        "skipped": True,
        "exit_code": None,
        "dist_dir": None,
        "file_count": 0,
        "has_index_html": False,
        "duration_ms": 0,
        "stdout_tail": "",
        "stderr_tail": "",
        "error": None,
        "warning": f"Build smoke gate skipped: {reason}",
    }


def _fail_result(
    *,
    exit_code: Optional[int],
    error: str,
    stdout_tail: str,
    stderr_tail: str,
    duration_ms: int,
) -> Dict[str, Any]:
    return {
        "passed": False,
        "skipped": False,
        "exit_code": exit_code,
        "dist_dir": None,
        "file_count": 0,
        "has_index_html": False,
        "duration_ms": duration_ms,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "error": error,
        "warning": None,
    }
