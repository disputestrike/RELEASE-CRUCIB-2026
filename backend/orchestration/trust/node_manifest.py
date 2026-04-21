"""
First-class DAG node metadata: runtime, timeouts, expected artifacts, verification classes.
Merged into planner output so plans and UI can show operator truth.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

# Default for unknown steps
_DEFAULT = {
    "runtime": "python",
    "entry": "orchestration.executor.execute_step",
    "expected_artifacts": ["workspace files per handler"],
    "timeout_sec": 600,
    "retry_policy": {"max_retries": 3, "backoff": "linear"},
    "verification_classes": ["presence"],
    "allowed_paths": ["**/*"],
}

_MANIFESTS: Dict[str, Dict[str, Any]] = {
    "planning.analyze": {
        "runtime": "python",
        "entry": "handle_planning_step",
        "expected_artifacts": ["PLAN.md"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence"],
    },
    "planning.requirements": {
        "runtime": "python",
        "entry": "handle_planning_step",
        "expected_artifacts": ["PLAN.md"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence"],
    },
    "frontend.scaffold": {
        "runtime": "python",
        "entry": "handle_frontend_generate",
        "expected_artifacts": ["package.json", "src/App.jsx", "src/pages/*.jsx"],
        "timeout_sec": 300,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax"],
    },
    "frontend.styling": {
        "runtime": "python",
        "entry": "handle_frontend_modify",
        "expected_artifacts": ["src/styles/global.css"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence"],
    },
    "frontend.routing": {
        "runtime": "python",
        "entry": "handle_frontend_modify",
        "expected_artifacts": ["src/pages/TeamPage.jsx", "src/App.jsx"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax"],
    },
    "backend.models": {
        "runtime": "python",
        "entry": "handle_backend_route",
        "expected_artifacts": ["backend/models.py or sketch"],
        "timeout_sec": 180,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax"],
    },
    "backend.routes": {
        "runtime": "python",
        "entry": "handle_backend_route",
        "expected_artifacts": ["backend/main.py"],
        "timeout_sec": 180,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax", "runtime"],
    },
    "backend.auth": {
        "runtime": "python",
        "entry": "handle_backend_route",
        "expected_artifacts": ["backend/main.py"],
        "timeout_sec": 180,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax"],
    },
    "backend.stripe": {
        "runtime": "python",
        "entry": "handle_backend_route",
        "expected_artifacts": ["backend/main.py"],
        "timeout_sec": 240,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "syntax"],
    },
    "database.migration": {
        "runtime": "python",
        "entry": "handle_db_migration",
        "expected_artifacts": ["migrations/*.sql"],
        "timeout_sec": 180,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence", "runtime"],
    },
    "database.seed": {
        "runtime": "python",
        "entry": "handle_db_migration",
        "expected_artifacts": ["seed data files"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence"],
    },
    "verification.compile": {
        "runtime": "python",
        "entry": "verify_compile_workspace",
        "expected_artifacts": ["node --check evidence"],
        "timeout_sec": 300,
        "retry_policy": {"max_retries": 1, "backoff": "none"},
        "verification_classes": ["syntax"],
    },
    "verification.api_smoke": {
        "runtime": "python",
        "entry": "verify_step (api)",
        "expected_artifacts": ["smoke proof rows"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["runtime"],
    },
    "verification.preview": {
        "runtime": "python+node",
        "entry": "verify_preview_workspace + browser_preview_verify (thread-isolated Playwright)",
        "expected_artifacts": [
            "npm ci/build logs",
            "dist/",
            "screenshot PNG",
            "console capture",
        ],
        "timeout_sec": 900,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["runtime", "experience"],
    },
    "verification.security": {
        "runtime": "python",
        "entry": "verify_step (security + optional RLS files + behavior bundle)",
        "expected_artifacts": [
            "security checklist proof",
            "tenancy_smoke / stripe_replay / rbac (merged)",
        ],
        "timeout_sec": 240,
        "retry_policy": {"max_retries": 1, "backoff": "none"},
        "verification_classes": ["runtime"],
    },
    "verification.behavior": {
        "runtime": "python",
        "entry": "verify_behavior_bundle_workspace",
        "expected_artifacts": ["tenancy_smoke", "stripe_replay", "rbac_smoke proofs"],
        "timeout_sec": 180,
        "retry_policy": {"max_retries": 1, "backoff": "linear"},
        "verification_classes": ["runtime"],
    },
    "verification.rls": {
        "runtime": "python",
        "entry": "verify_rls_workspace",
        "expected_artifacts": ["RLS migration structural proof"],
        "timeout_sec": 60,
        "retry_policy": {"max_retries": 1, "backoff": "none"},
        "verification_classes": ["syntax", "runtime"],
    },
    "verification.tenancy_smoke": {
        "runtime": "python+postgres",
        "entry": "verify_tenancy_smoke_workspace",
        "expected_artifacts": ["two-tenant isolation proof"],
        "timeout_sec": 120,
        "retry_policy": {"max_retries": 1, "backoff": "linear"},
        "verification_classes": ["runtime"],
    },
    "verification.stripe_replay": {
        "runtime": "python",
        "entry": "verify_stripe_replay_workspace",
        "expected_artifacts": ["idempotent insert proof"],
        "timeout_sec": 30,
        "retry_policy": {"max_retries": 1, "backoff": "none"},
        "verification_classes": ["runtime"],
    },
    "verification.rbac_enforcement": {
        "runtime": "python",
        "entry": "verify_rbac_enforcement_workspace",
        "expected_artifacts": ["optional admin-route HTTP proof"],
        "timeout_sec": 60,
        "retry_policy": {"max_retries": 1, "backoff": "none"},
        "verification_classes": ["runtime"],
    },
    "deploy.build": {
        "runtime": "shell",
        "entry": "handle_deploy",
        "expected_artifacts": [
            "Dockerfile",
            "deploy/PRODUCTION_SKETCH.md",
            "deploy/healthcheck.sh",
            "docs/COMPLIANCE_SKETCH.md (when goal is compliance-sensitive)",
            "deploy/observability/* (when goal mentions OTel/Prometheus/Grafana/metrics)",
            "terraform/multiregion_sketch (when goal matches multi-region + cloud/Terraform)",
        ],
        "timeout_sec": 600,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["presence"],
    },
    "deploy.publish": {
        "runtime": "shell",
        "entry": "handle_deploy",
        "expected_artifacts": ["live URL when configured"],
        "timeout_sec": 600,
        "retry_policy": {"max_retries": 2, "backoff": "linear"},
        "verification_classes": ["runtime", "experience"],
    },
}


def manifest_for_step_key(step_key: str) -> Dict[str, Any]:
    if step_key in _MANIFESTS:
        return copy.deepcopy(_MANIFESTS[step_key])
    phase = step_key.split(".")[0] if "." in step_key else ""
    out = copy.deepcopy(_DEFAULT)
    out["step_key"] = step_key
    out["phase"] = phase
    out["note"] = "Generic manifest — extend trust/node_manifest.py for full metadata."
    return out


def enrich_plan_with_node_manifests(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Mutates and returns plan with each step containing node_manifest."""
    plan = copy.deepcopy(plan)
    for phase in plan.get("phases") or []:
        for step in phase.get("steps") or []:
            key = step.get("key") or ""
            step["node_manifest"] = manifest_for_step_key(key)
    return plan
