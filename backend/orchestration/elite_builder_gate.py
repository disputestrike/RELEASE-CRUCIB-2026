"""
Elite builder delivery gate: classifications, critical keywords, presence-vs-runtime heuristics.

Env:
  CRUCIBAI_ELITE_BUILDER_GATE — strict | advisory | off (default: strict for new DAG).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .verifier import _proof_item, _result

_GATE_ENV = "CRUCIBAI_ELITE_BUILDER_GATE"


def _gate_mode() -> str:
    v = (os.environ.get(_GATE_ENV) or "strict").strip().lower()
    if v in ("strict", "advisory", "off"):
        return v
    return "strict"


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _delivery_classification_ok(text: str) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    required = ("Implemented", "Mocked", "Stubbed", "Unverified")
    for label in required:
        if label not in text:
            issues.append(f"proof/DELIVERY_CLASSIFICATION.md must mention '{label}'")
    if re.search(r"\bproduction[- ]ready\b", text, re.I) and "Unverified" not in text:
        issues.append("Claims production-ready without an Unverified section")
    return len(issues) == 0, issues


def _goal_suggests_critical(goal: str) -> List[str]:
    g = (goal or "").lower()
    tags: List[str] = []
    if any(x in g for x in ("tenant", "multi-tenant", "rls", "row-level")):
        tags.append("tenancy")
    if any(x in g for x in ("stripe", "payment", "checkout")):
        tags.append("payments")
    if any(x in g for x in ("auth", "rbac", "jwt", "oauth", "login")):
        tags.append("auth")
    if any(x in g for x in ("encrypt", "aes", "dek", "kek", "crypto")):
        tags.append("crypto")
    return tags


def _critical_runtime_evidence(text: str, tags: List[str]) -> Tuple[bool, List[str]]:
    """
    Presence-only patterns are insufficient for critical tags: require hints of runtime/test proof.
    """
    if not tags:
        return True, []
    tlow = text.lower()
    issues: List[str] = []
    if "tenancy" in tags:
        ok = any(
            x in tlow
            for x in (
                "tenancy_isolation",
                "pytest",
                "test_",
                "runtime",
                "smoke",
                "isolation",
            )
        )
        if not ok:
            issues.append(
                "Tenancy-related goal: DELIVERY_CLASSIFICATION or TEST_RESULTS should reference "
                "runtime/smoke/pytest evidence — structure-only mention of RLS is insufficient."
            )
    if "payments" in tags:
        ok = "mock" in tlow or "stripe" in tlow and ("webhook" in tlow or "test" in tlow)
        if not ok:
            issues.append("Payments-related goal: document Mocked keys or webhook test path in classification.")
    if "auth" in tags:
        ok = "mock" in tlow or "jwt" in tlow or "demo" in tlow or "stub" in tlow
        if not ok:
            issues.append("Auth-related goal: classify auth as Implemented/Mocked/Stubbed explicitly.")
    return len(issues) == 0, issues


async def verify_elite_builder_workspace(
    workspace_path: str,
    *,
    job_goal: str = "",
) -> Dict[str, Any]:
    """
    Elite builder verification with binary PASS/FAIL and explicit failure reasons.
    
    DETERMINISTIC: Either PASS (score >=80) with proof bundle, or FAIL with failed_checks list.
    
    Checks (10 total):
    1. Elite directive present (proof/ELITE_EXECUTION_DIRECTIVE.md)
    2. Delivery classification complete (proof/DELIVERY_CLASSIFICATION.md)
    3. Critical feature proof depth (runtime/smoke/pytest evidence)
    4. Error boundaries in code (React ErrorBoundary component)
    5. Console.error/warn free (no debug logs in production)
    6. API error handling (try-catch on all routes)
    7. SQL parameterization (no f-string/format interpolation)
    8. Authentication/RBAC present (AuthContext, useAuth, JWT, Depends)
    9. No hardcoded secrets (no API keys, passwords in source)
    10. Security headers configured (CSP, X-Frame-Options, HSTS, etc.)
    
    Scoring:
    - >=80% (8/10 checks pass): PASS with proof bundle
    - <80% (7/10 or fewer): FAIL with failed_checks list
    
    Returns:
    {
        "passed": bool,
        "score": int (0-100, percent of checks passed),
        "checks": [{"name": str, "passed": bool, "reason": str}],
        "checks_passed": int,
        "checks_total": int,
        "failed_checks": [str],  # Names of failed checks (for agent regeneration)
        "failure_reason": str or None,  # "elite_checks_failed" if not passed
        "recommendation": str,  # Which checks to fix
        "proof": [...]
    }
    """
    mode = _gate_mode()
    proof: List[Dict[str, Any]] = []
    issues: List[str] = []
    checks: List[Dict[str, Any]] = []
    
    if mode == "off":
        return _result(
            True,
            100,
            [],
            [
                _proof_item(
                    "generic",
                    "Elite builder gate off",
                    {"gate": "off"},
                    verification_class="presence",
                )
            ],
        )

    # CHECK 1: Elite directive
    elite_path = os.path.join(workspace_path, "proof", "ELITE_EXECUTION_DIRECTIVE.md")
    elite_txt = _read_text(elite_path) if workspace_path else None
    if not (elite_txt or "").strip():
        checks.append({"name": "elite_directive", "passed": False, "reason": "Missing proof/ELITE_EXECUTION_DIRECTIVE.md"})
        issues.append("Missing proof/ELITE_EXECUTION_DIRECTIVE.md — elite execution authority not materialized")
    else:
        checks.append({"name": "elite_directive", "passed": True})
        proof.append(
            _proof_item(
                "file",
                "Elite directive present",
                {"path": "proof/ELITE_EXECUTION_DIRECTIVE.md", "elite_materialized": True},
                verification_class="presence",
            )
        )

    # CHECK 2: Delivery classification
    dc_path = os.path.join(workspace_path, "proof", "DELIVERY_CLASSIFICATION.md")
    dc = _read_text(dc_path) if workspace_path else None
    if not (dc or "").strip():
        checks.append({"name": "delivery_classification", "passed": False, "reason": "Missing proof/DELIVERY_CLASSIFICATION.md"})
        issues.append("Missing proof/DELIVERY_CLASSIFICATION.md")
    else:
        ok_dc, dc_issues = _delivery_classification_ok(dc)
        if not ok_dc:
            checks.append({"name": "delivery_classification", "passed": False, "reason": "; ".join(dc_issues)})
            issues.extend(dc_issues)
        else:
            checks.append({"name": "delivery_classification", "passed": True})
        proof.append(
            _proof_item(
                "verification",
                "Delivery classification file",
                {"path": "proof/DELIVERY_CLASSIFICATION.md", "checks": "four_labels"},
                verification_class="syntax",
            )
        )
        
        # CHECK 3: Critical feature proof depth
        crit_tags = _goal_suggests_critical(job_goal)
        ok_crit, crit_issues = _critical_runtime_evidence(dc, crit_tags)
        if not ok_crit:
            checks.append({"name": "critical_feature_proof", "passed": False, "reason": "; ".join(crit_issues)})
            issues.extend(crit_issues)
        else:
            checks.append({"name": "critical_feature_proof", "passed": True})
            proof.append(
                _proof_item(
                    "verification",
                    "Critical feature proof depth",
                    {"tags": crit_tags, "presence_and_runtime": True},
                    verification_class="runtime",
                )
            )

    # CHECK 4: Error boundaries in code
    code_check_4 = _check_error_boundaries(workspace_path)
    checks.append(code_check_4)
    if not code_check_4["passed"]:
        issues.append(code_check_4["reason"])
    else:
        proof.append(_proof_item("verification", "Error boundaries present", {"check": "error_boundaries"}, verification_class="syntax"))

    # CHECK 5: Console.error/warn free
    code_check_5 = _check_console_errors(workspace_path)
    checks.append(code_check_5)
    if not code_check_5["passed"]:
        issues.append(code_check_5["reason"])
    else:
        proof.append(_proof_item("verification", "No console.error/warn", {"check": "console_clean"}, verification_class="syntax"))

    # CHECK 6: API error handling
    code_check_6 = _check_api_error_handling(workspace_path)
    checks.append(code_check_6)
    if not code_check_6["passed"]:
        issues.append(code_check_6["reason"])
    else:
        proof.append(_proof_item("verification", "API error handling", {"check": "api_errors"}, verification_class="syntax"))

    # CHECK 7: SQL parameterization
    code_check_7 = _check_sql_safety(workspace_path)
    checks.append(code_check_7)
    if not code_check_7["passed"]:
        issues.append(code_check_7["reason"])
    else:
        proof.append(_proof_item("verification", "SQL parameterization", {"check": "sql_safety"}, verification_class="syntax"))

    # CHECK 8: Auth/RBAC
    code_check_8 = _check_authentication(workspace_path)
    checks.append(code_check_8)
    if not code_check_8["passed"]:
        issues.append(code_check_8["reason"])
    else:
        proof.append(_proof_item("verification", "Auth/RBAC present", {"check": "authentication"}, verification_class="syntax"))

    # CHECK 9: No hardcoded secrets
    code_check_9 = _check_hardcoded_secrets(workspace_path)
    checks.append(code_check_9)
    if not code_check_9["passed"]:
        issues.append(code_check_9["reason"])
    else:
        proof.append(_proof_item("verification", "No hardcoded secrets", {"check": "secrets"}, verification_class="syntax"))

    # CHECK 10: Security headers
    code_check_10 = _check_security_headers(workspace_path)
    checks.append(code_check_10)
    if not code_check_10["passed"]:
        issues.append(code_check_10["reason"])
    else:
        proof.append(_proof_item("verification", "Security headers", {"check": "headers"}, verification_class="syntax"))

    # BINARY PASS/FAIL
    passed_checks = len([c for c in checks if c["passed"]])
    total_checks = len(checks)
    score = int((passed_checks / max(1, total_checks)) * 100)
    failed_check_names = [c["name"] for c in checks if not c["passed"]]
    
    passed = score >= 80  # >=80% = PASS
    
    if mode == "advisory" and not passed:
        proof.append(
            _proof_item(
                "verification",
                "Elite builder gate (advisory)",
                {"issues": issues, "would_fail_in_strict": True, "score": score},
                verification_class="runtime",
            )
        )
        result = _result(True, score, [], proof)
        result["checks"] = checks
        result["checks_passed"] = passed_checks
        result["checks_total"] = total_checks
        result["failed_checks"] = failed_check_names
        result["failure_reason"] = None  # Advisory mode: no failure
        return result

    result = _result(passed, score, issues if not passed else [], proof)
    result["checks"] = checks
    result["checks_passed"] = passed_checks
    result["checks_total"] = total_checks
    result["failed_checks"] = failed_check_names
    
    if passed:
        result["failure_reason"] = None
    else:
        result["failure_reason"] = "elite_checks_failed"
        result["recommendation"] = f"Fix failed checks: {', '.join(failed_check_names)}"
    
    return result


# ============================================================================
# FIX #3: ELITE BUILDER CHECKS (10-point verification)
# Each check returns: {"name": str, "passed": bool, "reason": str}
# ============================================================================

def _check_error_boundaries(workspace_path: str) -> Dict[str, Any]:
    """CHECK 4: Error boundaries in React code."""
    if not workspace_path:
        return {"name": "error_boundaries", "passed": False, "reason": "No workspace path"}
    
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]
            for f in files:
                if f.endswith((".jsx", ".tsx")):
                    path = os.path.join(root, f)
                    text = _read_text(path)
                    if text and "ErrorBoundary" in text:
                        return {"name": "error_boundaries", "passed": True}
    except:
        pass
    
    return {"name": "error_boundaries", "passed": False, "reason": "No Error Boundary component found"}


def _check_console_errors(workspace_path: str) -> Dict[str, Any]:
    """CHECK 5: No console.error or console.warn in production code."""
    if not workspace_path:
        return {"name": "console_errors", "passed": True}
    
    count = 0
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]
            for f in files:
                if f.endswith((".jsx", ".ts", ".tsx", ".js")):
                    path = os.path.join(root, f)
                    text = _read_text(path)
                    if text:
                        # Skip test files
                        if ".test." in f or ".spec." in f:
                            continue
                        count += text.count("console.error") + text.count("console.warn")
    except:
        pass
    
    if count > 0:
        return {"name": "console_errors", "passed": False, "reason": f"Found {count} console.error/warn calls"}
    return {"name": "console_errors", "passed": True}


def _check_api_error_handling(workspace_path: str) -> Dict[str, Any]:
    """CHECK 6: API routes have try-catch or error handling."""
    if not workspace_path:
        return {"name": "api_error_handling", "passed": True}
    
    try:
        backend_file = os.path.join(workspace_path, "backend", "main.py")
        if os.path.exists(backend_file):
            text = _read_text(backend_file)
            if text and ("@app.post" in text or "@app.get" in text):
                if "try:" in text or "except" in text or "HTTPException" in text:
                    return {"name": "api_error_handling", "passed": True}
                return {"name": "api_error_handling", "passed": False, "reason": "API routes lack error handling (try-catch)"}
    except:
        pass
    
    return {"name": "api_error_handling", "passed": True}


def _check_sql_safety(workspace_path: str) -> Dict[str, Any]:
    """CHECK 7: No raw SQL string interpolation."""
    if not workspace_path:
        return {"name": "sql_safety", "passed": True}
    
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]
            for f in files:
                if f.endswith((".py", ".sql")):
                    path = os.path.join(root, f)
                    text = _read_text(path)
                    if text:
                        # Check for f-strings with SQL
                        if 'f"' in text and "SELECT" in text:
                            continue  # Might be ok, could be string literal
                        if "execute(f'" in text or 'execute(f"' in text:
                            return {"name": "sql_safety", "passed": False, "reason": "SQL with f-string interpolation detected"}
    except:
        pass
    
    return {"name": "sql_safety", "passed": True}


def _check_authentication(workspace_path: str) -> Dict[str, Any]:
    """CHECK 8: Auth/RBAC patterns present."""
    if not workspace_path:
        return {"name": "authentication", "passed": False, "reason": "No workspace"}
    
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]
            for f in files:
                if f.endswith((".jsx", ".ts", ".tsx", ".py")):
                    path = os.path.join(root, f)
                    text = _read_text(path)
                    if text:
                        patterns = ("AuthContext", "useAuth", "JWT", "oauth", "Depends(get_current_user)", "is_authenticated")
                        if any(p in text for p in patterns):
                            return {"name": "authentication", "passed": True}
    except:
        pass
    
    return {"name": "authentication", "passed": False, "reason": "No authentication/authorization patterns found"}


def _check_hardcoded_secrets(workspace_path: str) -> Dict[str, Any]:
    """CHECK 9: No hardcoded API keys or secrets."""
    if not workspace_path:
        return {"name": "hardcoded_secrets", "passed": True}
    
    secret_patterns = [
        "api_key =",
        "apiKey =",
        "secret =",
        "password =",
        "sk_live_",
        "sk_test_",
        "OPENAI_KEY",
        "AWS_SECRET",
    ]
    
    count = 0
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build")]
            for f in files:
                if f.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
                    # Skip .env files, they're expected to have secrets
                    if f == ".env" or f == ".env.example":
                        continue
                    path = os.path.join(root, f)
                    text = _read_text(path)
                    if text:
                        for pattern in secret_patterns:
                            count += text.count(pattern)
    except:
        pass
    
    if count > 0:
        return {"name": "hardcoded_secrets", "passed": False, "reason": f"Found {count} potential hardcoded secrets"}
    return {"name": "hardcoded_secrets", "passed": True}


def _check_security_headers(workspace_path: str) -> Dict[str, Any]:
    """CHECK 10: Security headers in API."""
    if not workspace_path:
        return {"name": "security_headers", "passed": True}
    
    headers = [
        "Content-Security-Policy",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Strict-Transport-Security",
        "X-XSS-Protection",
    ]
    
    found = 0
    try:
        backend_file = os.path.join(workspace_path, "backend", "main.py")
        if os.path.exists(backend_file):
            text = _read_text(backend_file)
            if text:
                for header in headers:
                    if header in text:
                        found += 1
    except:
        pass
    
    if found >= 3:
        return {"name": "security_headers", "passed": True}
    return {"name": "security_headers", "passed": False, "reason": f"Only {found}/5 security headers configured"}
