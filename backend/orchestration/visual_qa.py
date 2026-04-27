"""
visual_qa.py — Manus-style DOM contract checking and route crawling.

Performs static analysis of the built workspace to verify:
  1. Route inventory — every declared route has a corresponding page component
  2. DOM contracts — key elements (nav, main, headings) are present per page
  3. Import reachability — components imported from App.jsx actually exist on disk
  4. Orphan detection — generated components not imported by any reachable file

Design: file-system only. No Playwright, no headless browser.
The research specifies "Manus-style debug collector + route crawling" —
we crawl the source tree and the built HTML rather than a live server.

Returns a VQAResult with per-route verdicts and a boolean `passed` flag.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── Regexes ───────────────────────────────────────────────────────────────────

_ROUTE_RE = re.compile(
    r"""<Route[^>]+path=["']([^"']+)["'][^>]*>|"""
    r"""createBrowserRouter\s*\(\s*\[|"""
    r"""path:\s*["']([^"']+)["']""",
    re.DOTALL,
)
_IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:\{[^}]*\}|[\w*]+)\s+from\s+["']([^"']+)["']"""
)
_COMPONENT_RE = re.compile(
    r"""(?:export\s+default\s+function|export\s+function|const\s+\w+\s*=\s*(?:\([^)]*\)\s*=>|\(\)))\s+(\w+)"""
)
_JSX_ELEMENT_RE = re.compile(r"<(\w[\w.]*)")
_HEADING_RE = re.compile(r"<h[1-3][\s>]")
_NAV_RE = re.compile(r"<nav[\s>]|<Nav[\s>]")
_MAIN_RE = re.compile(r"<main[\s>]|<Main[\s>]|id=[\"']app[\"']|id=[\"']root[\"']")

_SRC_EXTS = {".jsx", ".tsx", ".js", ".ts"}
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "coverage"}


# ── File walking ──────────────────────────────────────────────────────────────

def _walk_src(workspace_path: str) -> Dict[str, str]:
    """Return {rel_path: content} for all JS/TS/JSX/TSX source files."""
    result: Dict[str, str] = {}
    root = Path(workspace_path)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in filenames:
            if Path(fname).suffix not in _SRC_EXTS:
                continue
            full = Path(dirpath) / fname
            rel = str(full.relative_to(root)).replace("\\", "/")
            try:
                result[rel] = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return result


def _walk_html(workspace_path: str) -> Dict[str, str]:
    """Return {rel_path: content} for built HTML files (dist/)."""
    result: Dict[str, str] = {}
    dist = Path(workspace_path) / "dist"
    if not dist.is_dir():
        return result
    for full in dist.rglob("*.html"):
        rel = str(full.relative_to(Path(workspace_path))).replace("\\", "/")
        try:
            result[rel] = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return result


# ── Route extraction ──────────────────────────────────────────────────────────

def _extract_routes(files: Dict[str, str]) -> List[str]:
    """Pull declared routes from App.jsx / router files."""
    routes: List[str] = []
    for rel, content in files.items():
        base = os.path.basename(rel).lower()
        if not any(k in base for k in ("app", "router", "routes", "routing")):
            continue
        for m in _ROUTE_RE.finditer(content):
            path = m.group(1) or m.group(2)
            if path and path not in routes:
                routes.append(path)
    return routes or ["/"]


# ── Import reachability ───────────────────────────────────────────────────────

def _resolve_import(base_file: str, import_path: str, workspace_path: str) -> Optional[str]:
    """Try to resolve a relative import to an actual file rel path."""
    if not import_path.startswith("."):
        return None  # absolute/node_module import
    base_dir = os.path.dirname(base_file)
    candidates = [
        os.path.normpath(os.path.join(base_dir, import_path)).replace("\\", "/"),
    ]
    for candidate in candidates:
        for ext in ("", ".jsx", ".tsx", ".js", ".ts", "/index.jsx", "/index.tsx", "/index.js"):
            full = os.path.join(workspace_path, candidate + ext)
            if os.path.isfile(full):
                rel = os.path.relpath(full, workspace_path).replace("\\", "/")
                return rel
    return None


def _reachable_files(entry: str, files: Dict[str, str], workspace_path: str) -> Set[str]:
    """BFS from entry point, following relative imports."""
    visited: Set[str] = set()
    queue = [entry]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        content = files.get(current, "")
        for m in _IMPORT_FROM_RE.finditer(content):
            resolved = _resolve_import(current, m.group(1), workspace_path)
            if resolved and resolved not in visited:
                queue.append(resolved)
    return visited


# ── DOM contract checks ───────────────────────────────────────────────────────

def _check_dom_contracts(content: str, rel: str) -> List[str]:
    """Check a source file for minimum DOM contract elements."""
    issues = []
    if "page" in rel.lower() or "layout" in rel.lower():
        if not _HEADING_RE.search(content):
            issues.append(f"{rel}: no h1/h2/h3 heading found")
        if not _MAIN_RE.search(content):
            issues.append(f"{rel}: no <main> landmark or #root/#app element")
    return issues


def _check_built_html(html_files: Dict[str, str]) -> List[str]:
    """Check built dist/ HTML files for minimum contract elements."""
    issues = []
    for rel, content in html_files.items():
        if "<title>" not in content.lower():
            issues.append(f"{rel}: built HTML missing <title>")
        if "id=\"root\"" not in content and "id='root'" not in content:
            issues.append(f"{rel}: built HTML missing root mount point")
        # Check for JS bundle reference
        if "<script" not in content.lower():
            issues.append(f"{rel}: built HTML has no <script> — bundle may not be linked")
    return issues


# ── Orphan detection ──────────────────────────────────────────────────────────

def _find_orphans(files: Dict[str, str], reachable: Set[str]) -> List[str]:
    """Find component files not reachable from any entry point."""
    orphans = []
    for rel in files:
        if rel in reachable:
            continue
        # Only flag files that look like UI components (PascalCase filename in src/)
        name = os.path.basename(rel)
        stem = os.path.splitext(name)[0]
        if rel.startswith("src/") and stem and stem[0].isupper():
            orphans.append(rel)
    return orphans


# ── Main entry ────────────────────────────────────────────────────────────────

class VQAResult:
    def __init__(
        self,
        *,
        passed: bool,
        routes: List[str],
        reachable_count: int,
        orphans: List[str],
        dom_issues: List[str],
        html_issues: List[str],
        issues: List[str],
        score: int,
    ):
        self.passed = passed
        self.routes = routes
        self.reachable_count = reachable_count
        self.orphans = orphans
        self.dom_issues = dom_issues
        self.html_issues = html_issues
        self.issues = issues
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "routes": self.routes,
            "reachable_file_count": self.reachable_count,
            "orphans": self.orphans,
            "dom_issues": self.dom_issues,
            "html_issues": self.html_issues,
            "issues": self.issues,
        }


def run_visual_qa(workspace_path: str, *, goal: str = "") -> VQAResult:
    """
    Run the full visual QA suite against a workspace.

    Returns VQAResult. Designed to be called from auto_runner or the
    delivery gate before final completion.
    """
    issues: List[str] = []
    dom_issues: List[str] = []
    html_issues: List[str] = []
    orphans: List[str] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        return VQAResult(
            passed=False, routes=[], reachable_count=0, orphans=[],
            dom_issues=[], html_issues=[], issues=["Workspace directory not found"],
            score=0,
        )

    files = _walk_src(workspace_path)
    html_files = _walk_html(workspace_path)

    if not files:
        return VQAResult(
            passed=False, routes=[], reachable_count=0, orphans=[],
            dom_issues=[], html_issues=[], issues=["No source files found"],
            score=0,
        )

    # 1. Route inventory
    routes = _extract_routes(files)
    logger.info("visual_qa: found %d routes: %s", len(routes), routes[:10])

    # 2. Import reachability from App.jsx / main.jsx
    entry_candidates = [
        rel for rel in files
        if os.path.basename(rel).lower() in ("app.jsx", "app.tsx", "app.js", "main.jsx", "main.tsx")
    ]
    reachable: Set[str] = set()
    for entry in entry_candidates:
        reachable |= _reachable_files(entry, files, workspace_path)

    # 3. DOM contract checks on page files
    for rel, content in files.items():
        dom_issues.extend(_check_dom_contracts(content, rel))

    # 4. Built HTML checks
    html_issues.extend(_check_built_html(html_files))

    # 5. Orphan detection
    if reachable:
        orphans = _find_orphans(files, reachable)
        if orphans:
            issues.append(
                f"{len(orphans)} orphan component(s) not reachable from App.jsx: "
                + ", ".join(orphans[:5])
            )
            logger.warning("visual_qa: orphans detected: %s", orphans[:5])

    # 6. Missing route components
    for route in routes:
        if route in ("/", "*", ""):
            continue
        # Heuristic: route '/dashboard' should have a DashboardPage component
        route_word = route.strip("/").split("/")[0].lower()
        has_page = any(
            route_word in rel.lower() for rel in files
            if "page" in rel.lower() or "screen" in rel.lower() or "view" in rel.lower()
        )
        if not has_page:
            issues.append(f"Route '{route}' has no matching Page/Screen/View component")

    all_issues = issues + dom_issues[:5] + html_issues[:5]

    # Score: start at 100, deduct for each category
    score = 100
    score -= min(40, len(orphans) * 8)
    score -= min(20, len(dom_issues) * 4)
    score -= min(20, len(html_issues) * 5)
    score -= min(20, len(issues) * 5)
    score = max(0, score)

    # Threshold: 60 to pass
    passed = score >= 60 and len(all_issues) <= 10

    result = VQAResult(
        passed=passed,
        routes=routes,
        reachable_count=len(reachable),
        orphans=orphans,
        dom_issues=dom_issues,
        html_issues=html_issues,
        issues=all_issues,
        score=score,
    )

    logger.info(
        "visual_qa: score=%d passed=%s routes=%d reachable=%d orphans=%d dom_issues=%d html_issues=%d",
        score, passed, len(routes), len(reachable), len(orphans), len(dom_issues), len(html_issues),
    )

    # Persist result marker for delivery gate
    try:
        meta = Path(workspace_path) / ".crucibai"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "visual_qa.json").write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("visual_qa: could not write marker: %s", exc)

    return result
