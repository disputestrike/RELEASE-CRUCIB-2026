"""BuildContract artifact helpers for production workspaces.

The docs call for one contract truth that every agent, verifier, repair pass,
preview, and export path can inspect. This module keeps that truth on disk in
``.crucibai/`` and derives route/dependency maps from the final files instead
of trusting agent claims.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from .build_contract import BuildContract, ContractDelta
from .build_type_blueprints import get_blueprint
from .contract_generator import BuildContractGenerator
from .intent_classifier import IntentClassifier


IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^'\"\n]+?\s+from\s+)?|export\s+[^'\"\n]+?\s+from\s+|import\s*\()\s*['\"](?P<path>\.{1,2}/[^'\"]+)['\"]",
    re.MULTILINE,
)


def _read_text_files(workspace_path: str, *, max_files: int = 600) -> Dict[str, str]:
    root = Path(workspace_path)
    if not workspace_path or not root.exists():
        return {}
    skip = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", "build", ".next"}
    out: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if len(out) >= max_files:
                return out
            if not name.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".json", ".html", ".md", ".py", ".sql")) and name != "Dockerfile":
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            try:
                out[rel] = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return out


def generate_contract_for_job(job: Mapping[str, Any], *, build_id: Optional[str] = None) -> BuildContract:
    """Generate and freeze a BuildContract from the current job goal."""

    goal = str(job.get("goal") or job.get("prompt") or job.get("description") or "")
    jid = str(build_id or job.get("id") or job.get("job_id") or "build")
    dimensions = IntentClassifier().classify(goal)
    contract = BuildContractGenerator().generate(dimensions, goal, jid)
    contract.freeze()
    return contract


def _route_present(route: str, files: Mapping[str, str]) -> bool:
    if route == "/":
        return any(path.endswith(("App.jsx", "App.tsx", "HomePage.jsx", "HomePage.tsx")) for path in files)
    route_text = route.strip("/")
    if not route_text:
        return False
    lower_paths = " ".join(files.keys()).lower()
    lower_text = "\n".join(files.values()).lower()
    page_hint = f"{route_text}page"
    return (
        page_hint in lower_paths
        or f'path="/{route_text}"' in lower_text
        or f"path='/{route_text}'" in lower_text
        or f"to=\"/{route_text}\"" in lower_text
        or f"to='/{route_text}'" in lower_text
        or f'href="/{route_text}"' in lower_text
    )


def derive_route_map(files: Mapping[str, str], required_routes: Iterable[str]) -> Dict[str, str]:
    """Build a route map from actual page files and route declarations."""

    route_map: Dict[str, str] = {}
    for route in required_routes:
        if not _route_present(route, files):
            continue
        if route == "/":
            route_map[route] = "src/pages/HomePage.jsx"
            continue
        stem = route.strip("/").replace("-", "")
        for path in files:
            normalized = path.lower().replace("-", "")
            if normalized.endswith((f"{stem}page.jsx", f"{stem}page.tsx")):
                route_map[route] = path
                break
        route_map.setdefault(route, "src/routes.jsx")
    return route_map


def derive_dependency_graph(files: Mapping[str, str]) -> Dict[str, list[str]]:
    """Extract local JS/TS dependency edges from the actual disk files."""

    graph: Dict[str, list[str]] = {}
    for rel, source in files.items():
        if not rel.endswith((".js", ".jsx", ".ts", ".tsx")):
            continue
        deps = []
        for match in IMPORT_RE.finditer(source):
            deps.append(match.group("path"))
        if deps:
            graph[rel] = deps
    return graph


def update_contract_progress_from_workspace(
    contract: BuildContract,
    workspace_path: str,
    *,
    files: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Mark contract items done/missing from actual disk state."""

    source_files = dict(files or _read_text_files(workspace_path))
    actual_paths = set(source_files)

    for rel in contract.required_files:
        contract.update_progress("required_files", rel, done=rel in actual_paths)

    route_map = derive_route_map(source_files, contract.required_routes)
    for route in contract.required_routes:
        contract.update_progress("required_routes", route, done=route in route_map)

    for route in contract.required_preview_routes:
        contract.update_progress("required_preview_routes", route, done=route in route_map)

    combined = "\n".join(source_files.values()).lower()
    pkg = {}
    try:
        pkg = json.loads(source_files.get("package.json") or "{}")
    except json.JSONDecodeError:
        pkg = {}
    scripts = pkg.get("scripts") if isinstance(pkg, dict) else {}
    section_terms = {
        "hero": ("hero", "headline", "h1"),
        "features": ("feature", "benefit", "capability"),
        "pricing": ("pricing", "plan", "price"),
        "testimonials": ("testimonial", "quote", "customer"),
        "footer": ("footer", "contact", "copyright"),
    }
    for test in contract.required_tests:
        done = False
        if test == "test_build":
            done = isinstance(scripts, dict) and bool(scripts.get("build"))
        elif test == "test_routes":
            done = all(route in route_map for route in contract.required_routes)
        elif test == "test_visual_sections":
            done = all(any(term in combined for term in terms) for terms in section_terms.values())
        else:
            done = any(test.lower() in path.lower() for path in actual_paths)
        contract.update_progress("required_tests", test, done=done)

    return {
        "files": source_files,
        "route_map": route_map,
        "dependency_graph": derive_dependency_graph(source_files),
        "missing": contract.get_missing_items(),
    }


def persist_contract_artifacts(workspace_path: str, job: Mapping[str, Any]) -> Dict[str, Any]:
    """Generate, reconcile, and write contract artifacts into ``.crucibai``."""

    contract = generate_contract_for_job(job)
    derived = update_contract_progress_from_workspace(contract, workspace_path)
    root = Path(workspace_path)
    meta = root / ".crucibai"
    meta.mkdir(parents=True, exist_ok=True)

    blueprint = get_blueprint(contract.build_class)
    payload = contract.to_dict()
    payload["blueprint"] = blueprint
    payload["route_map"] = derived["route_map"]
    payload["dependency_graph"] = derived["dependency_graph"]

    (meta / "build_contract.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (meta / "contract_progress.json").write_text(json.dumps(contract.contract_progress, indent=2), encoding="utf-8")
    (meta / "route_map.json").write_text(json.dumps(derived["route_map"], indent=2), encoding="utf-8")
    (meta / "dependency_graph.json").write_text(json.dumps(derived["dependency_graph"], indent=2), encoding="utf-8")

    return {
        "contract": contract,
        "contract_dict": payload,
        "route_map": derived["route_map"],
        "dependency_graph": derived["dependency_graph"],
        "missing": derived["missing"],
        "satisfied": contract.is_satisfied(),
    }


CONTRACT_COMPARE_FIELDS = (
    "build_class",
    "dimensions",
    "stack",
    "required_files",
    "required_folders",
    "required_routes",
    "required_pages",
    "required_backend_modules",
    "required_api_endpoints",
    "required_database_tables",
    "required_migrations",
    "required_workers",
    "required_integrations",
    "required_tests",
    "required_docs",
    "required_preview_routes",
    "required_visual_checks",
    "required_screenshots",
    "required_proof_types",
)


def _load_existing_contract(workspace_path: str, job: Mapping[str, Any]) -> BuildContract:
    path = Path(workspace_path) / ".crucibai" / "build_contract.json"
    if path.exists():
        try:
            return BuildContract.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return generate_contract_for_job(job)


def _contract_changes(old: BuildContract, new: BuildContract) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field_name in CONTRACT_COMPARE_FIELDS:
        old_value = getattr(old, field_name, None)
        new_value = getattr(new, field_name, None)
        if old_value != new_value:
            changes.append({"field": field_name, "old": old_value, "new": new_value})
    return changes


def persist_steering_contract_delta(
    workspace_path: str,
    job: Mapping[str, Any],
    instruction: str,
    *,
    approved_by: str = "human_user",
) -> Dict[str, Any]:
    """Convert a steering instruction into a versioned contract delta.

    Steering must not restart or erase the workspace. It creates an active goal
    from the original contract plus the new instruction, generates a new
    contract candidate, records the delta, and reconciles that contract against
    the current disk tree.
    """

    message = str(instruction or "").strip()
    if not message:
        return {"accepted": False, "reason": "empty_instruction"}

    root = Path(workspace_path)
    meta = root / ".crucibai"
    meta.mkdir(parents=True, exist_ok=True)

    previous = _load_existing_contract(workspace_path, job)
    active_goal = (
        f"{previous.original_goal.strip()}\n\n"
        f"User steering request:\n{message}"
    ).strip()
    dimensions = IntentClassifier().classify(active_goal)
    updated = BuildContractGenerator().generate(
        dimensions,
        active_goal,
        previous.build_id,
    )
    updated.version = int(previous.version or 1) + 1
    updated.status = "frozen"
    changes = _contract_changes(previous, updated)

    delta = ContractDelta(
        delta_id=f"delta_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc),
        previous_version=int(previous.version or 1),
        new_version=int(updated.version),
        changes=changes,
        reason=message,
        trigger="human_request",
        approved_by=approved_by,
        context={
            "previous_build_class": previous.build_class,
            "new_build_class": updated.build_class,
            "active_goal": active_goal,
        },
    )

    derived = update_contract_progress_from_workspace(updated, workspace_path)
    payload = updated.to_dict()
    payload["blueprint"] = get_blueprint(updated.build_class)
    payload["route_map"] = derived["route_map"]
    payload["dependency_graph"] = derived["dependency_graph"]
    payload["active_goal"] = active_goal

    (meta / "build_contract.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (meta / "contract_progress.json").write_text(json.dumps(updated.contract_progress, indent=2), encoding="utf-8")
    (meta / "route_map.json").write_text(json.dumps(derived["route_map"], indent=2), encoding="utf-8")
    (meta / "dependency_graph.json").write_text(json.dumps(derived["dependency_graph"], indent=2), encoding="utf-8")
    with (meta / "contract_deltas.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(delta.to_dict()) + "\n")

    return {
        "accepted": True,
        "delta": delta.to_dict(),
        "active_goal": active_goal,
        "contract": payload,
        "missing": derived["missing"],
        "satisfied": updated.is_satisfied(),
    }
