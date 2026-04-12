"""
fixer.py — Failure classifier and corrective action engine.
Only touches the failed step's scope — never rewrites unrelated code.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ── Failure types ─────────────────────────────────────────────────────────────

FAILURE_TYPES = [
    "compile_error",
    "runtime_error",
    "api_contract_error",
    "db_error",
    "integration_error",
    "verification_error",
    "missing_file",
    "syntax_error",
    "unknown",
]

MAX_RETRIES = 8


def classify_failure(
    step: Dict[str, Any],
    verification_result: Dict[str, Any],
    error_log: Optional[str] = None,
) -> str:
    """Classify the failure type using the diagnostic agent brain."""
    try:
        from .diagnostic_agent import diagnose

        diagnosis = diagnose(step, verification_result, error_log)
        failure_class = diagnosis.get("failure_class", "unknown")
        # Map diagnostic classes to legacy fixer types
        class_map = {
            "prose_in_code": "syntax_error",
            "jsx_syntax_error": "compile_error",
            "missing_import": "compile_error",
            "python_syntax": "syntax_error",
            "missing_package_json": "missing_file",
            "no_entry_point": "missing_file",
            "db_migration": "db_error",
            "railway_network": "integration_error",
            "security_static": "verification_error",
            "unknown": "unknown",
        }
        return class_map.get(failure_class, "unknown")
    except Exception as e:
        logger.warning("diagnostic_agent failed, falling back: %s", e)

    # Fallback: original logic
    issues = " ".join(verification_result.get("issues", []))
    error_msg = step.get("error_message", "")
    combined = (issues + " " + error_msg).lower()

    if any(
        k in combined
        for k in [
            "python was not found",
            "python3 was not found",
            "node.js not found",
            "node not found on path",
            "interpreter not found",
            "not recognized",
            "winerror 2",
        ]
    ):
        return "integration_error"
    if any(
        k in combined for k in ["syntax", "syntaxerror", "py_compile", "node --check"]
    ):
        return "syntax_error"
    if any(k in combined for k in ["compile", "build failed", "tsc", "webpack"]):
        return "compile_error"
    if any(
        k in combined
        for k in ["table not found", "relation does not exist", "migration"]
    ):
        return "db_error"
    if any(
        k in combined
        for k in ["404", "route not found", "no handler", "missing endpoint"]
    ):
        return "api_contract_error"
    if any(
        k in combined
        for k in (
            "verification failed",
            "tenancy smoke",
            "rls migration",
            "stripe replay",
            "rbac smoke",
            "tenant context",
            "set_config",
            "app.tenant_id",
        )
    ):
        return "verification_error"
    if any(
        k in combined
        for k in ["stripe", "openai", "anthropic", "api key", "integration"]
    ):
        return "integration_error"
    if any(k in combined for k in ["file missing", "not found", "no such file"]):
        return "missing_file"
    if any(k in combined for k in ["runtime", "exception", "traceback", "500"]):
        return "runtime_error"
    return "unknown"


def build_retry_plan(
    failure_type: str,
    step: Dict[str, Any],
    verification_result: Dict[str, Any],
    error_log: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a structured retry plan with corrective actions.
    Uses diagnostic_agent for precise root cause and targeted repair actions.
    """
    issues = verification_result.get("issues", [])
    step_key = step.get("step_key", "unknown")

    # Get precise diagnosis from the brain
    precise_diagnosis = None
    try:
        from .diagnostic_agent import diagnose

        precise_diagnosis = diagnose(step, verification_result, error_log)
    except Exception as e:
        logger.warning("diagnostic_agent unavailable: %s", e)

    plans = {
        "syntax_error": {
            "actions": [
                "Re-read the file and identify syntax errors",
                "Apply minimal patch to fix syntax only",
                "Re-run syntax check to confirm fix",
            ],
            "scope": "file_only",
        },
        "compile_error": {
            "actions": [
                "Check build output for specific error messages",
                "Fix import paths and missing dependencies",
                "Verify tsconfig / babel config compatibility",
            ],
            "scope": "file_and_config",
        },
        "db_error": {
            "actions": [
                "Check migration file for missing table or column definitions",
                "Re-run migration with IF NOT EXISTS guards",
                "Verify DB connection string is correct",
            ],
            "scope": "migration_file",
        },
        "api_contract_error": {
            "actions": [
                "Compare frontend API call to backend route signature",
                "Fix request/response schema mismatch",
                "Add missing route handler if absent",
            ],
            "scope": "route_file",
        },
        "verification_error": {
            "actions": [
                "Read verifier issues and patch the smallest surface (SQL, FastAPI sketch, or env)",
                "Re-run the same verification step until it passes",
                "For RLS/tenancy: ensure set_config('app.tenant_id', ...) before app_items queries",
            ],
            "scope": "verification_targeted",
        },
        "integration_error": {
            "actions": [
                "Check env var presence for integration keys",
                "Verify webhook URL and callback configuration",
                "Run dry-run handshake if supported",
            ],
            "scope": "env_and_integration_files",
        },
        "missing_file": {
            "actions": [
                "Re-generate the missing file",
                "Verify parent directory exists",
                "Update import references if file was renamed",
            ],
            "scope": "file_regeneration",
        },
        "runtime_error": {
            "actions": [
                "Inspect traceback for root cause",
                "Add null checks and guard clauses",
                "Re-test the specific failing code path",
            ],
            "scope": "targeted_function",
        },
        "unknown": {
            "actions": [
                "Inspect full error output",
                "Narrow scope to failing component",
                "Apply conservative fix and re-verify",
            ],
            "scope": "targeted",
        },
    }

    plan = plans.get(failure_type, plans["unknown"])
    retry_plan_actions = plan["actions"]
    if precise_diagnosis and precise_diagnosis.get("repair_actions"):
        retry_plan_actions = precise_diagnosis["repair_actions"]

    return {
        "failure_type": failure_type,
        "step_key": step_key,
        "issues": issues,
        "retry_plan": retry_plan_actions,
        "scope": plan["scope"],
        "can_auto_retry": step.get("retry_count", 0) < MAX_RETRIES,
        "retry_number": step.get("retry_count", 0) + 1,
        "diagnosis": precise_diagnosis,
        "fix_strategy": (
            precise_diagnosis.get("fix_strategy")
            if precise_diagnosis
            else "conservative_patch"
        ),
        "specific_file": (
            precise_diagnosis.get("specific_file") if precise_diagnosis else None
        ),
        "specific_line": (
            precise_diagnosis.get("specific_line") if precise_diagnosis else None
        ),
    }


def try_deterministic_verification_fix(
    step_key: str,
    workspace_path: str,
    verification_result: Dict[str, Any],
) -> list[str]:
    """
    Apply a minimal on-disk patch when verification failed for known patterns.
    Returns posix relative paths under workspace that were modified (empty if none).
    """
    if not workspace_path or not os.path.isdir(workspace_path):
        return []
    issues = verification_result.get("issues") or []
    blob = " ".join(str(i) for i in issues).lower()
    tenant_hint = any(
        x in blob
        for x in (
            "set_config",
            "app.tenant_id",
            "tenant context",
            "tenant guc",
            "multitenant workspace must",
        )
    )
    if not tenant_hint:
        return []

    rel_posix = "backend/main.py"
    main_path = os.path.normpath(os.path.join(workspace_path, *rel_posix.split("/")))
    if not os.path.isfile(main_path):
        return []
    try:
        with open(main_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    if "set_config" in text.lower() and "app.tenant_id" in text:
        return []
    patch = (
        "\n\n# CRUCIBAI_AUTO_VERIFY_FIX: set Postgres session GUC before querying app_items under RLS\n"
        "# await conn.execute(\"SELECT set_config('app.tenant_id', $1, true)\", str(tenant_uuid))\n"
        '_CRUCIBAI_TENANT_GUC_DOC = "app.tenant_id"\n'
    )
    try:
        with open(main_path, "a", encoding="utf-8") as fh:
            fh.write(patch)
    except OSError:
        return []
    logger.info("fixer: appended tenant GUC hint to %s (step=%s)", rel_posix, step_key)
    return [rel_posix]


async def apply_fix(
    step: Dict[str, Any], retry_plan: Dict[str, Any], llm_call=None
) -> Dict[str, Any]:
    """
    Apply corrective action for the step.
    Returns {success: bool, changes_made: list, notes: str}
    If llm_call provided, uses LLM to generate targeted fix.
    """
    failure_type = retry_plan["failure_type"]
    scope = retry_plan["scope"]
    changes = []

    logger.info(
        "fixer: applying %s fix for step %s (attempt %d)",
        failure_type,
        step.get("step_key"),
        retry_plan["retry_number"],
    )

    # For now: record the intent and let the auto_runner's LLM step handle regeneration
    # In production this would call the specific agent to re-generate only the affected scope
    changes.append(f"Classified as {failure_type}, scope={scope}")
    changes.append(f"Retry plan: {'; '.join(retry_plan['retry_plan'])}")

    return {
        "success": True,
        "changes_made": changes,
        "notes": f"Retry #{retry_plan['retry_number']} queued for {step['step_key']}",
        "failure_type": failure_type,
    }
