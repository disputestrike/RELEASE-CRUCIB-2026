"""Targeted DAG retry planning for Build Integrity Validator failures.

The BIV already tells us *what* failed. This module turns those categories into
an executable, bounded repair plan so the final gate does not degrade into a
generic rerun.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


TARGET_STEP_KEYS: Dict[str, Tuple[str, str]] = {
    "planning": ("planning.requirements", "Repair or regenerate the build plan and acceptance contract."),
    "requirements": ("planning.requirements", "Clarify missing requirements before code changes."),
    "design": ("frontend.styling", "Repair design direction, tokens, page visual contracts, and assets."),
    "frontend": ("frontend.scaffold", "Repair frontend entry points, routes, pages, and components."),
    "backend": ("backend.routes", "Repair backend/API routes, schemas, and service wiring."),
    "stack": ("frontend.scaffold", "Repair package scripts, dependencies, and build configuration."),
    "mobile": ("mobile.expo", "Repair Expo metadata, App entry, screens, and packaging guidance."),
    "automation": ("automation.workflow", "Repair triggers, workflow definition, run_agent bridge, and executor files."),
    "security": ("verification.security", "Remove exposed secrets and unsafe client-delivered values."),
    "verification": ("verification.preview", "Repair preview/build artifacts and runtime readiness."),
    "deploy": ("deploy.build", "Repair deployment config, start command, and run instructions."),
    "executor": ("implementation.integration", "Repair workspace execution/state handoff."),
    "integration": ("implementation.integration", "Repair imports, orphan files, routing, and final assembly."),
}

TARGET_PRIORITY = {
    "planning": 0,
    "requirements": 1,
    "stack": 2,
    "design": 3,
    "frontend": 4,
    "backend": 5,
    "mobile": 6,
    "automation": 7,
    "security": 8,
    "integration": 9,
    "verification": 10,
    "deploy": 11,
    "executor": 12,
}


def _normalize_targets(targets: Iterable[Any]) -> List[str]:
    normalized = {str(target or "").strip().lower() for target in targets}
    normalized.discard("")
    return sorted(normalized, key=lambda item: TARGET_PRIORITY.get(item, 99))


def build_targeted_retry_plan(biv_result: Mapping[str, Any], *, max_steps: int = 4) -> Dict[str, Any]:
    """Create a deterministic repair plan from a BIV result."""

    targets = _normalize_targets(biv_result.get("retry_targets") or [])
    if not targets:
        targets = ["integration"]

    steps: List[Dict[str, Any]] = []
    seen_step_keys: set[str] = set()
    for target in targets:
        step_key, focus = TARGET_STEP_KEYS.get(target, TARGET_STEP_KEYS["integration"])
        if step_key in seen_step_keys:
            continue
        seen_step_keys.add(step_key)
        steps.append(
            {
                "target": target,
                "step_key": step_key,
                "repair_focus": focus,
                "agent_groups": [
                    group
                    for group in ((biv_result.get("retry_route") or {}).get("agent_groups") or [])
                    if isinstance(group, str)
                ],
            }
        )
        if len(steps) >= max_steps:
            break

    return {
        "strategy": "targeted_dag_retry",
        "source": "build_integrity_validator",
        "score": biv_result.get("score"),
        "profile": biv_result.get("profile"),
        "issues": list((biv_result.get("issues") or [])[:30]),
        "targets": targets,
        "steps": steps,
    }


async def run_targeted_biv_retry(
    *,
    workspace_path: str,
    biv_result: Mapping[str, Any],
    retry_count: int,
    job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run bounded targeted repairs for a failed BIV result."""

    from .brain_repair import run_full_brain_repair

    plan = build_targeted_retry_plan(biv_result)
    attempts: List[Dict[str, Any]] = []
    workspace_fixed = False
    files_repaired: List[str] = []

    for index, step in enumerate(plan["steps"], 1):
        error_payload = {
            "target": step["target"],
            "repair_focus": step["repair_focus"],
            "biv_score": biv_result.get("score"),
            "biv_profile": biv_result.get("profile"),
            "issues": (biv_result.get("issues") or [])[:30],
            "structured_issues": (biv_result.get("structured_issues") or [])[:30],
        }
        repair = await run_full_brain_repair(
            workspace_path=workspace_path,
            step_key=step["step_key"],
            error_message=json.dumps(error_payload)[:2400],
            retry_count=retry_count + index - 1,
            job=job,
        )
        repaired = repair.get("files_repaired") or []
        if isinstance(repaired, list):
            for rel in repaired:
                if rel not in files_repaired:
                    files_repaired.append(rel)
        workspace_fixed = workspace_fixed or bool(repair.get("workspace_fixed")) or bool(repaired)
        attempts.append(
            {
                "target": step["target"],
                "step_key": step["step_key"],
                "strategy": repair.get("strategy", "unknown"),
                "workspace_fixed": bool(repair.get("workspace_fixed")) or bool(repaired),
                "files_repaired": repaired,
            }
        )

    return {
        "strategy": "targeted_dag_retry",
        "plan": plan,
        "attempts": attempts,
        "workspace_fixed": workspace_fixed,
        "files_repaired": files_repaired,
    }
