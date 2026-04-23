"""
workspace_reader.py — Reads the actual workspace files to diagnose failures.

This is what I do manually: read App.jsx line 1, check package.json,
scan server.py imports, look at the proof bundle. The brain needs to
do the same thing before deciding how to fix a failure.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── File reading ───────────────────────────────────────────────────────────────

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

CODE_EXTENSIONS = {
    ".jsx",
    ".tsx",
    ".js",
    ".ts",
    ".py",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".sh",
    ".sql",
}


def read_workspace_file(workspace_path: str, rel_path: str) -> Optional[str]:
    """Read a file from the workspace safely."""
    if not workspace_path:
        return None
    full = os.path.normpath(os.path.join(workspace_path, rel_path))
    # Safety: no path escapes
    if not full.startswith(os.path.normpath(workspace_path)):
        return None
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def list_workspace_files(workspace_path: str) -> List[str]:
    """List all source files in workspace."""
    files = []
    if not workspace_path or not os.path.isdir(workspace_path):
        return files
    skip = {"node_modules", ".git", "__pycache__", "dist", "build", ".next"}
    for root, dirs, filenames in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in filenames:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace_path).replace("\\", "/")
            files.append(rel)
    return files


def detect_prose_in_file(content: str) -> Optional[str]:
    """Return the prose line if file starts with prose, else None."""
    if not content:
        return None
    first_line = content.strip().split("\n")[0].strip().lower()
    if any(first_line.startswith(p) for p in PROSE_PREFIXES):
        return content.strip().split("\n")[0][:120]
    return None


def check_jsx_syntax(content: str) -> List[str]:
    """Basic JSX sanity checks without running a compiler."""
    issues = []
    if not content or not content.strip():
        issues.append("File is empty")
        return issues

    # Prose preamble
    prose = detect_prose_in_file(content)
    if prose:
        issues.append(f"File starts with prose: {prose!r}")

    # Check for obvious unclosed brackets (rough heuristic)
    opens = content.count("{")
    closes = content.count("}")
    if abs(opens - closes) > 10:
        issues.append(f"Bracket mismatch: {opens} open vs {closes} close")

    # Check for import statements (good sign)
    has_import = bool(re.search(r"^import\s", content, re.MULTILINE))
    has_export = bool(re.search(r"^export\s", content, re.MULTILINE))
    if not has_import and not has_export:
        issues.append("No import or export statements found")

    return issues


def check_python_syntax(content: str) -> List[str]:
    """Python syntax check using compile()."""
    issues = []
    if not content or not content.strip():
        issues.append("File is empty")
        return issues

    prose = detect_prose_in_file(content)
    if prose:
        issues.append(f"File starts with prose: {prose!r}")
        return issues

    try:
        compile(content, "<string>", "exec")
    except SyntaxError as e:
        issues.append(f"SyntaxError at line {e.lineno}: {e.msg}")
    return issues


# ── Root cause graph ───────────────────────────────────────────────────────────

# Maps failure step → ordered list of (file, check_fn, fix_hint)
ROOT_CAUSE_GRAPH = {
    "verification.preview": [
        ("src/App.jsx", "jsx_syntax", "regenerate_frontend"),
        ("src/main.jsx", "jsx_syntax", "regenerate_entry_point"),
        ("package.json", "json_valid", "regenerate_package_json"),
        ("vite.config.js", "text_exists", "fix_vite_config"),
        ("src/App.tsx", "jsx_syntax", "regenerate_frontend"),
    ],
    "verification.compile": [
        ("src/App.jsx", "jsx_syntax", "regenerate_frontend"),
        ("server.py", "python_syntax", "regenerate_backend"),
        ("src/main.jsx", "jsx_syntax", "regenerate_entry_point"),
        ("vite.config.js", "text_exists", "fix_vite_config"),
    ],
    "verification.security": [
        ("server.py", "python_syntax", "regenerate_backend"),
        ("server.py", "hardcoded_secrets", "fix_secrets"),
    ],
    "agents.database_agent": [
        ("schema.sql", "text_exists", "regenerate_schema"),
        ("server.py", "python_syntax", "check_backend"),
    ],
    "agents.frontend_generation": [
        ("src/App.jsx", "jsx_syntax", "regenerate_frontend"),
        ("src/main.jsx", "text_exists", "regenerate_entry_point"),
    ],
    "agents.backend_generation": [
        ("server.py", "python_syntax", "regenerate_backend"),
        ("requirements.txt", "text_exists", "regenerate_requirements"),
    ],
}


def _check_file(
    workspace_path: str, rel_path: str, check_type: str
) -> Tuple[bool, List[str]]:
    """Run a specific check on a file. Returns (passed, issues)."""
    content = read_workspace_file(workspace_path, rel_path)

    if check_type == "text_exists":
        if not content or not content.strip():
            return False, [f"{rel_path} is missing or empty"]
        return True, []

    if check_type == "json_valid":
        if not content:
            return False, [f"{rel_path} missing"]
        try:
            json.loads(content)
            return True, []
        except json.JSONDecodeError as e:
            return False, [f"{rel_path} invalid JSON: {e}"]

    if check_type == "jsx_syntax":
        if not content:
            return False, [f"{rel_path} missing"]
        issues = check_jsx_syntax(content)
        return len(issues) == 0, issues

    if check_type == "python_syntax":
        if not content:
            return False, [f"{rel_path} missing"]
        issues = check_python_syntax(content)
        return len(issues) == 0, issues

    if check_type == "hardcoded_secrets":
        if not content:
            return True, []
        patterns = [
            r'secret\s*=\s*["\'][^"\']{8,}',
            r'password\s*=\s*["\'][^"\']{8,}',
            r'api_key\s*=\s*["\'][^"\']{8,}',
        ]
        for p in patterns:
            if re.search(p, content, re.IGNORECASE):
                return False, [f"{rel_path} may contain hardcoded secret"]
        return True, []

    return True, []


# ── Full workspace diagnosis ───────────────────────────────────────────────────


def diagnose_workspace(
    workspace_path: str,
    failed_step_key: str = "",
    error_message: str = "",
    proof_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full workspace diagnostic. This is what I do manually.

    Reads actual files, checks syntax, cross-references the proof bundle,
    and returns a structured diagnosis with the exact root cause and fix.
    """
    findings: List[Dict[str, Any]] = []
    root_cause = None
    recommended_fix = None
    affected_files: List[str] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        return {
            "workspace_readable": False,
            "findings": [
                {"issue": "Workspace path not accessible", "severity": "critical"}
            ],
            "root_cause": "workspace_missing",
            "recommended_fix": "trigger_redeploy",
            "affected_files": [],
        }

    # 1. Run root cause graph checks for this step
    checks = ROOT_CAUSE_GRAPH.get(failed_step_key, [])
    # Also run generic checks if step key has a prefix match
    for key, check_list in ROOT_CAUSE_GRAPH.items():
        if (
            failed_step_key.startswith(key.split(".")[0] + ".")
            and key != failed_step_key
        ):
            checks = checks + check_list

    for rel_path, check_type, fix_hint in checks:
        passed, issues = _check_file(workspace_path, rel_path, check_type)
        if not passed:
            content = read_workspace_file(workspace_path, rel_path)
            first_line = ""
            if content:
                first_line = content.strip().split("\n")[0][:120]
            finding = {
                "file": rel_path,
                "check": check_type,
                "issues": issues,
                "first_line": first_line,
                "severity": "critical",
                "fix_hint": fix_hint,
            }
            findings.append(finding)
            affected_files.append(rel_path)
            if root_cause is None:
                root_cause = fix_hint
                recommended_fix = fix_hint

    # 2. Scan ALL code files for prose preamble (the #1 recurring issue)
    # Prose overrides other root causes — it's almost always the real problem
    prose_found = False
    all_files = list_workspace_files(workspace_path)
    for rel in all_files:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in CODE_EXTENSIONS:
            continue
        if "node_modules" in rel or "dist/" in rel or "build/" in rel:
            continue
        content = read_workspace_file(workspace_path, rel)
        if not content:
            continue
        prose = detect_prose_in_file(content)
        if prose:
            findings.append(
                {
                    "file": rel,
                    "check": "prose_preamble",
                    "issues": [f"File starts with prose: {prose!r}"],
                    "first_line": prose,
                    "severity": "critical",
                    "fix_hint": "strip_prose_and_regenerate",
                }
            )
            if rel not in affected_files:
                affected_files.append(rel)
            prose_found = True
    # Prose overrides earlier root_cause — it's the #1 issue
    if prose_found:
        root_cause = "prose_in_code"
        recommended_fix = "strip_prose_and_regenerate"

    # 3. Check proof bundle for systemic issues
    if proof_bundle:
        trust = proof_bundle.get("trust_score", -1)
        if trust == 0:
            findings.append(
                {
                    "file": "proof_bundle",
                    "check": "trust_score",
                    "issues": ["Trust score is 0 — no runtime verification passed"],
                    "severity": "high",
                    "fix_hint": "fix_verification_depth",
                }
            )
        output_previews = [
            item
            for item in (proof_bundle.get("bundle", {}).get("generic") or [])
            if (item.get("payload") or {}).get("output_preview") in (None, "None", "")
        ]
        if len(output_previews) > 10:
            findings.append(
                {
                    "file": "proof_bundle",
                    "check": "output_preview_none",
                    "issues": [
                        f"{len(output_previews)} agents produced no output preview"
                    ],
                    "severity": "medium",
                    "fix_hint": "fix_output_capture",
                }
            )

    # 4. Check package.json for required deps
    pkg_content = read_workspace_file(workspace_path, "package.json")
    if pkg_content:
        try:
            pkg = json.loads(pkg_content)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            required = {"react", "react-dom"}
            missing = required - set(deps.keys())
            if missing:
                findings.append(
                    {
                        "file": "package.json",
                        "check": "required_deps",
                        "issues": [f"Missing required deps: {', '.join(missing)}"],
                        "severity": "critical",
                        "fix_hint": "regenerate_package_json",
                    }
                )
                if root_cause is None:
                    root_cause = "missing_dependencies"
                    recommended_fix = "regenerate_package_json"
        except json.JSONDecodeError:
            findings.append(
                {
                    "file": "package.json",
                    "check": "json_valid",
                    "issues": ["package.json is not valid JSON"],
                    "severity": "critical",
                    "fix_hint": "regenerate_package_json",
                }
            )

    # 5. Parse error_message for specific file/line info
    file_match = re.search(r"([\w/.-]+\.(jsx?|tsx?|py|sql)):(\d+)", error_message or "")
    if file_match:
        err_file = file_match.group(1)
        err_line = int(file_match.group(3))
        content = read_workspace_file(workspace_path, err_file)
        if content:
            lines = content.split("\n")
            if 0 < err_line <= len(lines):
                err_line_content = lines[err_line - 1]
                findings.append(
                    {
                        "file": err_file,
                        "check": "error_location",
                        "issues": [
                            f"Error at line {err_line}: {err_line_content[:120]}"
                        ],
                        "line": err_line,
                        "line_content": err_line_content,
                        "severity": "critical",
                        "fix_hint": "fix_at_error_location",
                    }
                )
                if err_file not in affected_files:
                    affected_files.append(err_file)

    critical_findings = [f for f in findings if f.get("severity") == "critical"]
    logger.info(
        "workspace_reader.diagnose: step=%s files=%d findings=%d critical=%d "
        "root_cause=%s fix=%s",
        failed_step_key,
        len(all_files),
        len(findings),
        len(critical_findings),
        root_cause,
        recommended_fix,
    )

    return {
        "workspace_readable": True,
        "workspace_file_count": len(all_files),
        "findings": findings,
        "critical_findings": critical_findings,
        "root_cause": root_cause or "unknown",
        "recommended_fix": recommended_fix or "conservative_retry",
        "affected_files": affected_files,
        "has_app_jsx": any("App.jsx" in f or "App.tsx" in f for f in all_files),
        "has_server_py": "server.py" in all_files,
        "has_package_json": "package.json" in all_files,
    }
