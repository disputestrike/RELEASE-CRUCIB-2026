"""
Preview gate — required success criteria for Sandpack/workspace bundles.
Used by verification.preview and final job completion (not optional).
"""
import json
import logging
import os
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def _walk_source_files(workspace_path: str) -> Dict[str, str]:
    """Relative path -> utf-8 text for js/jsx/json/css (bounded)."""
    out: Dict[str, str] = {}
    if not workspace_path or not os.path.isdir(workspace_path):
        return out
    skip = {"node_modules", ".git", "__pycache__", "dist", "build", ".next"}
    count = 0
    max_files = 120
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if count >= max_files:
                return out
            if not name.endswith((".jsx", ".js", ".json", ".css", ".tsx", ".ts")):
                continue
            if name.endswith((".test.js", ".spec.js")):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    out[rel] = fh.read()
            except OSError:
                continue
            count += 1
    return out


def _proof(
    kind: str,
    title: str,
    payload: Dict[str, Any],
    *,
    verification_class: str = "presence",
) -> Dict[str, Any]:
    p = {**payload, "verification_class": verification_class}
    return {"proof_type": kind, "title": title, "payload": p}


async def verify_preview_workspace(workspace_path: str) -> Dict[str, Any]:
    """
    Depth checks for a runnable preview bundle (not just file existence).
    Returns { passed, score, issues, proof, failure_reason }.
    
    DETERMINISTIC: Every failure has an explicit reason that can guide regeneration.
    Possible failure_reasons:
    - no_source_files: Workspace has no readable JS/JSON/CSS
    - missing_package_json: package.json not found or empty
    - invalid_package_json: package.json is not valid JSON
    - missing_dependencies: Missing react, react-dom, etc.
    - no_entry_point: No index.js/index.jsx with ReactDOM.createRoot
    - no_router: No react-router usage detected
    - no_auth: No auth context pattern found
    - no_persistence: No localStorage or zustand persist
    - no_components: No reusable components directory
    - no_app_file: No App.jsx/App.js found
    - browser_preview_failed: Browser-based verification failed
    """
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []
    files = _walk_source_files(workspace_path)
    combined = "\n".join(files.values()).lower()
    rel_joined = " ".join(files.keys()).lower()
    
    failure_reason = None

    if not files:
        failure_reason = "no_source_files"
        return {
            "passed": False,
            "score": 0,
            "issues": ["Workspace has no readable JS/JSON/CSS sources for preview."],
            "proof": [],
            "failure_reason": failure_reason,
        }

    pkg_text = files.get("package.json", "")
    if not pkg_text.strip():
        failure_reason = "missing_package_json"
        issues.append("Missing package.json — Sandpack needs declared react deps.")
    else:
        try:
            pkg = json.loads(pkg_text)
            deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
            need = ("react", "react-dom", "react-router-dom", "zustand")
            missing = [k for k in need if k not in deps]
            if missing:
                failure_reason = "missing_dependencies"
                issues.append(f"package.json missing dependencies: {', '.join(missing)}")
            else:
                proof.append(_proof("verification", "package.json has core deps", {"deps": list(need)}))
        except json.JSONDecodeError as e:
            failure_reason = "invalid_package_json"
            issues.append(f"package.json is not valid JSON: {e}")

    # Entry + React 18 root
    entry_ok = False
    for rel, txt in files.items():
        if rel.endswith("index.js") or rel.endswith("index.jsx") or rel.endswith("main.jsx"):
            if "createroot" in txt.lower().replace(" ", "") or "reactdom.render" in txt.lower():
                entry_ok = True
                proof.append(_proof("verification", f"Entry mount found: {rel}", {"path": rel}))
                break
    if not entry_ok:
        failure_reason = "no_entry_point"
        issues.append("No index/main entry with ReactDOM.createRoot (or render) found.")

    # Router
    router_ok = any(
        x in combined
        for x in ("memoryrouter", "browserrouter", "routes", "<route", "react-router")
    )
    if not router_ok:
        failure_reason = "no_router"
        issues.append("No react-router usage detected (MemoryRouter/Routes/Route).")
    else:
        proof.append(_proof("verification", "Routing primitives present", {"hint": "router"}))

    # Auth pattern (context or explicit)
    auth_ok = "authcontext" in combined or "authprovider" in combined or "useauth" in combined
    if not auth_ok:
        failure_reason = "no_auth"
        issues.append("No auth context pattern (AuthContext / useAuth) found in sources.")
    else:
        proof.append(_proof("verification", "Auth context pattern present", {}))

    # Persistence
    storage_ok = "localstorage" in combined or "sessionstorage" in combined
    persist_ok = "persist" in combined and "zustand" in combined
    if not storage_ok and not persist_ok:
        failure_reason = "no_persistence"
        issues.append("No localStorage/sessionStorage or zustand persist usage detected.")
    else:
        proof.append(
            _proof("verification", "Client persistence present", {"storage": storage_ok, "zustand_persist": persist_ok}),
        )

    # Reusable components (multiple under src/components or components/)
    comp_dirs = sum(
        1 for p in files if p.startswith("src/components/") or p.startswith("components/")
    )
    if comp_dirs < 1:
        failure_reason = "no_components"
        issues.append("Expected at least one file under src/components/ for reusable UI.")
    else:
        proof.append(_proof("verification", f"Component modules: {comp_dirs} files", {"count": comp_dirs}))

    # Default export App
    app_like = [p for p in files if p.endswith("App.jsx") or p.endswith("App.js")]
    if not app_like:
        failure_reason = "no_app_file"
        issues.append("No App.jsx / App.js found.")
    else:
        proof.append(_proof("file", f"Root app file: {app_like[0]}", {"path": app_like[0]}))

    static_passed = len(issues) == 0
    if static_passed:
        from .browser_preview_verify import verify_browser_preview

        br = await verify_browser_preview(workspace_path)
        proof.extend(br["proof"])
        issues.extend(br["issues"])
        if br.get("issues"):
            failure_reason = "browser_preview_failed"
    else:
        proof.append(
            _proof(
                "verification",
                "Browser preview not run (fix static preview checks first)",
                {"static_issue_count": len(issues)},
            ),
        )

    score = max(0, 100 - len(issues) * 18)
    passed = len(issues) == 0
    return {"passed": passed, "score": score, "issues": issues, "proof": proof, "failure_reason": failure_reason}
