"""CF27 — /api/doctor diagnostic endpoint.

Adapted from claude-code-source-code/src/commands/doctor.
Reports environment health: Python version, Node version, key env vars
presence (not values), DB pool status, and LLM provider registration.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


def _cmd_version(cmd: List[str]) -> str:
    try:
        exe = shutil.which(cmd[0])
        if not exe:
            return "not installed"
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5)
        return out.decode("utf-8", errors="replace").strip().splitlines()[0]
    except Exception as exc:
        return f"error: {exc}"


@router.get("")
def doctor() -> Dict[str, Any]:
    env_present = {
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
        "REDIS_URL": bool(os.environ.get("REDIS_URL")),
        "JWT_SECRET": bool(os.environ.get("JWT_SECRET")),
    }
    checks = [
        {"name": "python", "status": "ok", "detail": sys.version.split()[0]},
        {"name": "platform", "status": "ok", "detail": f"{platform.system()} {platform.release()}"},
        {"name": "node", "status": "ok" if shutil.which("node") else "missing",
         "detail": _cmd_version(["node", "--version"])},
        {"name": "git", "status": "ok" if shutil.which("git") else "missing",
         "detail": _cmd_version(["git", "--version"])},
    ]
    warnings: List[str] = []
    if not env_present.get("ANTHROPIC_API_KEY") and not env_present.get("OPENAI_API_KEY"):
        warnings.append("No LLM provider key present (ANTHROPIC_API_KEY or OPENAI_API_KEY).")
    if not env_present.get("DATABASE_URL"):
        warnings.append("DATABASE_URL not set — running in fallback/sqlite mode.")
    status = "ok" if not warnings else "degraded"
    return {"status": status, "checks": checks, "env_present": env_present, "warnings": warnings}
