"""
self_repair.py — Actually writes code fixes to the workspace before retry.

This is what makes the brain a code author, not just a parameter tuner.
When a file is broken, this module fixes it directly on disk so the
next retry starts with working code.

Also re-exports the old deterministic verification helpers from self_repair_old.py
so existing callers don't break.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Re-export old helpers so existing imports still work
try:
    from .self_repair_old import attempt_verification_self_repair  # noqa: F401
    from .self_repair_old import maybe_commit_workspace_repairs  # noqa: F401
except ImportError:

    def attempt_verification_self_repair(*args, **kwargs):
        return []

    def maybe_commit_workspace_repairs(*args, **kwargs):
        return []


# ── Safe file writing ──────────────────────────────────────────────────────────

PROSE_PREFIXES = (
    "i ",
    "i'",
    "here ",
    "here'",
    "appreciate",
    "certainly",
    "sure,",
    "below",
    "based on",
    "as requested",
    "i have",
    "i'll",
    "let me",
    "of course",
    "happy to",
    "glad to",
    "please find",
    "the following",
    "above is",
    "this is",
    "note:",
    "note that",
    "in this",
    "we have",
)

_VALID_VITE_MARKERS = (
    "defineconfig",
    "export default",
    "@vitejs/plugin-react",
)


def _safe_write(workspace_path: str, rel_path: str, content: str) -> bool:
    if not workspace_path:
        return False
    full = os.path.normpath(os.path.join(workspace_path, rel_path))
    if not full.startswith(os.path.normpath(workspace_path)):
        logger.warning("self_repair: rejected path escape %s", rel_path)
        return False
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("self_repair: wrote %s (%d chars)", rel_path, len(content))
        return True
    except OSError as e:
        logger.error("self_repair: failed to write %s: %s", rel_path, e)
        return False


def _read_safe(workspace_path: str, rel_path: str) -> Optional[str]:
    if not workspace_path:
        return None
    full = os.path.join(workspace_path, rel_path)
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


# ── Missing npm module (bundler / TS) ───────────────────────────────────────

_MISSING_MODULE_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"Cannot find module ['\"]([^'\"]+)['\"]", re.I),
    re.compile(r"Can't resolve ['\"]([^'\"]+)['\"]", re.I),
    re.compile(r"Failed to resolve import ['\"]([^'\"]+)['\"]", re.I),
    re.compile(r"Unable to resolve path to module ['\"]([^'\"]+)['\"]", re.I),
    re.compile(r"Could not resolve ['\"]([^'\"]+)['\"]", re.I),
)

# Pin common packages; unknown names get a conservative caret range so npm can resolve.
NPM_KNOWN_VERSIONS: Dict[str, str] = {
    "axios": "^1.6.0",
    "react-redux": "^9.1.0",
    "redux": "^5.0.0",
    "@reduxjs/toolkit": "^2.2.0",
    "zustand": "^4.5.0",
    "framer-motion": "^11.0.0",
    "@tanstack/react-query": "^5.0.0",
    "lucide-react": "^0.400.0",
    "date-fns": "^3.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
}


def _npm_root_package(spec: str) -> Optional[str]:
    s = (spec or "").strip()
    if not s or s.startswith(".") or s.startswith("/"):
        return None
    if s.startswith("@/") or s.startswith("~/"):
        return None
    if s.startswith("@"):
        parts = s.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return s
    return s.split("/")[0]


def _extract_missing_npm_spec(error_message: str) -> Optional[str]:
    if not error_message:
        return None
    for pat in _MISSING_MODULE_PATTERNS:
        m = pat.search(error_message)
        if m:
            return m.group(1).strip()
    return None


def try_add_missing_npm_dependency(
    workspace_path: str, error_message: str
) -> Dict[str, Any]:
    """If error text names an unresolved npm package, add it to package.json dependencies."""
    import json

    spec = _extract_missing_npm_spec(error_message)
    if not spec:
        return {"fixed": False, "reason": "no_missing_module_pattern"}
    pkg_key = _npm_root_package(spec)
    if not pkg_key:
        return {"fixed": False, "reason": "relative_or_alias_import"}

    content = _read_safe(workspace_path, "package.json")
    pkg: Dict[str, Any] = {}
    if content:
        try:
            pkg = json.loads(content)
        except json.JSONDecodeError:
            pkg = {}
    if not isinstance(pkg, dict):
        pkg = {}
    if not pkg:
        pkg = {
            "name": "crucibai-generated-app",
            "version": "0.1.0",
            "private": True,
            "type": "module",
        }
    deps = pkg.setdefault("dependencies", {})
    if not isinstance(deps, dict):
        deps = {}
        pkg["dependencies"] = deps
    if pkg_key in deps:
        return {"fixed": False, "reason": "already_installed", "package": pkg_key}

    version = NPM_KNOWN_VERSIONS.get(pkg_key) or NPM_KNOWN_VERSIONS.get(spec)
    if not version:
        version = "^1.0.0"
    deps[pkg_key] = version
    _safe_write(workspace_path, "package.json", json.dumps(pkg, indent=2))
    return {
        "fixed": True,
        "file": "package.json",
        "package": pkg_key,
        "version": version,
        "action": "add_npm_dependency",
    }


# ── Repair functions ───────────────────────────────────────────────────────────


def strip_prose_preamble(content: str) -> str:
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in PROSE_PREFIXES):
            continue
        return "\n".join(lines[i:])
    return content


def repair_prose_in_file(workspace_path: str, rel_path: str) -> Dict[str, Any]:
    content = _read_safe(workspace_path, rel_path)
    if not content:
        return {"fixed": False, "reason": f"{rel_path} not readable"}
    cleaned = strip_prose_preamble(content)
    if cleaned == content:
        return {"fixed": False, "reason": "No prose preamble found"}
    lines_removed = content.count("\n") - cleaned.count("\n")
    _safe_write(workspace_path, rel_path, cleaned)
    return {
        "fixed": True,
        "file": rel_path,
        "lines_removed": lines_removed,
        "first_line_after": (
            cleaned.strip().split("\n")[0][:80] if cleaned.strip() else ""
        ),
    }


def repair_package_json(workspace_path: str) -> Dict[str, Any]:
    import json

    content = _read_safe(workspace_path, "package.json")
    pkg = {}
    if content:
        try:
            pkg = json.loads(content)
        except json.JSONDecodeError:
            pkg = {}
    pkg.setdefault("name", "crucibai-generated-app")
    pkg.setdefault("version", "0.1.0")
    pkg.setdefault("private", True)
    pkg.setdefault("type", "module")
    deps = pkg.setdefault("dependencies", {})
    deps.setdefault("react", "^18.2.0")
    deps.setdefault("react-dom", "^18.2.0")
    deps.setdefault("react-router-dom", "^6.22.0")
    dev_deps = pkg.setdefault("devDependencies", {})
    dev_deps.setdefault("vite", "^5.0.0")
    dev_deps.setdefault("@vitejs/plugin-react", "^4.2.0")
    scripts = pkg.setdefault("scripts", {})
    scripts.setdefault("dev", "vite")
    scripts.setdefault("build", "vite build")
    scripts.setdefault("preview", "vite preview")
    _safe_write(workspace_path, "package.json", json.dumps(pkg, indent=2))
    return {"fixed": True, "file": "package.json"}


def repair_entry_point(workspace_path: str) -> Dict[str, Any]:
    content = _read_safe(workspace_path, "src/main.jsx")
    if content and "createRoot" in content and "App" in content:
        return {"fixed": False, "reason": "src/main.jsx already valid"}
    _safe_write(
        workspace_path,
        "src/main.jsx",
        """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

const container = document.getElementById('root');
if (container) {
  createRoot(container).render(<App />);
}
""",
    )
    return {"fixed": True, "file": "src/main.jsx", "action": "created_minimal"}


def repair_app_jsx_if_broken(workspace_path: str) -> Dict[str, Any]:
    content = _read_safe(workspace_path, "src/App.jsx")
    is_empty = not content or not content.strip()
    is_prose = False
    if not is_empty:
        first = content.strip().split("\n")[0].strip().lower()
        is_prose = any(first.startswith(p) for p in PROSE_PREFIXES)

    if not is_prose and not is_empty:
        cleaned = strip_prose_preamble(content)
        if cleaned != content:
            _safe_write(workspace_path, "src/App.jsx", cleaned)
            return {
                "fixed": True,
                "file": "src/App.jsx",
                "action": "stripped_prose",
                "first_line": cleaned.strip().split("\n")[0][:80],
            }
        return {"fixed": False, "reason": "App.jsx appears valid"}

    _safe_write(
        workspace_path,
        "src/App.jsx",
        """import React from 'react';

export default function App() {
  return (
    <div className="app">
      <h1>Loading...</h1>
      <p>Application is being generated. Please wait.</p>
    </div>
  );
}
""",
    )
    return {
        "fixed": True,
        "file": "src/App.jsx",
        "action": "replaced_with_scaffold" if is_prose else "created_minimal",
    }


def repair_vite_config(workspace_path: str) -> Dict[str, Any]:
    content = _read_safe(workspace_path, "vite.config.js")
    normalized = (content or "").lower()
    if content and all(marker in normalized for marker in _VALID_VITE_MARKERS):
        return {"fixed": False, "reason": "vite.config.js already valid"}
    _safe_write(
        workspace_path,
        "vite.config.js",
        """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist' },
  server: { port: 3000 },
});
""",
    )
    return {
        "fixed": True,
        "file": "vite.config.js",
        "action": "replaced_invalid" if content else "created_minimal",
    }


def repair_index_html(workspace_path: str) -> Dict[str, Any]:
    content = _read_safe(workspace_path, "index.html")
    if content and "root" in content:
        return {"fixed": False, "reason": "index.html already exists"}
    _safe_write(
        workspace_path,
        "index.html",
        """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""",
    )
    return {"fixed": True, "file": "index.html", "action": "created_minimal"}


# ── Main dispatch ──────────────────────────────────────────────────────────────


async def apply_self_repair(
    workspace_path: str,
    diagnosis: Dict[str, Any],
    step_key: str = "",
    error_message: str = "",
) -> Dict[str, Any]:
    """
    Apply all available self-repairs based on the workspace diagnosis.
    Called BEFORE retry so the next attempt starts with working code.
    """
    repairs: List[Dict[str, Any]] = []
    fixed_count = 0

    if not workspace_path or not os.path.isdir(workspace_path):
        return {"repairs": [], "fixed_count": 0, "workspace_accessible": False}

    # 0. Unresolved npm package from bundler / verifier output (before broader diagnosis)
    if error_message:
        r0 = try_add_missing_npm_dependency(workspace_path, error_message)
        repairs.append({"type": "add_npm_dependency", **r0})
        if r0.get("fixed"):
            fixed_count += 1

    root_cause = diagnosis.get("root_cause", "unknown")
    findings = diagnosis.get("findings", [])
    affected_files = diagnosis.get("affected_files", [])

    # 1. Strip prose from any file that has it
    for finding in [f for f in findings if f.get("check") == "prose_preamble"]:
        rel = finding.get("file", "")
        if rel:
            r = repair_prose_in_file(workspace_path, rel)
            repairs.append({"type": "strip_prose", **r})
            if r.get("fixed"):
                fixed_count += 1

    # 2. Fix App.jsx if broken
    if root_cause in (
        "prose_in_code",
        "regenerate_frontend",
        "jsx_syntax_error",
    ) or any("App.jsx" in f for f in affected_files):
        r = repair_app_jsx_if_broken(workspace_path)
        repairs.append({"type": "repair_app_jsx", **r})
        if r.get("fixed"):
            fixed_count += 1

    # 3. Fix package.json
    if root_cause in ("missing_dependencies", "regenerate_package_json") or any(
        "package.json" in f for f in affected_files
    ):
        r = repair_package_json(workspace_path)
        repairs.append({"type": "repair_package_json", **r})
        if r.get("fixed"):
            fixed_count += 1

    # 4. Fix entry point
    if root_cause in ("no_entry_point", "regenerate_entry_point") or not diagnosis.get(
        "has_app_jsx"
    ):
        r = repair_entry_point(workspace_path)
        repairs.append({"type": "repair_entry_point", **r})
        if r.get("fixed"):
            fixed_count += 1

    # 5. Fix vite config
    if "vite" in error_message.lower() or root_cause == "fix_vite_config":
        r = repair_vite_config(workspace_path)
        repairs.append({"type": "repair_vite_config", **r})
        if r.get("fixed"):
            fixed_count += 1

    # 6. Fix index.html
    if "index.html" in error_message.lower() or (
        diagnosis.get("has_app_jsx") and not _read_safe(workspace_path, "index.html")
    ):
        r = repair_index_html(workspace_path)
        repairs.append({"type": "repair_index_html", **r})
        if r.get("fixed"):
            fixed_count += 1

    # 7. Fallback: scan ALL code files for prose
    if fixed_count == 0:
        try:
            from .workspace_reader import CODE_EXTENSIONS, list_workspace_files

            for rel in list_workspace_files(workspace_path):
                ext = os.path.splitext(rel)[1].lower()
                if ext not in CODE_EXTENSIONS or "node_modules" in rel:
                    continue
                r = repair_prose_in_file(workspace_path, rel)
                if r.get("fixed"):
                    repairs.append({"type": "strip_prose_scan", **r})
                    fixed_count += 1
        except Exception as e:
            logger.warning("self_repair: fallback scan failed: %s", e)

    logger.info(
        "self_repair.apply: step=%s root_cause=%s fixed=%d repairs=%d",
        step_key,
        root_cause,
        fixed_count,
        len(repairs),
    )
    return {
        "repairs": repairs,
        "fixed_count": fixed_count,
        "workspace_accessible": True,
        "root_cause_addressed": root_cause,
    }
