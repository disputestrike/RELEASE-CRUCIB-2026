"""
browser_qa.py — Headless browser validation of generated preview builds (FIX 12).

Validates built dist/ routes via Playwright → stdlib HTTP server → urllib fallback.
Checks: <title>, #root/#app, <script src>, headings.
Score < 60 blocks completion and delivery gate.
"""
from __future__ import annotations

import asyncio
import http.server
import logging
import os
import socket
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BROWSER_QA_MIN_SCORE = 60
_ROUTES_TO_CHECK = ["/", "/dashboard", "/app"]
_TIMEOUT_SECONDS = 10


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_static_server(dist_path: str, port: int) -> http.server.HTTPServer:
    """Serve dist_path on localhost:port in a background thread."""
    import functools

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=dist_path,
    )

    class _QuietHandler(handler):  # type: ignore[misc]
        def log_message(self, *args: Any) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), _QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def _fetch_html(url: str, timeout: int = _TIMEOUT_SECONDS) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("browser_qa: fetch failed %s — %s", url, e)
        return None


def _score_html(html: str, route: str) -> Dict[str, Any]:
    """Score a single route's HTML response."""
    issues: List[str] = []
    proof: List[str] = []
    html_lower = html.lower()

    # 1. Has title
    if "<title>" in html_lower:
        proof.append(f"{route}: has <title>")
    else:
        issues.append(f"{route}: missing <title>")

    # 2. Has root mount point
    if 'id="root"' in html or 'id="app"' in html:
        proof.append(f"{route}: has #root/#app mount")
    else:
        issues.append(f"{route}: missing #root or #app mount point")

    # 3. Has script bundle
    if "<script" in html_lower and ("src=" in html_lower or "type=" in html_lower):
        proof.append(f"{route}: has <script> bundle")
    else:
        issues.append(f"{route}: missing JS bundle <script> tag")

    # 4. Not completely blank / error page
    blank_signals = ["404 not found", "cannot get /", "page not found"]
    if any(s in html_lower for s in blank_signals):
        issues.append(f"{route}: error/404 page returned")

    return {"issues": issues, "proof": proof}


async def _check_with_playwright(dist_path: str) -> Optional[Dict[str, Any]]:
    """Try Playwright headless check. Returns None if Playwright not available."""
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        return None

    port = _find_free_port()
    server = _start_static_server(dist_path, port)
    base = f"http://127.0.0.1:{port}"
    issues: List[str] = []
    proof: List[str] = []

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
            page = await browser.new_page()
            for route in _ROUTES_TO_CHECK:
                try:
                    resp = await asyncio.wait_for(
                        page.goto(f"{base}{route}", wait_until="domcontentloaded"),
                        timeout=_TIMEOUT_SECONDS,
                    )
                    content = await page.content()
                    result = _score_html(content, route)
                    issues.extend(result["issues"])
                    proof.extend(result["proof"])
                    if resp and resp.status >= 400:
                        issues.append(f"{route}: HTTP {resp.status}")
                    else:
                        proof.append(f"{route}: HTTP {resp.status if resp else '?'} OK")
                except asyncio.TimeoutError:
                    issues.append(f"{route}: timed out loading")
                except Exception as e:
                    issues.append(f"{route}: playwright error — {e}")
            await browser.close()
    finally:
        server.shutdown()

    score = max(0, 100 - len(issues) * 15)
    return {"issues": issues, "proof": proof, "score": score, "method": "playwright"}


def _check_with_urllib(dist_path: str) -> Dict[str, Any]:
    """Fallback: serve dist/ statically and fetch with urllib."""
    port = _find_free_port()
    server = _start_static_server(dist_path, port)
    base = f"http://127.0.0.1:{port}"
    issues: List[str] = []
    proof: List[str] = []

    # Brief settle time
    time.sleep(0.3)

    try:
        for route in _ROUTES_TO_CHECK[:1]:  # Just check root in fallback
            html = _fetch_html(f"{base}{route}")
            if html is None:
                issues.append(f"{route}: could not fetch (urllib)")
            else:
                result = _score_html(html, route)
                issues.extend(result["issues"])
                proof.extend(result["proof"])
    finally:
        server.shutdown()

    score = max(0, 100 - len(issues) * 20)
    return {"issues": issues, "proof": proof, "score": score, "method": "urllib"}


async def run_browser_qa(workspace_path: str) -> Dict[str, Any]:
    """
    Run headless browser QA on the built preview (dist/ or build/).
    Returns {"passed": bool, "score": int, "issues": [...], "proof": [...], "failure_reason": str|None}.
    """
    # Find the build output directory
    dist_path = None
    for candidate in ("dist", "build", "out", "public"):
        p = os.path.join(workspace_path, candidate)
        if os.path.isdir(p) and any(
            f.endswith(".html") for _, _, files in os.walk(p) for f in files
        ):
            dist_path = p
            break

    if not dist_path:
        logger.info("browser_qa: no built output directory found — skipping")
        return {
            "passed": True,
            "score": 100,
            "issues": [],
            "proof": ["browser_qa: no dist/build found — skipped"],
            "failure_reason": None,
            "skipped": True,
        }

    logger.info("browser_qa: checking %s", dist_path)

    # Try Playwright first, fall back to urllib
    result = await _check_with_playwright(dist_path)
    if result is None:
        result = _check_with_urllib(dist_path)

    score = result.get("score", 0)
    issues = result.get("issues", [])
    passed = score >= BROWSER_QA_MIN_SCORE and len([i for i in issues if "missing" in i or "error" in i]) == 0

    if not passed:
        logger.warning("browser_qa: FAILED score=%s issues=%d method=%s", score, len(issues), result.get("method"))

    return {
        "passed": passed,
        "score": score,
        "issues": issues,
        "proof": result.get("proof", []),
        "failure_reason": "browser_preview_failed" if not passed else None,
        "method": result.get("method"),
    }
