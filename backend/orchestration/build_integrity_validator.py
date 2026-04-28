"""Build Integrity Validator (BIV).

Universal convergence gate for generated workspaces.

The validator answers one question before a job is allowed to leave the build
pipeline: did the final artifact converge into the thing the user asked for?

It is intentionally deterministic and file-system based. LLM agents can produce
plans, code, and repairs, but this module only inspects concrete artifacts.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


TEXT_SUFFIXES = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".css",
    ".html",
    ".md",
    ".py",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
}

TEXT_FILENAMES = {
    "Dockerfile",
    "Procfile",
}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
}

SCORE_WEIGHTS = {
    "architecture": 20,
    "design_system": 15,
    "completeness": 20,
    "runtime_validity": 25,
    "integration": 10,
    "deployability": 10,
}

RETRY_THRESHOLD = 85
HARD_FAIL_THRESHOLD = 70

RETRY_AGENT_ROUTES: Dict[str, Tuple[str, ...]] = {
    "planning": ("Planner", "Requirements Clarifier"),
    "requirements": ("Requirements Clarifier",),
    "design": ("Design Agent", "Frontend Generation"),
    "frontend": ("Frontend Generation", "Integration Agent"),
    "backend": ("Backend Generation", "Integration Agent"),
    "stack": ("Stack Selector", "Integration Agent"),
    "mobile": ("Mobile Generation", "Integration Agent"),
    "automation": ("Automation Agent", "Integration Agent"),
    "security": ("Security Checker", "Frontend Generation"),
    "verification": ("Verifier", "Frontend Generation"),
    "deploy": ("Deployment Agent", "Integration Agent"),
    "executor": ("Execution Agent", "Integration Agent"),
    "integration": ("Integration Agent",),
}


@dataclass
class IntegrityIssue:
    code: str
    message: str
    phase: str
    severity: str
    retry_targets: Tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "phase": self.phase,
            "severity": self.severity,
            "retry_targets": list(self.retry_targets),
        }


def _issue(
    code: str,
    message: str,
    phase: str,
    severity: str = "blocker",
    retry_targets: Iterable[str] = ("integration",),
) -> IntegrityIssue:
    return IntegrityIssue(
        code=code,
        message=message,
        phase=phase,
        severity=severity,
        retry_targets=tuple(retry_targets),
    )


def route_retry_targets(targets: Iterable[str]) -> Dict[str, Any]:
    """Map validator retry target categories to concrete DAG agent groups."""

    normalized = sorted({str(target).strip().lower() for target in targets if str(target).strip()})
    agent_groups: List[str] = []
    for target in normalized:
        for agent in RETRY_AGENT_ROUTES.get(target, ("Integration Agent",)):
            if agent not in agent_groups:
                agent_groups.append(agent)
    return {
        "targets": normalized,
        "agent_groups": agent_groups,
        "strategy": "targeted_dag_retry" if normalized else "none",
    }


def _walk_text_files(workspace_path: str, *, max_files: int = 500) -> Dict[str, str]:
    root = Path(workspace_path)
    if not workspace_path or not root.exists() or not root.is_dir():
        return {}

    out: Dict[str, str] = {}
    for rel_index in ("dist/index.html", "build/index.html"):
        index_path = root / rel_index
        if index_path.exists() and index_path.is_file():
            try:
                out[rel_index] = index_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if len(out) >= max_files:
                return out
            path = Path(dirpath) / filename
            if path.suffix.lower() not in TEXT_SUFFIXES and filename not in TEXT_FILENAMES:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                out[rel] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return out


def _combined(files: Mapping[str, str]) -> str:
    return "\n".join([*files.keys(), *files.values()]).lower()


def _has_file(files: Mapping[str, str], *needles: str) -> bool:
    rels = [p.lower() for p in files]
    return any(any(n.lower() in p for p in rels) for n in needles)


def _has_any_text(text: str, needles: Iterable[str]) -> bool:
    return any(n.lower() in text for n in needles)


def _read_package(files: Mapping[str, str]) -> Dict[str, Any]:
    raw = files.get("package.json") or files.get("frontend/package.json") or ""
    if not raw.strip():
        for path, text in files.items():
            if path.endswith("/package.json"):
                raw = text
                break
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"__invalid_json__": True}


_LOCAL_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^'\"\n]+?\s+from\s+)?|export\s+[^'\"\n]+?\s+from\s+|import\s*\()\s*['\"](?P<path>\.{1,2}/[^'\"]+)['\"]",
    re.MULTILINE,
)


def _resolve_local_import(files: Mapping[str, str], importer: str, raw_specifier: str) -> bool:
    specifier = raw_specifier.split("?", 1)[0].split("#", 1)[0]
    base = Path(importer).parent
    normalized = posixpath.normpath((base / specifier).as_posix())
    candidates = [normalized]
    suffixes = ("", ".js", ".jsx", ".ts", ".tsx", ".json", ".css")
    index_suffixes = ("index.js", "index.jsx", "index.ts", "index.tsx", "index.json", "index.css")
    for suffix in suffixes:
        if suffix:
            candidates.append(normalized + suffix)
    for index_name in index_suffixes:
        candidates.append((Path(normalized) / index_name).as_posix())
    existing = {p.replace("\\", "/") for p in files}
    return any(candidate in existing for candidate in candidates)


def _find_broken_local_imports(files: Mapping[str, str], *, max_items: int = 12) -> List[str]:
    broken: List[str] = []
    for rel, source in files.items():
        if not rel.endswith((".js", ".jsx", ".ts", ".tsx")):
            continue
        for match in _LOCAL_IMPORT_RE.finditer(source):
            specifier = match.group("path")
            if not _resolve_local_import(files, rel, specifier):
                broken.append(f"{rel} imports missing {specifier}")
                if len(broken) >= max_items:
                    return broken
    return broken


_CLIENT_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|private[_-]?key)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]"
    ),
)


def _find_client_exposed_secrets(files: Mapping[str, str], *, max_items: int = 8) -> List[str]:
    exposed: List[str] = []
    for rel, source in files.items():
        low = rel.lower()
        if not (
            low.startswith(("src/", "client/src/", "frontend/src/", "expo-mobile/"))
            and rel.endswith((".js", ".jsx", ".ts", ".tsx", ".json", ".env"))
        ):
            continue
        for pattern in _CLIENT_SECRET_PATTERNS:
            if pattern.search(source):
                exposed.append(rel)
                break
        if len(exposed) >= max_items:
            return exposed
    return exposed


def detect_build_profile(goal: str, files: Optional[Mapping[str, str]] = None) -> str:
    goal_lower = (goal or "").lower()

    # ── Web escape hatch (checked before everything else) ──────────────────────
    # vite.config.js / index.html as actual workspace files = unambiguous web
    # build.  Don't let stray "app.json" references in docs fool the detector.
    # Sub-classification uses ONLY goal text — file content is unreliable
    # (a marketing site legitimately mentions "pricing" in its copy, which would
    # otherwise trigger "saas_ui").
    _WEB_ANCHORS = ("vite.config.js", "vite.config.ts", "index.html", "webpack.config.js")
    if files and any(k in files for k in _WEB_ANCHORS):
        if _has_any_text(goal_lower, ("saas", "product ui", "dashboard", "analytics",
                                      "settings", "team page", "subscription")):
            return "saas_ui"
        if _has_any_text(goal_lower, ("website", "marketing site", "portfolio",
                                      "e-commerce", "ecommerce", "storefront",
                                      "landing page", "product launch", "launch page")):
            return "web_site"
        return "web"

    # ── Mobile: only trigger on goal text + explicit mobile file keys ──────────
    # Never trigger from file *content* alone — docs/READMEs routinely mention
    # "app.json" without the workspace being a React Native project.
    _MOBILE_FILE_KEYS = {"app.json", "eas.json", "app.config.js", "app.config.ts"}
    _mobile_goal = bool(re.search(
        r"\b(?:expo|react native|react-native|mobile app|app store|ios|android)\b",
        goal_lower,
    ))
    _mobile_files = files is not None and bool(_MOBILE_FILE_KEYS & set(files.keys()))
    if _mobile_goal or _mobile_files:
        return "mobile"

    text = goal_lower
    if files:
        text += "\n" + _combined(files)

    if _has_any_text(text, ("automation", "workflow", "trigger", "run_agent", "scheduled", "agent workflow")):
        return "automation"
    if _has_any_text(text, ("website", "marketing site", "portfolio", "e-commerce", "ecommerce", "storefront", "landing page")) and not _has_any_text(
        text,
        ("saas", "dashboard", "analytics", "settings", "team page", "product ui", "subscription"),
    ):
        return "web_site"
    if _has_any_text(text, ("saas", "product ui", "dashboard", "analytics", "pricing", "settings", "team page", "landing page")):
        return "saas_ui"
    if _has_any_text(text, ("api", "backend", "fastapi", "openapi", "rest", "graphql")) and not _has_any_text(
        text, ("react", "frontend", "landing", "dashboard")
    ):
        return "api_backend"
    if files and _has_file(files, "package.json", "src/app", "src/main", "src/App"):
        return "web"
    return "universal"


def validate_plan_integrity(plan: Any, *, goal: str = "") -> Dict[str, Any]:
    """Validate a pre-build plan artifact.

    This is used by the plan-first phase. It accepts either a dict or a string
    because current planners can return structured JSON or markdown.
    """

    if isinstance(plan, dict):
        text = json.dumps(plan, sort_keys=True).lower()
    else:
        text = str(plan or "").lower()

    issues: List[IntegrityIssue] = []
    requirements = {
        "pages": ("pages", "routes", "screens"),
        "components": ("components", "ui primitives", "widgets"),
        "layout": ("layout", "navigation", "shell"),
        "data": ("data", "models", "schema"),
        "dependencies": ("dependencies", "package", "libraries"),
        "file_tree": ("file tree", "folder structure", "files"),
        "risks": ("risk", "ambiguity", "assumption"),
    }
    for code, needles in requirements.items():
        if not _has_any_text(text, needles):
            issues.append(
                _issue(
                    f"plan_missing_{code}",
                    f"Plan is missing {code.replace('_', ' ')}.",
                    "plan",
                    retry_targets=("planning", "requirements"),
                )
            )

    design_option_count = len(re.findall(r"design (?:option|direction)|option [abc]|direction [123]", text))
    if detect_build_profile(goal, None) in {"saas_ui", "web"} and design_option_count < 3:
        issues.append(
            _issue(
                "plan_missing_design_options",
                "UI plan must include at least three design options and one chosen direction.",
                "plan",
                retry_targets=("planning", "design"),
            )
        )

    score = max(0, 100 - len(issues) * 12)
    return _format_result(
        phase="plan",
        profile=detect_build_profile(goal, None),
        category_scores={
            "architecture": 20 if not any(i.code.startswith("plan_missing_file_tree") for i in issues) else 8,
            "design_system": 15 if not any(i.code == "plan_missing_design_options" for i in issues) else 3,
            "completeness": max(0, 20 - len(issues) * 2),
            "runtime_validity": 25,
            "integration": 10,
            "deployability": 10,
        },
        issues=issues,
        proof=[
            {
                "proof_type": "plan",
                "title": "Plan integrity inspected",
                "payload": {"input_kind": "dict" if isinstance(plan, dict) else "text"},
            }
        ],
        override_score=score,
    )


def validate_workspace_integrity(
    workspace_path: str,
    *,
    goal: str = "",
    phase: str = "final",
    build_target: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate structure, convergence, runtime surface, and deployability."""

    files = _walk_text_files(workspace_path)
    profile = detect_build_profile(goal, files)
    if build_target:
        target = build_target.lower()
        if "agent" in target or "automation" in target:
            profile = "automation"
        elif "api" in target or "backend" in target:
            profile = "api_backend"
        elif "mobile" in target or "expo" in target:
            profile = "mobile"

    issues: List[IntegrityIssue] = []
    proof: List[Dict[str, Any]] = []
    scores = {k: 0 for k in SCORE_WEIGHTS}

    if not files:
        issues.append(
            _issue(
                "workspace_missing",
                "Workspace has no readable source/config artifacts.",
                phase,
                retry_targets=("integration", "executor"),
            )
        )
        return _format_result(phase=phase, profile=profile, category_scores=scores, issues=issues, proof=proof)

    text = _combined(files)
    pkg = _read_package(files)

    _score_architecture(files, text, pkg, profile, phase, issues, proof, scores)
    _score_design(files, text, profile, phase, issues, proof, scores)
    _score_completeness(files, text, profile, phase, issues, proof, scores)
    _score_runtime(files, text, pkg, profile, phase, issues, proof, scores)
    _score_integration(files, text, profile, phase, issues, proof, scores)
    _score_security(files, profile, phase, issues, proof)

    # ── Hard gates: content purity, manifest, stripe-first ──
    purity_violations = _check_content_type_purity(files)
    if purity_violations:
        for v in purity_violations[:8]:
            issues.append(
                _issue(
                    "content_type_violation",
                    f"Executable file contains Markdown/prose instead of code: {v}",
                    phase,
                    severity="blocker",
                    retry_targets=("frontend", "integration"),
                )
            )

    manifest_issues = _check_manifest_vs_disk(workspace_path, files)
    for mi in manifest_issues[:8]:
        issues.append(
            _issue(
                "manifest_reconciliation_failure",
                mi,
                phase,
                severity="blocker",
                retry_targets=("integration", "frontend"),
            )
        )

    stripe_issues = _check_stripe_first(files)
    for si in stripe_issues[:4]:
        issues.append(
            _issue(
                "stripe_first_violation",
                si,
                phase,
                severity="blocker",
                retry_targets=("backend", "integration"),
            )
        )
    _score_deployability(files, text, pkg, profile, phase, issues, proof, scores)

    return _format_result(
        phase=phase,
        profile=profile,
        category_scores=scores,
        issues=issues,
        proof=proof,
    )


def _score_architecture(
    files: Mapping[str, str],
    text: str,
    pkg: Mapping[str, Any],
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    score = 0
    if pkg and "__invalid_json__" not in pkg:
        score += 4
    elif profile == "api_backend" and _has_file(files, "requirements.txt", "pyproject.toml", "Pipfile"):
        score += 4
    else:
        issues.append(_issue("missing_package_json", "Missing or invalid package.json.", phase, retry_targets=("stack", "integration")))

    if _has_file(files, "index.html") or _has_file(files, "client/index.html"):
        score += 3
    elif profile in {"web", "web_site", "saas_ui", "mobile"}:
        issues.append(_issue("missing_html_shell", "Missing browser HTML shell/root.", phase, retry_targets=("frontend", "integration")))

    if _has_file(files, "src/main", "client/src/main", "src/index"):
        score += 4
    elif profile in {"web", "web_site", "saas_ui", "mobile"}:
        issues.append(_issue("missing_entry_point", "Missing app entry point.", phase, retry_targets=("frontend", "integration")))

    if _has_file(files, "src/App", "client/src/App", "app/page", "app/layout"):
        score += 4
    elif profile in {"web", "web_site", "saas_ui", "mobile"}:
        issues.append(_issue("missing_root_app", "Missing root app component.", phase, retry_targets=("frontend", "integration")))

    if _has_any_text(text, ("<route", "routes", "browserrouter", "memoryrouter", "wouter", "createbrowserrouter")):
        score += 3
    elif profile in {"web", "saas_ui"}:
        issues.append(_issue("missing_route_map", "Missing route map/router wiring.", phase, retry_targets=("frontend", "integration")))

    if profile == "api_backend":
        if _has_file(files, "backend", "server", "app/main.py") and _has_any_text(text, ("fastapi", "express", "openapi", "@app.", "router")):
            score += 5
        else:
            issues.append(_issue("missing_api_surface", "Backend/API profile lacks route surface.", phase, retry_targets=("backend", "integration")))
    elif profile == "automation":
        if _has_file(files, "automation", "workflows", "agents") and _has_any_text(text, ("workflow", "trigger", "executor", "runtime", "run_agent")):
            score += 12
        else:
            issues.append(_issue("missing_automation_architecture", "Automation profile lacks workflow/trigger/runtime architecture.", phase, retry_targets=("automation", "integration")))
    elif profile == "mobile":
        if _has_any_text(text, ("expo", "react-native", "app.json", "eas.json", "@react-navigation")):
            score += 2

    scores["architecture"] = min(SCORE_WEIGHTS["architecture"], score)
    proof.append({"proof_type": "structure", "title": "Architecture inspected", "payload": {"score": scores["architecture"]}})


def _score_design(
    files: Mapping[str, str],
    text: str,
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    if profile not in {"saas_ui", "web_site", "mobile"}:
        scores["design_system"] = SCORE_WEIGHTS["design_system"]
        return

    if profile == "mobile":
        score = 0
        if _has_any_text(text, ("stylesheet.create", "styles =", "react-native")):
            score += 7
        if _has_any_text(text, ("app.json", "userinterfacestyle", "backgroundcolor", "orientation")):
            score += 4
        if _has_any_text(text, ("safeareaview", "scrollview", "pressable", "statusbar")):
            score += 4
        if score < 10:
            issues.append(_issue("weak_mobile_design_system", "Mobile build lacks React Native styling/layout primitives.", phase, retry_targets=("design", "mobile")))
        scores["design_system"] = min(SCORE_WEIGHTS["design_system"], score)
        proof.append({"proof_type": "design", "title": "Mobile design system inspected", "payload": {"score": scores["design_system"]}})
        return

    score = 0
    if _has_file(files, "ideas.md", "design", "tokens"):
        score += 4
    elif profile in {"saas_ui", "web_site"}:
        issues.append(_issue("missing_design_artifact", "UI build lacks a concrete design artifact such as ideas.md.", phase, retry_targets=("design",)))

    css_text = "\n".join(v for k, v in files.items() if k.endswith((".css", ".md", ".tsx", ".jsx"))).lower()
    token_needles = ("--primary", "--background", "--foreground", "--chart", "--sidebar", "--radius")
    token_hits = [n for n in token_needles if n in css_text]
    if len(token_hits) >= 4:
        score += 6
    else:
        issues.append(_issue("weak_design_tokens", "Design system lacks enough reusable color/layout/chart/sidebar tokens.", phase, retry_targets=("design", "frontend")))

    if _has_any_text(text, ("tailwind", "class-variance-authority", "radix", "shadcn", "buttonvariants", "component variants")):
        score += 3
    elif profile in {"saas_ui", "web_site"}:
        issues.append(_issue("missing_component_variants", "SaaS/product UI lacks component variant system evidence.", phase, retry_targets=("design", "frontend")))

    if _has_any_text(text, ("font-family", "typography", "inter", "jakarta", "font-sans")):
        score += 2

    scores["design_system"] = min(SCORE_WEIGHTS["design_system"], score)
    proof.append({"proof_type": "design", "title": "Design system inspected", "payload": {"token_hits": token_hits, "score": scores["design_system"]}})


def _page_source(files: Mapping[str, str], page_name: str) -> str:
    needle = page_name.lower()
    candidates: List[str] = []
    for rel, source in files.items():
        low = rel.lower().replace("\\", "/")
        stem = Path(rel).stem.lower()
        if low.startswith(("src/pages/", "client/src/pages/", "frontend/src/pages/")) and stem == needle:
            candidates.append(source)
    if candidates:
        return "\n".join(candidates).lower()
    return ""


def _validate_visual_contracts(
    files: Mapping[str, str],
    text: str,
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
) -> int:
    """Prompt-specific visual/product QA.

    The old failure mode was a runnable shell with scattered keywords. This
    makes the validator inspect each route-level page for the sections users
    naturally expect from that product type.
    """

    if profile == "saas_ui":
        contracts = {
            "home": ("hero", "feature", "cta"),
            "dashboard": ("kpi", "chart", "table"),
            "analytics": ("chart", "funnel", "cohort", "top pages"),
            "team": ("invite", "role", "member", "search"),
            "pricing": ("plans", "pricing", "faq"),
            "settings": ("profile", "security", "billing", "integrations"),
        }
        missing: List[str] = []
        for page, needles in contracts.items():
            source = _page_source(files, page)
            if not source:
                continue
            hit_count = sum(1 for needle in needles if needle in source)
            if hit_count < min(3, len(needles)):
                missing.append(f"{page}({hit_count}/{len(needles)})")
        visual_needles = ("<img", "background-image", "url(", ".png", ".jpg", ".jpeg", ".webp", "recharts", "area chart", "barchart", "linechart", "piechart", "svg")
        has_visual_asset = any(needle in text for needle in visual_needles)
        if missing:
            issues.append(
                _issue(
                    "weak_saas_page_contract",
                    "SaaS pages do not meet route-level visual/product contracts: " + ", ".join(missing),
                    phase,
                    retry_targets=("frontend", "design", "integration"),
                )
            )
        if not has_visual_asset:
            issues.append(
                _issue(
                    "missing_visual_assets",
                    "SaaS/product UI lacks charts, imagery, SVG/canvas, or comparable visual assets.",
                    phase,
                    retry_targets=("design", "frontend"),
                )
            )
        proof.append(
            {
                "proof_type": "visual_qa",
                "title": "Route-level SaaS visual contracts inspected",
                "payload": {"weak_pages": missing, "has_visual_asset": has_visual_asset},
            }
        )
        return max(0, 4 - len(missing) - (0 if has_visual_asset else 2))

    if profile == "web_site":
        site_terms = ("hero", "nav", "feature", "cta", "testimonial", "pricing", "contact", "footer")
        hits = [term for term in site_terms if term in text]
        has_visual_asset = any(needle in text for needle in ("<img", "background-image", "url(", ".png", ".jpg", ".jpeg", ".webp", "svg", "canvas"))
        if len(hits) < 5:
            issues.append(
                _issue(
                    "thin_website_sections",
                    "Website build lacks enough public-site sections: " + ", ".join(sorted(set(site_terms) - set(hits))),
                    phase,
                    retry_targets=("frontend", "design"),
                )
            )
        if not has_visual_asset:
            issues.append(
                _issue(
                    "missing_website_visual_assets",
                    "Website build lacks imagery, SVG/canvas, or comparable visual assets.",
                    phase,
                    retry_targets=("design", "frontend"),
                )
            )
        proof.append(
            {
                "proof_type": "visual_qa",
                "title": "Website visual contracts inspected",
                "payload": {"section_hits": hits, "has_visual_asset": has_visual_asset},
            }
        )
        return min(4, len(hits) // 2) + (1 if has_visual_asset else 0)

    return 4


def _score_completeness(
    files: Mapping[str, str],
    text: str,
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    score = 0
    if profile == "saas_ui":
        required = {
            "home": ("src/pages/home", "/"),
            "dashboard": ("src/pages/dashboard", "/dashboard"),
            "analytics": ("src/pages/analytics", "/analytics"),
            "team": ("src/pages/team", "/team"),
            "pricing": ("src/pages/pricing", "/pricing"),
            "settings": ("src/pages/settings", "/settings"),
        }
        present = [name for name, (path_hint, route_hint) in required.items() if path_hint in text and route_hint in text]
        score += int(12 * len(present) / len(required))
        missing = sorted(set(required) - set(present))
        if missing:
            issues.append(_issue("missing_saas_pages", "SaaS build missing mounted pages: " + ", ".join(missing), phase, retry_targets=("frontend", "integration")))
        section_needles = ("hero", "feature", "cta", "kpi", "chart", "table", "invite", "plans", "faq", "security", "billing")
        hits = [n for n in section_needles if n in text]
        score += min(8, len(hits))
        if len(hits) < 8:
            issues.append(_issue("thin_product_sections", "SaaS build lacks rich product sections/data density.", phase, retry_targets=("frontend", "design")))
        score += _validate_visual_contracts(files, text, profile, phase, issues, proof)
    elif profile == "web_site":
        if _has_file(files, "src/pages/home", "client/src/pages/home", "src/App", "client/src/App"):
            score += 8
        else:
            issues.append(_issue("missing_website_surface", "Website build lacks a mounted home/landing surface.", phase, retry_targets=("frontend", "integration")))
        section_needles = ("hero", "nav", "feature", "cta", "testimonial", "pricing", "contact", "footer")
        hits = [n for n in section_needles if n in text]
        score += min(8, len(hits))
        score += _validate_visual_contracts(files, text, profile, phase, issues, proof)
    elif profile == "mobile":
        if _has_any_text(text, ("expo", "react-native", "react native")):
            score += 8
        else:
            issues.append(_issue("missing_mobile_framework", "Mobile build must use Expo/React Native or declare an equivalent.", phase, retry_targets=("mobile", "stack")))
        if _has_file(files, "App.tsx", "App.jsx", "app.json") or _has_any_text(text, ("app.json", "eas.json")):
            score += 8
        else:
            issues.append(_issue("missing_mobile_entry", "Mobile build lacks App entry or Expo metadata.", phase, retry_targets=("mobile", "integration")))
        if _has_any_text(text, ("screen", "navigation", "@react-navigation")):
            score += 4
    elif profile == "automation":
        if _has_any_text(text, ("trigger", "schedule", "webhook", "cron")):
            score += 7
        else:
            issues.append(_issue("missing_automation_trigger", "Automation build lacks trigger definition.", phase, retry_targets=("automation", "integration")))
        if _has_any_text(text, ("workflow", "steps", "agent", "run_agent")):
            score += 7
        else:
            issues.append(_issue("missing_workflow_definition", "Automation build lacks workflow/agent definition.", phase, retry_targets=("automation", "integration")))
        if _has_file(files, "automation", "workflows", "agents") or _has_any_text(text, ("executor", "runtime")):
            score += 6
    elif profile == "api_backend":
        route_hits = sum(1 for n in ("@app.get", "@router", "fastapi", "express", "openapi", "health") if n in text)
        score += min(20, route_hits * 4)
        if route_hits < 3:
            issues.append(_issue("thin_api_contract", "API build lacks enough route/schema/health evidence.", phase, retry_targets=("backend", "integration")))
    else:
        score = 16 if _has_file(files, "src", "backend", "server") else 8

    if profile in {"web", "web_site", "saas_ui", "api_backend"}:
        placeholder_hits = [
            p
            for p in (
                "placeholder",
                "sample page",
                "configure cmd for your app",
                "todo: implement",
                "crucib_incomplete",
            )
            if p in text
        ]
        if placeholder_hits:
            issues.append(_issue("placeholder_language", "Final output contains placeholder/scaffold language: " + ", ".join(placeholder_hits), phase, retry_targets=("integration", "frontend")))
            score = max(0, score - 6)

    scores["completeness"] = min(SCORE_WEIGHTS["completeness"], score)
    proof.append({"proof_type": "product", "title": "Completeness inspected", "payload": {"profile": profile, "score": scores["completeness"]}})


def _score_runtime(
    files: Mapping[str, str],
    text: str,
    pkg: Mapping[str, Any],
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    score = 0
    scripts = pkg.get("scripts") if isinstance(pkg, Mapping) else {}
    if profile == "api_backend":
        if _has_file(files, "requirements.txt", "pyproject.toml", "Pipfile"):
            score += 7
        if _has_any_text(text, ("uvicorn", "gunicorn", "fastapi", "pytest")):
            score += 7
        if _has_any_text(text, ("try:", "except ", "httpexception", "pydantic")):
            score += 4
        score += 7
        scores["runtime_validity"] = min(SCORE_WEIGHTS["runtime_validity"], score)
        proof.append({"proof_type": "runtime", "title": "Runtime validity inspected", "payload": {"phase": phase, "score": scores["runtime_validity"]}})
        return

    if isinstance(scripts, Mapping) and scripts.get("build"):
        score += 7
    elif profile in {"web", "web_site", "saas_ui", "mobile"}:
        issues.append(_issue("missing_build_script", "package.json lacks build script.", phase, retry_targets=("stack", "integration")))

    if isinstance(scripts, Mapping) and (scripts.get("dev") or scripts.get("start")):
        score += 4
    if isinstance(scripts, Mapping) and (scripts.get("test") or scripts.get("check")):
        score += 4

    if phase in {"runtime", "final"} and profile in {"web", "web_site", "saas_ui"}:
        if _has_file(files, "dist/index.html", "build/index.html"):
            score += 7
        else:
            issues.append(_issue("missing_static_preview_artifact", "Final web build lacks dist/index.html or build/index.html.", phase, retry_targets=("verification", "frontend")))
    else:
        score += 7

    if _has_any_text(text, ("errorboundary", "try {", "catch (", "try:", "except ")):
        score += 3

    scores["runtime_validity"] = min(SCORE_WEIGHTS["runtime_validity"], score)
    proof.append({"proof_type": "runtime", "title": "Runtime validity inspected", "payload": {"phase": phase, "score": scores["runtime_validity"]}})


def _score_integration(
    files: Mapping[str, str],
    text: str,
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    score = 10
    broken_imports = _find_broken_local_imports(files)
    if broken_imports:
        score = max(0, score - min(10, len(broken_imports) * 3))
        issues.append(
            _issue(
                "broken_local_imports",
                "Local imports do not resolve: " + "; ".join(broken_imports[:8]),
                phase,
                retry_targets=("integration", "frontend"),
            )
        )

    app_text = "\n".join(v for k, v in files.items() if k.lower().endswith(("app.jsx", "app.tsx", "app.js", "app.ts"))).lower()
    orphans: List[str] = []
    for rel in files:
        low = rel.lower()
        if not low.startswith(("src/pages/", "client/src/pages/", "src/features/", "client/src/features/")):
            continue
        if any(x in low for x in (".test.", ".spec.", "types.", "mock", "__tests__")):
            continue
        stem = Path(rel).stem.lower()
        if stem in {"index", "types", "data"}:
            continue
        if profile == "saas_ui" and low.startswith(("src/pages/", "client/src/pages/")) and stem not in app_text:
            orphans.append(rel)
        elif low.startswith(("src/features/", "client/src/features/")) and stem not in text.replace(files[rel].lower(), "", 1):
            orphans.append(rel)

    if orphans:
        score = max(0, score - min(10, len(orphans) * 2))
        issues.append(_issue("orphan_product_files", "Generated product files are not referenced from the runnable app: " + ", ".join(orphans[:8]), phase, retry_targets=("integration",)))

    scores["integration"] = score
    proof.append(
        {
            "proof_type": "integration",
            "title": "Convergence/import/orphan check inspected",
            "payload": {"orphans": orphans[:20], "broken_imports": broken_imports[:20], "score": score},
        }
    )


def _score_security(
    files: Mapping[str, str],
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
) -> None:
    exposed = _find_client_exposed_secrets(files)
    if exposed:
        issues.append(
            _issue(
                "client_secret_exposed",
                "Potential secret material is present in client-delivered code: " + ", ".join(exposed[:8]),
                phase,
                retry_targets=("security", "frontend"),
            )
        )
    proof.append(
        {
            "proof_type": "security",
            "title": "Client secret exposure scan inspected",
            "payload": {"profile": profile, "exposed_files": exposed[:20]},
        }
    )


def _score_deployability(
    files: Mapping[str, str],
    text: str,
    pkg: Mapping[str, Any],
    profile: str,
    phase: str,
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    scores: Dict[str, int],
) -> None:
    score = 0
    if _has_file(files, "Dockerfile", "railway.json", "vercel.json", "netlify.toml", "render.yaml", "deploy"):
        score += 4
    if _has_file(files, "README", "README_BUILD", "DEPLOY") or _has_any_text(text, ("how to run", "deployment", "deploy")):
        score += 3
    scripts = pkg.get("scripts") if isinstance(pkg, Mapping) else {}
    if isinstance(scripts, Mapping) and (scripts.get("start") or scripts.get("preview")):
        score += 3
    elif profile == "api_backend" and _has_any_text(text, ("uvicorn", "gunicorn", "fastapi")):
        score += 3

    if "configure cmd for your app" in text:
        issues.append(_issue("placeholder_deploy_command", "Deploy files contain placeholder command text.", phase, retry_targets=("deploy", "integration")))
        score = 0

    scores["deployability"] = min(SCORE_WEIGHTS["deployability"], score)
    proof.append({"proof_type": "deploy", "title": "Deployability inspected", "payload": {"score": scores["deployability"]}})




# ── Content-Type Purity Gate ─────────────────────────────────────────────────
_MARKDOWN_STARTS = (
    re.compile(r"^#{1,6}\s", re.MULTILINE),   # ## heading at start of file
    re.compile(r"^\*\*[A-Za-z]", re.MULTILINE),  # **bold text at line start
    re.compile(r"^```"),                          # fenced code block
    re.compile(r"^>\s"),                          # blockquote
    re.compile(r"^I am the ", re.IGNORECASE),     # agent self-identification
    re.compile(r"^Generating production", re.IGNORECASE),  # agent activity prose
    re.compile(r"^This file (is|contains|implements)", re.IGNORECASE),
)
_EXECUTABLE_EXTENSIONS = {".jsx", ".tsx", ".ts", ".js", ".mjs"}


def _check_content_type_purity(files: Mapping[str, str]) -> List[str]:
    """Return list of paths where an executable file starts with Markdown/prose."""
    violations: List[str] = []
    for rel, source in files.items():
        ext = Path(rel).suffix.lower()
        if ext not in _EXECUTABLE_EXTENSIONS:
            continue
        # Strip leading whitespace/BOM then check first non-blank line
        stripped = source.lstrip("\ufeff\n\r ")
        if not stripped:
            continue
        first_line = stripped.splitlines()[0] if stripped.splitlines() else ""
        for pattern in _MARKDOWN_STARTS:
            if pattern.match(first_line):
                violations.append(rel)
                break
    return violations


# ── Manifest-vs-Disk Reconciliation Gate ─────────────────────────────────────

def _check_manifest_vs_disk(workspace_path: str, files: Mapping[str, str]) -> List[str]:
    """Compare META/merge_map.json claimed paths/sizes against actual disk state."""
    issues: List[str] = []
    root = Path(workspace_path)
    manifest_path = root / "META" / "merge_map.json"
    if not manifest_path.exists():
        return []  # no manifest = skip (not all builds use one)
    try:
        raw = manifest_path.read_text(encoding="utf-8", errors="replace")
        manifest = json.loads(raw)
    except Exception:
        return ["MANIFEST_INVALID_JSON: META/merge_map.json could not be parsed"]

    claimed = manifest.get("files", [])
    if not claimed:
        return []

    for entry in claimed:
        if not isinstance(entry, dict):
            continue
        rel_path = entry.get("path", "")
        if not rel_path:
            continue
        claimed_bytes = entry.get("approx_bytes") or entry.get("size") or 0
        abs_path = root / rel_path.lstrip("/")
        if not abs_path.exists():
            issues.append(f"MANIFEST_MISSING: {rel_path} claimed in manifest but absent on disk")
            continue
        if abs_path.stat().st_size == 0:
            issues.append(f"MANIFEST_EMPTY: {rel_path} exists but is 0 bytes (manifest claimed {claimed_bytes}B)")
            continue
        if claimed_bytes and claimed_bytes > 200:
            actual = abs_path.stat().st_size
            ratio = actual / claimed_bytes
            if ratio < 0.20:
                issues.append(
                    f"MANIFEST_OVERWRITE_SUSPECTED: {rel_path} claimed={claimed_bytes}B "
                    f"actual={actual}B ratio={ratio:.2f} — possible agent overwrite"
                )
    return issues


# ── Stripe-First Payment Enforcement Gate ────────────────────────────────────
_BRAINTREE_PATTERNS = (
    re.compile(r"braintree", re.IGNORECASE),
    re.compile(r"BraintreeGateway", re.IGNORECASE),
    re.compile(r"sandbox\.braintreegateway", re.IGNORECASE),
)
_PAYMENT_EXTENSIONS = {".py", ".ts", ".js", ".jsx", ".tsx"}


def _check_stripe_first(
    files: Mapping[str, str],
    user_requested_braintree: bool = False,
) -> List[str]:
    """Fail if Braintree appears in generated customer app code without explicit user request."""
    if user_requested_braintree:
        return []
    violations: List[str] = []
    for rel, source in files.items():
        ext = Path(rel).suffix.lower()
        if ext not in _PAYMENT_EXTENSIONS:
            continue
        # Only check generated customer app code, not CrucibAI platform billing
        low = rel.lower()
        is_platform_billing = any(
            seg in low for seg in ("routes/braintree", "services/braintree", "migrations/018", "migrations/019")
        )
        if is_platform_billing:
            continue
        for pattern in _BRAINTREE_PATTERNS:
            if pattern.search(source):
                violations.append(
                    f"STRIPE_FIRST_VIOLATION: {rel} contains Braintree integration. "
                    f"Use Stripe Checkout/Billing/Customer Portal for generated apps. "
                    f"Only use Braintree when user explicitly requests it."
                )
                break
    return violations

def _format_result(
    *,
    phase: str,
    profile: str,
    category_scores: Mapping[str, int],
    issues: List[IntegrityIssue],
    proof: List[Dict[str, Any]],
    override_score: Optional[int] = None,
) -> Dict[str, Any]:
    score = int(override_score if override_score is not None else sum(category_scores.values()))
    retry_targets = sorted({target for issue in issues for target in issue.retry_targets})
    retry_route = route_retry_targets(retry_targets)
    hard_block = score < HARD_FAIL_THRESHOLD or any(i.severity == "blocker" for i in issues)
    passed = score >= RETRY_THRESHOLD and not issues
    return {
        "passed": passed,
        "score": score,
        "profile": profile,
        "phase": phase,
        "thresholds": {"retry": RETRY_THRESHOLD, "hard_fail": HARD_FAIL_THRESHOLD},
        "category_scores": dict(category_scores),
        "issues": [i.message for i in issues],
        "structured_issues": [i.as_dict() for i in issues],
        "retry_targets": retry_targets,
        "retry_route": retry_route,
        "hard_block": hard_block,
        "recommendation": "approved" if passed else ("hard_fail" if hard_block else "retry"),
        "proof": proof,
    }
