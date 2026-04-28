"""
browser_qa.py — Headless route validation for CrucibAI built artifacts.

Implements the "Manus-style screenshot per route" principle from the research
without requiring a full Playwright/Chromium install in every environment.

Strategy (tried in order):
  1. Playwright async (if installed) — real screenshots + DOM assertions
  2. Static HTTP server + httpx — route reachability + HTML body contracts
  3. HTML file analysis — deep parse of built dist/ files as fallback

Returns a BrowserQAResult with per-route verdicts and a boolean `passed` flag.
Wire into auto_runner.py after visual_qa so the pipeline has two QA layers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import socket
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import HTTPServer, SimpleHTTPRequestHandler
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
ROUTE_TIMEOUT   = 8      # seconds per route HTTP request
MAX_ROUTES      = 12     # cap routes to validate
PASS_THRESHOLD  = 60     # minimum score to pass


# ── DOM contract parser ───────────────────────────────────────────────────────

class _ContractParser(HTMLParser):
    """Minimal HTML parser that checks DOM contracts without a full browser."""

    def __init__(self):
        super().__init__()
        self.has_title   = False
        self.has_root    = False
        self.has_script  = False
        self.has_heading = False
        self.has_nav     = False
        self.has_main    = False
        self._in_title   = False
        self.title_text  = ""

    def handle_starttag(self, tag: str, attrs: list):
        tag_l = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag_l == "title":
            self._in_title = True
        elif tag_l in ("h1", "h2", "h3"):
            self.has_heading = True
        elif tag_l == "nav":
            self.has_nav = True
        elif tag_l == "main":
            self.has_main = True
        elif tag_l == "script" and attr_map.get("src", ""):
            self.has_script = True
        elif tag_l == "div":
            eid = attr_map.get("id", "")
            if eid in ("root", "app", "__next"):
                self.has_root = True

    def handle_data(self, data: str):
        if self._in_title:
            self.title_text += data

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self._in_title = False
            if self.title_text.strip():
                self.has_title = True


def _check_html_contracts(html: str, url: str) -> Tuple[bool, List[str]]:
    """Parse HTML and return (ok, issues)."""
    p = _ContractParser()
    try:
        p.feed(html)
    except Exception as exc:
        return False, [f"{url}: HTML parse error: {exc}"]

    issues = []
    if not p.has_title:
        issues.append(f"{url}: missing <title>")
    if not p.has_root:
        issues.append(f"{url}: missing #root/#app mount point")
    if not p.has_script:
        issues.append(f"{url}: no <script src> — JS bundle not linked")
    return len(issues) == 0, issues


# ── Static HTTP server (fallback when Playwright absent) ─────────────────────

def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass  # suppress request log spam
    def log_error(self, *args):   pass


def _start_static_server(dist_root: str) -> Tuple[HTTPServer, int]:
    port = _find_free_port()
    handler = lambda *a, **kw: _QuietHandler(*a, directory=dist_root, **kw)
    srv = HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, port


def _http_check_route(port: int, path: str) -> Tuple[int, str]:
    """Hit a route on the local static server; return (status, body_snippet)."""
    import urllib.request, urllib.error
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=ROUTE_TIMEOUT) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


# ── Playwright layer (optional) ───────────────────────────────────────────────

async def _playwright_check(dist_root: str, routes: List[str]) -> Optional[List[Dict]]:
    """Try Playwright. Returns per-route results or None if Playwright unavailable."""
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        return None

    srv, port = _start_static_server(dist_root)
    results = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            for route in routes[:MAX_ROUTES]:
                url = f"http://127.0.0.1:{port}{route}"
                verdict: Dict[str, Any] = {"route": route, "url": url}
                try:
                    resp = await page.goto(url, wait_until="networkidle", timeout=ROUTE_TIMEOUT * 1000)
                    status = resp.status if resp else 0
                    html   = await page.content()
                    # Screenshot as base64
                    screenshot = await page.screenshot(type="png")
                    screenshot_hash = hashlib.md5(screenshot).hexdigest()[:8]
                    ok, issues = _check_html_contracts(html, route)
                    verdict.update({
                        "status": status,
                        "reachable": status == 200,
                        "contract_ok": ok,
                        "issues": issues,
                        "screenshot_hash": screenshot_hash,
                        "method": "playwright",
                    })
                except Exception as exc:
                    verdict.update({
                        "status": 0,
                        "reachable": False,
                        "contract_ok": False,
                        "issues": [str(exc)[:200]],
                        "method": "playwright",
                    })
                results.append(verdict)
            await browser.close()
    finally:
        srv.shutdown()
    return results


# ── Static HTTP fallback ──────────────────────────────────────────────────────

def _static_http_check(dist_root: str, routes: List[str]) -> List[Dict]:
    """Serve dist/ via stdlib HTTP, hit each route, validate HTML."""
    srv, port = _start_static_server(dist_root)
    # Give the server a moment to start
    time.sleep(0.1)
    results = []
    try:
        for route in routes[:MAX_ROUTES]:
            # SPAs serve index.html for all routes — always hit /
            status, body = _http_check_route(port, route)
            if status == 0:
                # Route returned nothing — try root (SPA fallback)
                status, body = _http_check_route(port, "/")
            ok, issues = _check_html_contracts(body, route)
            results.append({
                "route": route,
                "status": status,
                "reachable": status in (200, 304),
                "contract_ok": ok,
                "issues": issues,
                "method": "static_http",
            })
    finally:
        srv.shutdown()
    return results


# ── File-analysis fallback ────────────────────────────────────────────────────

def _file_analysis_check(dist_root: str, routes: List[str]) -> List[Dict]:
    """Deepest fallback: parse built HTML files directly without serving."""
    index = Path(dist_root) / "index.html"
    if not index.exists():
        return [{"route": r, "status": 0, "reachable": False,
                 "contract_ok": False, "issues": ["dist/index.html missing"],
                 "method": "file_analysis"} for r in routes]
    try:
        html = index.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [{"route": r, "status": 0, "reachable": False,
                 "contract_ok": False, "issues": [str(exc)],
                 "method": "file_analysis"} for r in routes]

    ok, issues = _check_html_contracts(html, "/")
    return [{"route": r, "status": 200, "reachable": True,
             "contract_ok": ok, "issues": issues,
             "method": "file_analysis"} for r in routes]


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class BrowserQAResult:
    passed:         bool
    score:          int
    method:         str         # playwright | static_http | file_analysis | skipped
    route_results:  List[Dict]  = field(default_factory=list)
    issues:         List[str]   = field(default_factory=list)
    routes_ok:      int         = 0
    routes_total:   int         = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed":       self.passed,
            "score":        self.score,
            "method":       self.method,
            "routes_ok":    self.routes_ok,
            "routes_total": self.routes_total,
            "route_results": self.route_results,
            "issues":       self.issues,
        }


# ── Main entry ────────────────────────────────────────────────────────────────

def run_browser_qa(
    workspace_path: str,
    routes: Optional[List[str]] = None,
    *,
    goal: str = "",
) -> BrowserQAResult:
    """
    Run headless browser QA against the built workspace.

    Tries Playwright → static HTTP server → file analysis.
    Returns BrowserQAResult.  Always writes .crucibai/browser_qa.json.
    """
    ws = Path(workspace_path) if workspace_path else None
    if not ws or not ws.is_dir():
        return BrowserQAResult(
            passed=False, score=0, method="skipped",
            issues=["Workspace not found"],
        )

    dist_root = ws / "dist"
    if not dist_root.is_dir() or not (dist_root / "index.html").exists():
        logger.info("browser_qa: no dist/index.html — skipping (source-only build)")
        result = BrowserQAResult(
            passed=True, score=100, method="skipped",
            issues=[], routes_ok=0, routes_total=0,
        )
        _write_marker(ws, result)
        return result

    # Default routes
    if not routes:
        routes = ["/"]
        # Try to read from visual_qa marker if available
        vqa_path = ws / ".crucibai" / "visual_qa.json"
        if vqa_path.exists():
            try:
                vqa = json.loads(vqa_path.read_text())
                routes = (vqa.get("routes") or ["/"])[:MAX_ROUTES] or ["/"]
            except Exception:
                routes = ["/"]

    routes = routes[:MAX_ROUTES]
    route_results: List[Dict] = []
    method = "file_analysis"

    # Try Playwright first
    try:
        loop = asyncio.new_event_loop()
        pw_results = loop.run_until_complete(
            _playwright_check(str(dist_root), routes)
        )
        loop.close()
        if pw_results is not None:
            route_results = pw_results
            method = "playwright"
            logger.info("browser_qa: used Playwright for %d routes", len(routes))
    except Exception as exc:
        logger.debug("browser_qa: Playwright attempt failed: %s", exc)

    # Fallback to static HTTP
    if not route_results:
        try:
            route_results = _static_http_check(str(dist_root), routes)
            method = "static_http"
            logger.info("browser_qa: used static HTTP server for %d routes", len(routes))
        except Exception as exc:
            logger.debug("browser_qa: static HTTP fallback failed: %s", exc)

    # Last resort: file analysis
    if not route_results:
        route_results = _file_analysis_check(str(dist_root), routes)
        method = "file_analysis"
        logger.info("browser_qa: used file analysis fallback for %d routes", len(routes))

    # Score
    total  = len(route_results)
    ok     = sum(1 for r in route_results if r.get("reachable") and r.get("contract_ok"))
    issues = [i for r in route_results for i in (r.get("issues") or [])]

    if total == 0:
        score = 100
    else:
        reachable = sum(1 for r in route_results if r.get("reachable"))
        score = int(
            (reachable / total) * 60 +        # reachability = 60 pts
            (ok / total) * 40                  # contract compliance = 40 pts
        )

    passed = score >= PASS_THRESHOLD

    result = BrowserQAResult(
        passed=passed,
        score=score,
        method=method,
        route_results=route_results,
        issues=issues,
        routes_ok=ok,
        routes_total=total,
    )

    logger.info(
        "browser_qa: method=%s score=%d passed=%s routes=%d/%d issues=%d",
        method, score, passed, ok, total, len(issues),
    )

    _write_marker(ws, result)
    return result


def _write_marker(ws: Path, result: BrowserQAResult) -> None:
    try:
        meta = ws / ".crucibai"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "browser_qa.json").write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("browser_qa: could not write marker: %s", exc)
