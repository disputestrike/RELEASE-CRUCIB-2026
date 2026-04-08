"""
Runtime health for Auto-Runner: same interpreters the verifier/executor rely on.
Fail fast before jobs start instead of deep into backend.models.
"""
import asyncio
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def _version_line(cmd: str, *args: str, timeout: float = 6.0) -> Optional[str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            return None
        return (out or b"").decode(errors="replace").strip().split("\n")[0] or None
    except Exception:
        return None


def collect_runtime_health_sync() -> Dict[str, Any]:
    """Synchronous subset for cheap checks (no subprocess version probes)."""
    py_exe = sys.executable or ""
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    return {
        "python": {
            "available": bool(py_exe and os.path.isfile(py_exe)),
            "executable": py_exe,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "node": {
            "available": bool(node_path),
            "path": node_path or "",
        },
        "npm": {
            "available": bool(npm_path),
            "path": npm_path or "",
        },
    }


async def collect_runtime_health() -> Dict[str, Any]:
    """Full check including --version subprocesses (node may be slow first call)."""
    base = collect_runtime_health_sync()
    node_v = None
    if base["node"]["available"]:
        node_v = await _version_line("node", "--version")
    return {
        **base,
        "node": {**base["node"], "version": node_v or ""},
        "checks_passed": bool(
            base["python"]["available"] and base["node"]["available"]
        ),
    }


def skip_node_verify_env() -> bool:
    """When True, Auto-Runner does not require Node and skips `node --check` in the verifier."""
    return os.environ.get("CRUCIBAI_SKIP_NODE_VERIFY", "").strip().lower() in (
        "1", "true", "yes",
    )


def default_api_healthcheck_url() -> str:
    """Local API health URL used by the Auto-Runner preflight.

    Railway injects PORT dynamically, so a hard-coded 8000 check can report a
    false preflight failure even when the container is healthy.
    """
    explicit = os.environ.get("CRUCIBAI_HEALTHCHECK_URL", "").strip()
    if explicit:
        return explicit
    port = os.environ.get("PORT", "").strip() or "8000"
    return f"http://127.0.0.1:{port}/api/health"


def runtime_issues_for_autorunner(sync_report: Dict[str, Any]) -> List[str]:
    """Human-readable blockers for starting an Auto-Runner job."""
    issues: List[str] = []
    if not sync_report.get("python", {}).get("available"):
        issues.append(
            "Python interpreter not available (sys.executable invalid). "
            "The API must be started with a working Python."
        )
    if not skip_node_verify_env() and not sync_report.get("node", {}).get("available"):
        issues.append(
            "Node.js not found on PATH. Auto-Runner verifies frontend files with "
            "`node --check`. Install Node LTS and restart the terminal, or set "
            "CRUCIBAI_SKIP_NODE_VERIFY=1 only if you accept skipped JS syntax checks."
        )
    return issues


async def extended_autorunner_preflight_issues() -> List[str]:
    """
    Harder gate: pip/npm invocations, API health URL, optional CRA dev server.

    In CRUCIBAI_DEV=1 this returns no issues so local "Run" is not blocked when Node/npm
    are missing from the API process PATH (common on Windows). Use production without
    CRUCIBAI_DEV, or set CRUCIBAI_SKIP_AUTORUNNER_PREFLIGHT=1 explicitly.
    """
    if os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes"):
        return []
    if os.environ.get("CRUCIBAI_SKIP_AUTORUNNER_PREFLIGHT", "").strip().lower() in (
        "1", "true", "yes",
    ):
        return []
    issues: List[str] = list(runtime_issues_for_autorunner(collect_runtime_health_sync()))

    pip_v = await _version_line(sys.executable, "-m", "pip", "--version")
    if not pip_v:
        issues.append(
            "pip not available via `python -m pip` — dependency installs will fail.",
        )

    if shutil.which("npm"):
        npm_v = await _version_line("npm", "--version")
        if not npm_v:
            issues.append("`npm --version` failed — package manager may be broken.")
    else:
        if not skip_node_verify_env():
            issues.append("npm not on PATH (often installed with Node).")

    if os.environ.get("CRUCIBAI_SKIP_HEALTHCHECK", "").strip().lower() not in (
        "1", "true", "yes",
    ):
        health_url = default_api_healthcheck_url()
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(health_url)
                if r.status_code >= 400:
                    issues.append(
                        f"API health check returned HTTP {r.status_code} for {health_url}",
                    )
        except Exception as e:
            issues.append(
                f"API health check failed for {health_url}: {str(e)[:160]}",
            )

    if os.environ.get("CRUCIBAI_REQUIRE_BROWSER_PREVIEW", "").strip().lower() in (
        "1", "true", "yes",
    ):
        from .browser_preview_verify import playwright_chromium_status

        pw_status = await asyncio.to_thread(playwright_chromium_status)
        if not pw_status.get("package_available"):
            issues.append(
                "CRUCIBAI_REQUIRE_BROWSER_PREVIEW is set but the playwright package "
                "is not installed (pip install playwright; python -m playwright install chromium).",
            )
        elif not pw_status.get("chromium_available"):
            issues.append(
                "CRUCIBAI_REQUIRE_BROWSER_PREVIEW is set but Playwright Chromium is not installed "
                "(python -m playwright install chromium).",
            )

    if os.environ.get("CRUCIBAI_REQUIRE_DEV_SERVER", "").strip().lower() in (
        "1", "true", "yes",
    ):
        fe = os.environ.get(
            "CRUCIBAI_FRONTEND_DEV_URL",
            "http://127.0.0.1:3000",
        )
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(fe)
                if r.status_code >= 400:
                    issues.append(
                        f"Frontend dev server HTTP {r.status_code} at {fe}",
                    )
        except Exception as e:
            issues.append(
                f"Frontend dev server not reachable at {fe}: {str(e)[:120]}",
            )

    return issues


def is_infrastructure_failure(error_message: str) -> bool:
    """True when retries will not help (missing runtimes, OS errors)."""
    msg = (error_message or "").lower()
    patterns = (
        "python was not found",
        "python3 was not found",
        "'python' is not recognized",
        "'python3' is not recognized",
        "cannot find python",
        "node' is not recognized",
        "node was not found",
        "'node' is not recognized",
        "errno 2",  # no such file on POSIX spawn
        "winerror 2",
        "no such file or directory",
        "system cannot find the file",
        "interpreter not found",
    )
    return any(p in msg for p in patterns)
