"""
Structured Auto-Runner preflight report (preflight_report.json shape in job events).
Emitted before DAG execution so operators see pass/fail per dependency.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Dict, List

from .browser_preview_verify import playwright_chromium_status, skip_browser_preview_env
from .runtime_health import (
    collect_runtime_health_sync,
    extended_autorunner_preflight_issues,
    skip_node_verify_env,
)


def _recommended_fix(check_id: str, ok: bool, **ctx) -> str:
    if ok:
        return ""
    fixes = {
        "python": "Install Python 3.11+ and ensure the interpreter used to run the API is on PATH.",
        "node": "Install Node.js LTS and add it to PATH, or set CRUCIBAI_SKIP_NODE_VERIFY=1 for local dev only.",
        "npm": "Install Node.js (npm ships with it) or use a version manager (nvm, fnm).",
        "pnpm": "Optional: npm install -g pnpm if your workspace uses pnpm.",
        "yarn": "Optional: npm install -g yarn if your workspace uses yarn.",
        "git": "Install Git and ensure `git` is on PATH (clone/patch workflows).",
        "docker": "Optional for local DBs: install Docker Desktop and run docker compose up -d postgres redis.",
        "playwright_python": (
            "pip install playwright && python -m playwright install chromium "
            "(or set CRUCIBAI_SKIP_BROWSER_PREVIEW=1 to skip headless UI gate)."
        ),
        "database_url": "Set DATABASE_URL in backend/.env (e.g. postgresql://… from docker-compose).",
    }
    return fixes.get(
        check_id,
        "See issues[] for this preflight run; fix listed dependencies or use documented skip flags for dev.",
    )


async def build_preflight_report() -> Dict[str, Any]:
    """
    Single JSON-serializable object: checks[], issues[], passed, schema version.
    """
    sync = collect_runtime_health_sync()
    issues: List[str] = await extended_autorunner_preflight_issues()
    checks: List[Dict[str, Any]] = []

    py = sync.get("python") or {}
    py_ok = bool(py.get("available"))
    checks.append(
        {
            "id": "python",
            "ok": py_ok,
            "version": py.get("version") or "",
            "executable": (py.get("executable") or "")[:200],
            "recommended_fix": _recommended_fix("python", py_ok),
        }
    )

    node = sync.get("node") or {}
    node_ok = bool(node.get("available"))
    checks.append(
        {
            "id": "node",
            "ok": node_ok,
            "path": (node.get("path") or "")[:300],
            "version": (node.get("version") or "")[:80],
            "verify_skipped": skip_node_verify_env(),
            "recommended_fix": _recommended_fix(
                "node", node_ok or skip_node_verify_env()
            ),
        }
    )

    npm = sync.get("npm") or {}
    npm_ok = bool(npm.get("available"))
    checks.append(
        {
            "id": "npm",
            "ok": npm_ok,
            "path": (npm.get("path") or "")[:300],
            "recommended_fix": _recommended_fix("npm", npm_ok),
        }
    )

    pnpm = shutil.which("pnpm") or ""
    yarn = shutil.which("yarn") or ""
    pnpm_ok = bool(pnpm)
    yarn_ok = bool(yarn)
    checks.append(
        {
            "id": "pnpm",
            "ok": pnpm_ok,
            "path": pnpm[:300],
            "optional": True,
            "recommended_fix": _recommended_fix("pnpm", pnpm_ok),
        }
    )
    checks.append(
        {
            "id": "yarn",
            "ok": yarn_ok,
            "path": yarn[:300],
            "optional": True,
            "recommended_fix": _recommended_fix("yarn", yarn_ok),
        }
    )

    git_ok = bool(shutil.which("git"))
    checks.append(
        {
            "id": "git",
            "ok": git_ok,
            "path": (shutil.which("git") or "")[:300],
            "recommended_fix": _recommended_fix("git", git_ok),
        }
    )

    docker_ok = bool(shutil.which("docker"))
    checks.append(
        {
            "id": "docker",
            "ok": docker_ok,
            "optional": True,
            "recommended_fix": _recommended_fix("docker", docker_ok),
        }
    )

    pw_status = await asyncio.to_thread(playwright_chromium_status)
    playwright_pkg = bool(pw_status.get("package_available"))
    playwright_chromium = bool(pw_status.get("chromium_available"))
    pw_ok = playwright_pkg or skip_browser_preview_env()
    chromium_ok = playwright_chromium or skip_browser_preview_env()
    checks.append(
        {
            "id": "playwright_python",
            "ok": pw_ok,
            "browser_preview_skipped": skip_browser_preview_env(),
            "recommended_fix": _recommended_fix("playwright_python", pw_ok),
        }
    )
    checks.append(
        {
            "id": "playwright_chromium",
            "ok": chromium_ok,
            "browser_preview_skipped": skip_browser_preview_env(),
            "executable_path": (pw_status.get("executable_path") or "")[:300],
            "error": (pw_status.get("error") or "")[:300],
            "recommended_fix": _recommended_fix("playwright_python", chromium_ok),
        }
    )
    if not chromium_ok:
        issues.append(
            "Playwright Chromium not available. Run: python -m playwright install chromium"
        )

    db_ok = bool(os.environ.get("DATABASE_URL", "").strip())
    checks.append(
        {
            "id": "database_url",
            "ok": db_ok,
            "recommended_fix": _recommended_fix("database_url", db_ok),
        }
    )

    return {
        "schema": "crucibai.preflight/v1",
        "passed": len(issues) == 0,
        "issues": issues,
        "checks": checks,
        "env_flags": {
            "CRUCIBAI_DEV": os.environ.get("CRUCIBAI_DEV", ""),
            "CRUCIBAI_SKIP_NODE_VERIFY": os.environ.get(
                "CRUCIBAI_SKIP_NODE_VERIFY", ""
            ),
            "CRUCIBAI_SKIP_BROWSER_PREVIEW": os.environ.get(
                "CRUCIBAI_SKIP_BROWSER_PREVIEW", ""
            ),
            "CRUCIBAI_SKIP_AUTORUNNER_PREFLIGHT": os.environ.get(
                "CRUCIBAI_SKIP_AUTORUNNER_PREFLIGHT", ""
            ),
        },
    }
