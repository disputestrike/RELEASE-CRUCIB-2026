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
    """Relative path -> utf-8 text for source/config/docs (bounded)."""
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
            if not name.endswith((".jsx", ".js", ".json", ".css", ".tsx", ".ts", ".md")):
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


def _has_file(files: Dict[str, str], *needles: str) -> bool:
    rels = [p.lower() for p in files]
    return any(any(needle.lower() in rel for rel in rels) for needle in needles)


def _detect_saas_product_intent(files: Dict[str, str], combined: str) -> bool:
    # Check PLAN.md / REQUIREMENTS.md / STACK.md (the job's original goal text),
    # NOT the generated file content — because the manus template injects SaaS
    # words (analytics, pricing, dashboard) into every build's file content.
    goal_sources = {
        k: v for k, v in files.items()
        if k.lower() in ("plan.md", "requirements.md", "stack.md", "readme.md")
    }
    goal_text = " ".join(goal_sources.values()).lower() if goal_sources else ""
    # Strong SaaS signals that must appear in the *goal* documents, not generated code
    strong_markers = ("saas", "product ui", "modern ui", "design system", "landing page", "marketing page")
    supporting_markers = ("dashboard", "analytics", "pricing", "settings", "multiple pages", "responsive layout")
    strong_hits = sum(1 for m in strong_markers if m in goal_text)
    supporting_hits = sum(1 for m in supporting_markers if m in goal_text)
    # Need at least 1 strong signal OR 3 supporting signals from the goal docs
    return strong_hits >= 1 or supporting_hits >= 3


def _verify_saas_product_contract(
    files: Dict[str, str],
    combined: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Hard Manus-parity gate for modern SaaS/product UI prompts.

    The old scaffold rendered and built, but still delivered only Home/Login/
    Dashboard/Team with placeholder copy. This gate checks final product shape:
    pages, routes, design system, charts, product sections, and no visible
    scaffold language.
    """

    issues: List[str] = []
    proof: List[Dict[str, Any]] = []
    lower = combined.lower()
    rels = " ".join(files.keys()).lower()

    required_pages = {
        "home": ("src/pages/home", "/"),
        "dashboard": ("src/pages/dashboard", "/dashboard"),
        "analytics": ("src/pages/analytics", "/analytics"),
        "team": ("src/pages/team", "/team"),
        "pricing": ("src/pages/pricing", "/pricing"),
        "settings": ("src/pages/settings", "/settings"),
        "notfound": ("src/pages/notfound", "/404"),
    }
    missing = []
    for label, (path_hint, route_hint) in required_pages.items():
        has_page = path_hint in rels
        has_route = route_hint in lower
        if not (has_page and has_route):
            missing.append(label)
    if missing:
        issues.append(
            "SaaS UI contract missing mounted pages/routes: " + ", ".join(missing)
        )
    else:
        proof.append(
            _proof(
                "verification",
                "SaaS route inventory complete",
                {"routes": sorted(required_pages)},
                verification_class="product",
            )
        )

    if not _has_file(files, "marketingnav"):
        issues.append("SaaS UI contract missing a public MarketingNav component.")
    if not _has_file(files, "dashboardlayout"):
        issues.append("SaaS UI contract missing a reusable DashboardLayout/app shell.")

    css = "\n".join(
        txt for path, txt in files.items() if path.endswith((".css", ".md"))
    ).lower()
    token_needles = ("--primary", "--chart", "--sidebar", "--surface", "--muted")
    if sum(1 for needle in token_needles if needle in css) < 4:
        issues.append(
            "SaaS UI contract needs a real design-token system with primary, chart, sidebar, surface, and muted tokens."
        )
    else:
        proof.append(
            _proof(
                "verification",
                "SaaS design tokens present",
                {"tokens": [n for n in token_needles if n in css]},
                verification_class="product",
            )
        )

    chart_needles = ("recharts", "areachart", "barchart", "linechart", "piechart")
    if sum(1 for needle in chart_needles if needle in lower) < 3:
        issues.append(
            "SaaS dashboard/analytics contract needs real chart components (area/bar/line/pie or equivalent)."
        )
    else:
        proof.append(
            _proof(
                "verification",
                "SaaS chart surface present",
                {"chart_markers": [n for n in chart_needles if n in lower]},
                verification_class="product",
            )
        )

    section_checks = {
        "marketing hero/features/CTA": ("hero", "feature", "cta"),
        "dashboard KPIs/table/activity": ("kpi", "table", "activity"),
        "analytics funnel/top pages": ("funnel", "top pages"),
        "team roles/invite/search": ("invite", "role", "search"),
        "pricing plans/FAQ": ("plans", "faq"),
        "settings security/billing/integrations": ("security", "billing", "integrations"),
    }
    for label, needles in section_checks.items():
        if not all(needle in lower for needle in needles):
            issues.append(f"SaaS UI contract missing section content: {label}.")

    scaffold_phrases = (
        "crucib_incomplete",
        "sample team page",
        "included in the scaffold",
        "generated module placeholder",
        "ready for real data wiring",
        "real test placeholder",
        "thin provider/router mount",
        "replace with real api",
        "client-only token stored",
        "configure cmd for your app",
    )
    found_scaffold = [phrase for phrase in scaffold_phrases if phrase in lower]
    if found_scaffold:
        issues.append(
            "SaaS UI contract found visible scaffold/placeholder language: "
            + ", ".join(found_scaffold)
        )

    if not issues:
        proof.append(
            _proof(
                "verification",
                "SaaS product completeness gate passed",
                {
                    "required_pages": len(required_pages),
                    "section_checks": len(section_checks),
                },
                verification_class="product",
            )
        )

    return issues, proof


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

    try:
        from agents.preview_validator_agent import PreviewValidatorAgent

        validator = PreviewValidatorAgent()
        preflight = await validator.execute({"workspace_path": workspace_path})
        critical_issues = list(preflight.get("critical_issues") or [])
        warnings = list(preflight.get("warnings") or [])
        if critical_issues:
            failure_reason = failure_reason or "preview_preflight_failed"
            for issue in critical_issues:
                issue_text = issue.get("issue") or "preview preflight issue"
                suggestion = issue.get("suggestion") or ""
                issues.append(
                    f"Preview preflight: {issue_text}{f' ({suggestion})' if suggestion else ''}"
                )
            proof.append(
                _proof(
                    "verification",
                    "Preview preflight found blocking issues",
                    {
                        "critical_issue_count": len(critical_issues),
                        "warning_count": len(warnings),
                        "status": preflight.get("status"),
                    },
                    verification_class="runtime",
                ),
            )
        else:
            proof.append(
                _proof(
                    "verification",
                    "Preview preflight passed",
                    {
                        "warning_count": len(warnings),
                        "status": preflight.get("status"),
                        "files_checked": preflight.get("total_files_checked"),
                    },
                    verification_class="runtime",
                ),
            )
    except Exception as exc:
        proof.append(
            _proof(
                "verification",
                "Preview preflight unavailable",
                {"error": str(exc)[:200]},
            ),
        )

    pkg_text = files.get("package.json", "")
    if not pkg_text.strip():
        failure_reason = "missing_package_json"
        issues.append("Missing package.json — Sandpack needs declared react deps.")
    else:
        try:
            pkg = json.loads(pkg_text)
            deps = {
                **(pkg.get("dependencies") or {}),
                **(pkg.get("devDependencies") or {}),
            }
            need = ("react", "react-dom", "react-router-dom", "zustand")
            missing = [k for k in need if k not in deps]
            if missing:
                failure_reason = "missing_dependencies"
                issues.append(
                    f"package.json missing dependencies: {', '.join(missing)}"
                )
            else:
                proof.append(
                    _proof(
                        "verification",
                        "package.json has core deps",
                        {"deps": list(need)},
                    )
                )
        except json.JSONDecodeError as e:
            failure_reason = "invalid_package_json"
            issues.append(f"package.json is not valid JSON: {e}")

    # Entry + React 18 root
    entry_ok = False
    for rel, txt in files.items():
        if (
            rel.endswith("index.js")
            or rel.endswith("index.jsx")
            or rel.endswith("main.jsx")
        ):
            if (
                "createroot" in txt.lower().replace(" ", "")
                or "reactdom.render" in txt.lower()
            ):
                entry_ok = True
                proof.append(
                    _proof("verification", f"Entry mount found: {rel}", {"path": rel})
                )
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
        proof.append(
            _proof("verification", "Routing primitives present", {"hint": "router"})
        )

    # Auth pattern (context or explicit)
    auth_ok = (
        "authcontext" in combined or "authprovider" in combined or "useauth" in combined
    )
    if not auth_ok:
        failure_reason = "no_auth"
        issues.append(
            "No auth context pattern (AuthContext / useAuth) found in sources."
        )
    else:
        proof.append(_proof("verification", "Auth context pattern present", {}))

    # Persistence
    storage_ok = "localstorage" in combined or "sessionstorage" in combined
    persist_ok = "persist" in combined and "zustand" in combined
    if not storage_ok and not persist_ok:
        failure_reason = "no_persistence"
        issues.append(
            "No localStorage/sessionStorage or zustand persist usage detected."
        )
    else:
        proof.append(
            _proof(
                "verification",
                "Client persistence present",
                {"storage": storage_ok, "zustand_persist": persist_ok},
            ),
        )

    # Reusable components (multiple under src/components or components/)
    comp_dirs = sum(
        1
        for p in files
        if p.startswith("src/components/") or p.startswith("components/")
    )
    if comp_dirs < 1:
        failure_reason = "no_components"
        issues.append(
            "Expected at least one file under src/components/ for reusable UI."
        )
    else:
        proof.append(
            _proof(
                "verification",
                f"Component modules: {comp_dirs} files",
                {"count": comp_dirs},
            )
        )

    # Default export App
    app_like = [p for p in files if p.endswith("App.jsx") or p.endswith("App.js")]
    if not app_like:
        failure_reason = "no_app_file"
        issues.append("No App.jsx / App.js found.")
    else:
        proof.append(
            _proof("file", f"Root app file: {app_like[0]}", {"path": app_like[0]})
        )

    if _detect_saas_product_intent(files, combined):
        saas_issues, saas_proof = _verify_saas_product_contract(files, combined)
        proof.extend(saas_proof)
        if saas_issues:
            failure_reason = "saas_product_contract_failed"
            issues.extend(saas_issues)

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
    return {
        "passed": passed,
        "score": score,
        "issues": issues,
        "proof": proof,
        "failure_reason": failure_reason,
    }
