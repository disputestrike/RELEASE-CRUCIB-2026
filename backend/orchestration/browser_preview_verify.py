"""
Headless browser verification: npm install, vite build, serve dist, Playwright checks.

Playwright's sync API must never run on the asyncio event-loop thread (Playwright raises
if it detects a running loop). We therefore run the **entire** npm + sync Playwright
pipeline in ``asyncio.to_thread`` via ``_verify_browser_preview_sync``.

The public ``verify_browser_preview`` is async only so ``preview_gate`` / ``verifier``
can ``await`` it without blocking the loop for minutes.
"""

import asyncio
import json
import logging
import os
import shutil
import socket
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.orchestration.trust.trust_scoring import sha256_file_preview
except ImportError:
    try:
        from backend.orchestration.trust.trust_scoring import sha256_file_preview
    except ImportError:
        def sha256_file_preview(*a, **kw): return ""

logger = logging.getLogger(__name__)


def skip_browser_preview_env() -> bool:
    return os.environ.get("CRUCIBAI_SKIP_BROWSER_PREVIEW", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def playwright_chromium_status() -> Dict[str, Any]:
    """Check whether the Playwright package and Chromium browser binary are available."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "package_available": False,
            "chromium_available": False,
            "executable_path": "",
            "error": "playwright package not installed",
        }
    try:
        with sync_playwright() as p:
            exe = p.chromium.executable_path
            return {
                "package_available": True,
                "chromium_available": bool(exe and os.path.exists(exe)),
                "executable_path": exe or "",
                "error": (
                    ""
                    if exe and os.path.exists(exe)
                    else "chromium browser binary missing"
                ),
            }
    except Exception as exc:
        return {
            "package_available": True,
            "chromium_available": False,
            "executable_path": "",
            "error": str(exc)[:300],
        }


def _proof(
    kind: str,
    title: str,
    payload: Dict[str, Any],
    *,
    verification_class: str = "experience",
) -> Dict[str, Any]:
    p = {**payload, "verification_class": verification_class}
    return {"proof_type": kind, "title": title, "payload": p}


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve_dist(dist_dir: str) -> Tuple[ThreadingHTTPServer, threading.Thread, int]:
    port = _free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=dist_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread, port


def _run_npm(args: List[str], cwd: str, timeout: int) -> Tuple[int, str]:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")
    if not npm:
        return -1, "npm not found on PATH"
    try:
        r = subprocess.run(
            [npm, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
            shell=False,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out[-4000:]
    except subprocess.TimeoutExpired:
        return -1, f"npm {' '.join(args)} timed out after {timeout}s"
    except OSError as e:
        return -1, str(e)


def _run_build_with_autofix(ws: str, build_timeout: int) -> Tuple[int, str, List[Dict[str, Any]]]:
    attempts: List[Dict[str, Any]] = []
    code, log = _run_npm(["run", "build"], ws, build_timeout)
    if code == 0:
        return code, log, attempts

    try:
        max_attempts = max(0, min(5, int(os.environ.get("CRUCIBAI_NPM_BUILD_AUTOFIX_ATTEMPTS", "2"))))
    except ValueError:
        max_attempts = 2
    if max_attempts <= 0:
        return code, log, attempts

    try:
        from backend.orchestration.npm_build_autofix import repair_npm_build_failure
    except Exception as exc:
        attempts.append({"changed_files": [], "reason": "autofix_unavailable", "error": str(exc)[:300]})
        return code, log, attempts

    for attempt_index in range(1, max_attempts + 1):
        repair = repair_npm_build_failure(ws, log)
        repair["attempt"] = attempt_index
        attempts.append(repair)
        if not repair.get("changed_files"):
            break
        code, log = _run_npm(["run", "build"], ws, build_timeout)
        if code == 0:
            break
    return code, log, attempts


def _verify_browser_preview_sync(workspace_path: str) -> Dict[str, Any]:
    """
    Full browser preview on a worker thread only. Uses sync Playwright (allowed here).
    """
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    ws = (workspace_path or "").strip()
    if not ws or not os.path.isdir(ws):
        issues.append("Browser preview: invalid workspace path.")
        return {"passed": False, "issues": issues, "proof": proof}

    pkg_path = os.path.join(ws, "package.json")
    if not os.path.isfile(pkg_path):
        issues.append("Browser preview: package.json missing.")
        return {"passed": False, "issues": issues, "proof": proof}

    try:
        with open(pkg_path, encoding="utf-8") as fh:
            pkg = json.load(fh)
    except json.JSONDecodeError as e:
        issues.append(f"Browser preview: package.json invalid JSON: {e}")
        return {"passed": False, "issues": issues, "proof": proof}

    scripts = pkg.get("scripts") or {}
    if not scripts.get("build"):
        issues.append(
            "Browser preview: add scripts.build (e.g. vite build) to package.json.",
        )
        return {"passed": False, "issues": issues, "proof": proof}

    install_timeout = int(os.environ.get("CRUCIBAI_NPM_INSTALL_TIMEOUT", "300"))
    build_timeout = int(os.environ.get("CRUCIBAI_NPM_BUILD_TIMEOUT", "180"))

    # Railway often runs with NODE_ENV=production; npm then omits devDependencies
    # unless we explicitly include them. Vite lives in devDependencies for generated apps.
    code, log = _run_npm(
        ["install", "--include=dev", "--no-fund", "--no-audit", "--legacy-peer-deps"], ws, install_timeout
    )
    if code != 0:
        # Retry without --legacy-peer-deps as a fallback
        code2, log2 = _run_npm(
            ["install", "--include=dev", "--no-fund", "--no-audit"], ws, install_timeout
        )
        if code2 == 0:
            code, log = code2, log2
        else:
            issues.append(f"npm install failed (exit {code}): {log[:500]}")
            return {"passed": False, "issues": issues, "proof": proof}
    proof.append(
        _proof(
            "verification",
            "npm install completed",
            {"exit": code},
            verification_class="runtime",
        )
    )

    code, log, repair_attempts = _run_build_with_autofix(ws, build_timeout)
    if repair_attempts:
        proof.append(
            _proof(
                "verification",
                "npm build deterministic autofix attempts",
                {"attempts": repair_attempts},
                verification_class="runtime",
            )
        )
    if code != 0:
        issues.append(f"npm run build failed (exit {code}): {log[:800]}")
        return {"passed": False, "issues": issues, "proof": proof}
    proof.append(
        _proof(
            "verification",
            "npm run build completed",
            {"exit": code},
            verification_class="runtime",
        )
    )

    dist_dir = os.path.join(ws, "dist")
    if not os.path.isfile(os.path.join(dist_dir, "index.html")):
        issues.append("Browser preview: dist/index.html missing after build.")
        return {"passed": False, "issues": issues, "proof": proof}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        issues.append(
            "Playwright Python package missing. pip install playwright && "
            "python -m playwright install chromium",
        )
        return {"passed": False, "issues": issues, "proof": proof}

    httpd: Optional[ThreadingHTTPServer] = None
    base = ""
    try:
        httpd, _thr, port = _serve_dist(dist_dir)
        base = f"http://127.0.0.1:{port}/"
        console_errors: List[str] = []
        page_errors: List[str] = []

        with sync_playwright() as p:
            browser = None
            try:
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as e:
                    logger.warning("playwright chromium launch failed: %s", e)
                    issues.append(
                        "Playwright Chromium not available. Run: python -m playwright install chromium",
                    )
                    return {"passed": False, "issues": issues, "proof": proof}

                page = browser.new_page()

                def on_console(msg) -> None:
                    if msg.type == "error":
                        console_errors.append(msg.text)

                def on_page_error(exc) -> None:
                    page_errors.append(str(exc))

                page.on("console", on_console)
                page.on("pageerror", on_page_error)

                page.goto(base, wait_until="load", timeout=90000)
                page.wait_for_selector("#root", timeout=30000)
                root_text = page.locator("#root").inner_text(timeout=10000).strip()
                if len(root_text) < 3:
                    issues.append(
                        "Browser preview: #root has almost no visible text after load.",
                    )
                proof.append(
                    _proof(
                        "verification",
                        "Playwright: root rendered",
                        {"root_len": len(root_text)},
                    ),
                )

                home_links = page.get_by_role("link", name="Home")
                login_links = page.get_by_role("link", name="Login")
                if home_links.count() > 0 and login_links.count() > 0:
                    page.get_by_role("link", name="Home").first.wait_for(
                        state="visible",
                        timeout=15000,
                    )
                    page.get_by_role("link", name="Login").first.click(timeout=15000)
                    page.get_by_placeholder("Display name").wait_for(
                        state="visible",
                        timeout=15000,
                    )
                    page.get_by_placeholder("Display name").fill("gate_e2e")
                    page.get_by_role("button", name="Sign in (demo)").click()
                    page.get_by_role("heading", name="Dashboard").wait_for(
                        state="visible",
                        timeout=15000,
                    )
                    proof.append(
                        _proof(
                            "verification",
                            "Playwright: login -> dashboard flow",
                            {"flow": "demo_auth"},
                        ),
                    )
                else:
                    proof.append(
                        _proof(
                            "verification",
                            "Playwright: generic root render only",
                            {"flow": "generic_render_only"},
                        ),
                    )

                try:
                    preview_dir = os.path.join(ws, ".crucibai", "preview")
                    os.makedirs(preview_dir, exist_ok=True)
                    shot_path = os.path.join(preview_dir, "screenshot.png")
                    page.screenshot(path=shot_path, full_page=False)
                    h = sha256_file_preview(shot_path)
                    sz = os.path.getsize(shot_path) if os.path.isfile(shot_path) else 0
                    proof.append(
                        _proof(
                            "verification",
                            "Preview screenshot captured",
                            {
                                "kind": "preview_screenshot",
                                "relative_path": ".crucibai/preview/screenshot.png",
                                "sha256_prefix": h,
                                "bytes": sz,
                            },
                        ),
                    )
                except Exception as se:
                    logger.warning("browser preview screenshot failed: %s", se)
                    proof.append(
                        _proof(
                            "verification",
                            "Preview screenshot not captured (non-fatal)",
                            {
                                "kind": "preview_screenshot_error",
                                "error": str(se)[:300],
                            },
                            verification_class="experience",
                        ),
                    )
            except Exception as e:
                logger.exception("browser preview playwright step failed")
                issues.append(f"Playwright E2E failed: {str(e)[:400]}")
            finally:
                if browser:
                    browser.close()

        if page_errors:
            issues.append(f"Browser page errors: {'; '.join(page_errors[:5])}")
        if console_errors:
            issues.append(f"Browser console errors: {'; '.join(console_errors[:8])}")

    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()

    passed = len(issues) == 0
    if passed and base:
        proof.append(
            _proof("verification", "Browser preview gate passed", {"url": base}),
        )
    return {"passed": passed, "issues": issues, "proof": proof}


def _materialize_dist_without_playwright(workspace_path: str) -> Dict[str, Any]:
    """Build dist/index.html even when Chromium verification is disabled."""
    proof: List[Dict[str, Any]] = []
    ws = (workspace_path or "").strip()
    if not ws or not os.path.isdir(ws):
        return {
            "passed": False,
            "issues": ["Preview build: invalid workspace path."],
            "proof": proof,
        }

    dist_index = os.path.join(ws, "dist", "index.html")
    if os.path.isfile(dist_index):
        proof.append(
            _proof(
                "verification",
                "Preview artifact already materialized",
                {"relative_path": "dist/index.html"},
                verification_class="runtime",
            )
        )
        return {"passed": True, "issues": [], "proof": proof}

    pkg_path = os.path.join(ws, "package.json")
    if not os.path.isfile(pkg_path):
        return {
            "passed": False,
            "issues": ["Preview build: package.json missing."],
            "proof": proof,
        }

    try:
        with open(pkg_path, encoding="utf-8") as fh:
            pkg = json.load(fh)
    except json.JSONDecodeError as e:
        return {
            "passed": False,
            "issues": [f"Preview build: package.json invalid JSON: {e}"],
            "proof": proof,
        }

    if not (pkg.get("scripts") or {}).get("build"):
        return {
            "passed": False,
            "issues": ["Preview build: add scripts.build to package.json."],
            "proof": proof,
        }

    install_timeout = int(os.environ.get("CRUCIBAI_NPM_INSTALL_TIMEOUT", "300"))
    build_timeout = int(os.environ.get("CRUCIBAI_NPM_BUILD_TIMEOUT", "180"))

    code, log = _run_npm(["install", "--include=dev", "--no-fund", "--no-audit", "--legacy-peer-deps"], ws, install_timeout)
    if code != 0:
        # Retry without --legacy-peer-deps as a fallback
        code2, log2 = _run_npm(["install", "--include=dev", "--no-fund", "--no-audit"], ws, install_timeout)
        if code2 == 0:
            code, log = code2, log2
        else:
            return {
                "passed": False,
                "issues": [f"npm install failed (exit {code}): {log[:500]}"],
                "proof": proof,
            }
    proof.append(
        _proof(
            "verification",
            "npm install completed",
            {"exit": code},
            verification_class="runtime",
        )
    )

    code, log, repair_attempts = _run_build_with_autofix(ws, build_timeout)
    if repair_attempts:
        proof.append(
            _proof(
                "verification",
                "npm build deterministic autofix attempts",
                {"attempts": repair_attempts},
                verification_class="runtime",
            )
        )
    if code != 0:
        return {
            "passed": False,
            "issues": [f"npm run build failed (exit {code}): {log[:800]}"],
            "proof": proof,
        }
    proof.append(
        _proof(
            "verification",
            "npm run build completed",
            {"exit": code},
            verification_class="runtime",
        )
    )

    if not os.path.isfile(dist_index):
        return {
            "passed": False,
            "issues": ["Preview build: dist/index.html missing after npm run build."],
            "proof": proof,
        }

    proof.append(
        _proof(
            "verification",
            "Preview artifact materialized",
            {"relative_path": "dist/index.html"},
            verification_class="runtime",
        )
    )
    return {"passed": True, "issues": [], "proof": proof}


async def verify_browser_preview(workspace_path: str) -> Dict[str, Any]:
    """
    npm install + npm run build + Playwright E2E. Runs heavy work off the event loop.
    """
    if skip_browser_preview_env():
        result = await asyncio.to_thread(_materialize_dist_without_playwright, workspace_path)
        result.setdefault("proof", []).append(
            _proof(
                "verification",
                "Chromium browser preview skipped; static preview build still enforced",
                {"env": "CRUCIBAI_SKIP_BROWSER_PREVIEW"},
                verification_class="runtime",
            )
        )
        return result
    return await asyncio.to_thread(_verify_browser_preview_sync, workspace_path)
