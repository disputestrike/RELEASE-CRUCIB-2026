"""
diagnostic_agent.py — Smart failure diagnosis brain.

Reads the actual error output, classifies the root cause with precision,
and returns a structured repair plan. Used by the fixer before every retry
so retries are targeted — not blind generic patches.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Failure classification ────────────────────────────────────────────────────

FAILURE_CLASSES = {
    "prose_in_code": {
        "description": "LLM wrote conversational text into a source file",
        "patterns": [
            r"expected\s*[\"']?;[\"']?\s*but found\s*[\"']?\w+[\"']?",
            r"found ['\"]appreciate['\"]",
            r"found ['\"]certainly['\"]",
            r"found ['\"]here['\"]",
            r"found ['\"]i ['\"]",
            r"found ['\"]the ['\"]",
            r"found ['\"]this ['\"]",
            r"Transform failed.*Expected.*found",
        ],
        "fix_strategy": "strip_prose_and_regenerate_frontend",
        "target_files": ["src/App.jsx", "src/App.tsx", "src/main.jsx"],
        "severity": "critical",
    },
    "jsx_syntax_error": {
        "description": "JSX/TSX syntax error in source file",
        "patterns": [
            r"vite.*esbuild.*Transform failed",
            r"SyntaxError.*jsx",
            r"Unexpected token.*<",
            r"Expected.*jsx",
            r"npm run build failed",
            r"vite build.*error",
        ],
        "fix_strategy": "regenerate_frontend_clean",
        "target_files": ["src/App.jsx"],
        "severity": "critical",
    },
    "missing_import": {
        "description": "Import references a module that doesn't exist",
        "patterns": [
            r"Cannot find module",
            r"Module not found",
            r"Failed to resolve import",
            r"does not provide an export named",
        ],
        "fix_strategy": "fix_imports",
        "target_files": [],
        "severity": "high",
    },
    "python_syntax": {
        "description": "Python syntax error in backend file",
        "patterns": [
            r"SyntaxError.*\.py",
            r"IndentationError",
            r"invalid syntax",
            r"py_compile.*failed",
        ],
        "fix_strategy": "regenerate_backend_clean",
        "target_files": ["server.py", "main.py"],
        "severity": "critical",
    },
    "missing_package_json": {
        "description": "package.json missing or malformed",
        "patterns": [
            r"missing_package_json",
            r"package\.json.*not found",
            r"ENOENT.*package\.json",
            r"invalid.*package\.json",
        ],
        "fix_strategy": "regenerate_package_json",
        "target_files": ["package.json"],
        "severity": "critical",
    },
    "no_entry_point": {
        "description": "No React entry point found",
        "patterns": [
            r"no_entry_point",
            r"index\.jsx.*not found",
            r"index\.js.*not found",
            r"No entry.*ReactDOM",
        ],
        "fix_strategy": "regenerate_entry_point",
        "target_files": ["src/main.jsx", "src/index.js"],
        "severity": "critical",
    },
    "db_migration": {
        "description": "Database migration or table missing",
        "patterns": [
            r"relation.*does not exist",
            r"table.*not found",
            r"migration.*failed",
            r"column.*does not exist",
        ],
        "fix_strategy": "fix_db_migration",
        "target_files": ["schema.sql"],
        "severity": "high",
    },
    "railway_network": {
        "description": "Railway infrastructure network timeout",
        "patterns": [
            r"DEADLINE_EXCEEDED",
            r"i/o timeout",
            r"dial tcp.*timeout",
            r"registry.*timeout",
        ],
        "fix_strategy": "trigger_redeploy",
        "target_files": [],
        "severity": "infra",
    },
    "security_static": {
        "description": "Security scan found issues",
        "patterns": [
            r"hardcoded.*secret",
            r"sql injection",
            r"xss.*vulnerability",
            r"missing.*csrf",
            r"cors.*wildcard",
        ],
        "fix_strategy": "apply_security_patches",
        "target_files": ["server.py"],
        "severity": "high",
    },
    "unknown": {
        "description": "Unclassified failure",
        "patterns": [],
        "fix_strategy": "conservative_patch",
        "target_files": [],
        "severity": "unknown",
    },
}


def diagnose(
    step: Dict[str, Any],
    verification_result: Optional[Dict[str, Any]] = None,
    error_log: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Primary diagnostic function. Reads step data + error log and returns
    a structured diagnosis with classified failure type, fix strategy,
    target files, and a human-readable explanation.
    """
    verification_result = verification_result or {}
    issues = verification_result.get("issues", [])
    error_message = step.get("error_message", "") or ""
    failure_reason = verification_result.get("failure_reason", "") or ""

    # Build a single string from all available error context
    all_context = " ".join(
        [
            error_message,
            failure_reason,
            error_log or "",
            " ".join(str(i) for i in issues),
        ]
    ).lower()

    # Run through classifiers in priority order
    failure_class = "unknown"
    for class_name, class_def in FAILURE_CLASSES.items():
        if class_name == "unknown":
            continue
        for pattern in class_def["patterns"]:
            if re.search(pattern, all_context, re.IGNORECASE):
                failure_class = class_name
                break
        if failure_class != "unknown":
            break

    class_def = FAILURE_CLASSES[failure_class]
    retry_count = step.get("retry_count", 0)
    max_retries = step.get("max_retries", 8)

    # Extract specific file and line info if available
    file_match = re.search(r"([/\w.-]+\.(jsx?|tsx?|py|sql)):(\d+)", all_context)
    specific_file = file_match.group(1) if file_match else None
    specific_line = int(file_match.group(3)) if file_match else None

    diagnosis = {
        "failure_class": failure_class,
        "description": class_def["description"],
        "fix_strategy": class_def["fix_strategy"],
        "target_files": class_def["target_files"]
        + ([specific_file] if specific_file else []),
        "severity": class_def["severity"],
        "specific_file": specific_file,
        "specific_line": specific_line,
        "retry_count": retry_count,
        "can_retry": retry_count < max_retries,
        "retry_number": retry_count + 1,
        "raw_error_snippet": all_context[:500],
        "issues": issues,
        "step_key": step.get("step_key", "unknown"),
        "explanation": _build_explanation(
            failure_class, specific_file, specific_line, issues
        ),
        "repair_actions": _build_repair_actions(failure_class, specific_file, issues),
    }

    logger.info(
        "diagnostic_agent: step=%s class=%s strategy=%s severity=%s retry=%d/%d",
        step.get("step_key"),
        failure_class,
        class_def["fix_strategy"],
        class_def["severity"],
        retry_count,
        max_retries,
    )

    return diagnosis


def _build_explanation(
    failure_class: str,
    specific_file: Optional[str],
    specific_line: Optional[int],
    issues: List[str],
) -> str:
    base = FAILURE_CLASSES[failure_class]["description"]
    if specific_file and specific_line:
        return f"{base} — detected in {specific_file} at line {specific_line}."
    if specific_file:
        return f"{base} — detected in {specific_file}."
    if issues:
        return f"{base}: {issues[0][:200]}"
    return base


def _build_repair_actions(
    failure_class: str,
    specific_file: Optional[str],
    issues: List[str],
) -> List[str]:
    strategies = {
        "strip_prose_and_regenerate_frontend": [
            f"Strip all prose/conversational lines from top of {specific_file or 'src/App.jsx'}",
            "Re-run Frontend Generation agent with enforced code-only output",
            "Validate JSX syntax before writing to disk",
            "Re-run vite build verification",
        ],
        "regenerate_frontend_clean": [
            "Delete corrupted src/App.jsx",
            "Re-run Frontend Generation with strict code-only prompt",
            "Verify output starts with valid JSX (import/export/function)",
            "Run vite build to confirm",
        ],
        "fix_imports": [
            f"Scan {specific_file or 'all JSX files'} for broken import paths",
            "Check that all imported modules exist in package.json",
            "Fix relative path references",
            "Re-run compile verification",
        ],
        "regenerate_backend_clean": [
            "Delete corrupted server.py",
            "Re-run Backend Generation agent with strict Python-only output",
            "Validate Python syntax with py_compile",
            "Re-run API smoke test",
        ],
        "regenerate_package_json": [
            "Re-generate package.json with correct react/react-dom/vite dependencies",
            "Ensure build script is 'vite build'",
            "Run npm install",
        ],
        "regenerate_entry_point": [
            "Re-generate src/main.jsx with ReactDOM.createRoot pattern",
            "Ensure it imports App from './App.jsx'",
        ],
        "fix_db_migration": [
            "Check schema.sql for missing table definitions",
            "Add IF NOT EXISTS guards to all CREATE TABLE statements",
            "Re-run database migration",
        ],
        "trigger_redeploy": [
            "Railway registry timeout — infrastructure issue not code issue",
            "Wait 60 seconds and retry deployment",
            "No code changes needed",
        ],
        "apply_security_patches": [
            "Scan server.py for hardcoded secrets → replace with os.environ.get()",
            "Add CORS middleware with explicit allowed origins",
            "Add CSRF token middleware",
            "Re-run security verification",
        ],
        "conservative_patch": [
            f"Inspect full error: {issues[0][:200] if issues else 'no details'}",
            "Narrow scope to failing component",
            "Apply minimal patch and re-verify",
        ],
    }

    strategy = FAILURE_CLASSES[failure_class]["fix_strategy"]
    return strategies.get(strategy, strategies["conservative_patch"])


def diagnose_from_proof_bundle(proof_bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyse a full proof bundle and return a list of diagnoses
    for all failed/blocked steps.
    """
    diagnoses = []
    build_contract = proof_bundle.get("build_contract", {})
    blockers = build_contract.get("blockers", [])

    # Synthesize a fake step from proof bundle data
    if "missing_file_evidence" in blockers:
        diagnoses.append(
            {
                "failure_class": "missing_file_evidence",
                "description": "No file evidence in proof — agents ran but wrote nothing verifiable",
                "fix_strategy": "fix_output_capture",
                "repair_actions": [
                    "Ensure agent output is captured in proof bundle",
                    "Check that output_preview is populated from step output not output_ref",
                ],
                "severity": "high",
            }
        )

    trust = proof_bundle.get("trust_score", 0)
    if trust == 0:
        diagnoses.append(
            {
                "failure_class": "zero_trust_score",
                "description": "Trust score is 0 — no runtime or experience verification passed",
                "fix_strategy": "fix_verification_depth",
                "repair_actions": [
                    "Ensure at least one runtime check passes (not just presence)",
                    "Wire preview visual evidence",
                    "Fix experience-class verification",
                ],
                "severity": "critical",
            }
        )

    return diagnoses
