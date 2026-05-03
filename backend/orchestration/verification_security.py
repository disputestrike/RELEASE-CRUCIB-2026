"""
verification.security — static checks for tenancy / PayPal sketches and obvious footguns.
Not a full SAST; complements production_gate secret scan on deploy.build.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

from .multitenancy_rls_sql import validate_rls_syntax


def _read_sql_migrations(workspace_path: str) -> str:
    mig = os.path.join(workspace_path, "db", "migrations")
    if not os.path.isdir(mig):
        return ""
    parts: List[str] = []
    for name in sorted(os.listdir(mig)):
        if not name.endswith(".sql"):
            continue
        try:
            with open(
                os.path.join(mig, name), encoding="utf-8", errors="replace"
            ) as fh:
                parts.append(fh.read())
        except OSError:
            continue
    return "\n".join(parts).lower()


def _read_file(rel: str, workspace_path: str) -> str:
    p = os.path.normpath(os.path.join(workspace_path, rel.replace("/", os.sep)))
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _pi(
    proof_type: str,
    title: str,
    payload: Dict[str, Any],
    *,
    verification_class: str = "presence",
) -> Dict[str, Any]:
    p = {**payload, "verification_class": verification_class}
    return {"proof_type": proof_type, "title": title, "payload": p}


def _vr(
    passed: bool, score: int, issues: List[str], proof: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


def _npm_audit_if_enabled(
    workspace_path: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Optional npm audit during verification.security (off by default; can be slow)."""
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []
    raw = os.environ.get("CRUCIBAI_NPM_AUDIT_ON_SECURITY", "").strip().lower()
    if raw not in ("1", "true", "yes"):
        return issues, proof
    pkg = os.path.join(workspace_path, "package.json")
    if not os.path.isfile(pkg):
        return issues, proof
    npm = shutil.which("npm")
    if not npm:
        proof.append(
            _pi(
                "verification",
                "Security: npm audit skipped (npm not on PATH)",
                {"check": "npm_audit", "skipped": True},
                verification_class="presence",
            ),
        )
        return issues, proof
    try:
        r = subprocess.run(
            [npm, "audit", "--omit=dev", "--json"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        summary: Any = None
        try:
            data = json.loads(r.stdout or "{}")
            meta = data.get("metadata") or {}
            summary = meta.get("vulnerabilities") or meta.get("vulnerability_count")
        except Exception:
            summary = (r.stdout or "")[:400]
        proof.append(
            _pi(
                "verification",
                f"Security: npm audit finished (exit {r.returncode})",
                {"check": "npm_audit", "exit": r.returncode, "summary": summary},
                verification_class="runtime",
            ),
        )
        strict = os.environ.get("CRUCIBAI_NPM_AUDIT_STRICT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if strict and r.returncode != 0:
            issues.append("npm audit reported issues (CRUCIBAI_NPM_AUDIT_STRICT=1)")
    except subprocess.TimeoutExpired:
        issues.append("npm audit timed out (120s)")
    except Exception as e:
        proof.append(
            _pi(
                "verification",
                f"Security: npm audit error: {str(e)[:120]}",
                {"check": "npm_audit", "error": True},
                verification_class="presence",
            ),
        )
    return issues, proof


def verify_security_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        return _vr(False, 0, ["No workspace for security verification"], proof)

    sql = _read_sql_migrations(workspace_path)
    if sql:
        if "tenant" in sql and ("tenant_id" in sql or "tenants" in sql):
            proof.append(
                _pi(
                    "verification",
                    "Security: tenancy columns/tables present in migration sketch",
                    {"check": "tenancy_sql_sketch"},
                    verification_class="runtime",
                ),
            )
        sl = sql.lower()
        if "row level security" in sl and "create policy" in sl:
            proof.append(
                _pi(
                    "verification",
                    "Security: migration SQL includes PostgreSQL RLS (FORCE ROW LEVEL SECURITY / CREATE POLICY)",
                    {"check": "rls_policies_in_migrations"},
                    verification_class="runtime",
                ),
            )
            mig_dir = os.path.join(workspace_path, "db", "migrations")
            for name in sorted(os.listdir(mig_dir)):
                if not name.endswith(".sql"):
                    continue
                p = os.path.join(mig_dir, name)
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        one = fh.read()
                except OSError:
                    continue
                ol = one.lower()
                if "row level security" not in ol or "create policy" not in ol:
                    continue
                v = validate_rls_syntax(one)
                if not v["passed"]:
                    for it in v["issues"]:
                        issues.append(f"{name}: {it}")
                else:
                    proof.append(
                        _pi(
                            "verification",
                            f"Security: RLS migration structurally valid ({name})",
                            {
                                "check": "rls_syntax_valid",
                                "file": name,
                                "status": "pass",
                            },
                            verification_class="runtime",
                        ),
                    )
        if "paypal_events_processed" in sql:
            proof.append(
                _pi(
                    "verification",
                    "Security: PayPal webhook idempotency table sketch in SQL",
                    {"check": "payment_webhook_idempotency_sql"},
                    verification_class="runtime",
                ),
            )
        proof.append(
            _pi(
                "verification",
                f"Security: scanned {len(sql)} chars of migration SQL",
                {"check": "migrations_read"},
                verification_class="presence",
            ),
        )
    else:
        # Not all projects require a database — skip migration check gracefully.
        proof.append(
            _pi(
                "verification",
                "Security: no db/migrations SQL found — skipping migration security checks (no DB required)",
                {"check": "migrations_skipped", "reason": "no_db_migrations_dir"},
                verification_class="presence",
            )
        )

    main_py = _read_file("backend/main.py", workspace_path)
    if not main_py.strip():
        # Not all projects have a Python backend — skip this check gracefully.
        proof.append(
            _pi(
                "verification",
                "Security: backend/main.py not found — skipping backend security checks (frontend-only or non-Python project)",
                {"check": "backend_main_skipped", "reason": "no_backend_main"},
                verification_class="presence",
            )
        )
    else:
        if "CORSMiddleware" in main_py and (
            'allow_origins=["*"]' in main_py or "allow_origins=['*']" in main_py
        ):
            proof.append(
                _pi(
                    "verification",
                    "Security note: CORS allow_origins is wildcard — tighten before production",
                    {"check": "cors_wildcard", "severity": "advisory"},
                    verification_class="presence",
                ),
            )
        if "paypal_routes" in main_py or "include_router" in main_py:
            proof.append(
                _pi(
                    "verification",
                    "Security: API app includes mounted sub-routers (e.g. PayPal)",
                    {"check": "router_mount"},
                    verification_class="presence",
                ),
            )

    pkg_raw = _read_file("package.json", workspace_path)
    if pkg_raw.strip():
        try:
            pkg_data = json.loads(pkg_raw)
        except json.JSONDecodeError as e:
            issues.append(f"package.json invalid JSON: {e}")
        else:
            if pkg_data.get("dependencies"):
                proof.append(
                    _pi(
                        "verification",
                        "Security: package.json dependencies declared (supply-chain review is manual)",
                        {"check": "package_json_present"},
                        verification_class="presence",
                    ),
                )
            eng = pkg_data.get("engines") or {}
            if eng:
                proof.append(
                    _pi(
                        "verification",
                        "Security: package.json engines field set (reproducible Node/npm)",
                        {"check": "package_engines", "engines": eng},
                        verification_class="presence",
                    ),
                )
            else:
                proof.append(
                    _pi(
                        "verification",
                        "Security note: package.json has no engines field — pin Node for production CI",
                        {"check": "package_engines_missing", "severity": "advisory"},
                        verification_class="presence",
                    ),
                )
    extra_issues, extra_proof = _npm_audit_if_enabled(workspace_path)
    proof.extend(extra_proof)
    issues.extend(extra_issues)

    obs_dir = os.path.join(workspace_path, "deploy", "observability")
    if os.path.isdir(obs_dir):
        proof.append(
            _pi(
                "verification",
                "Security: observability pack directory present (OTel/Prometheus/Grafana stubs)",
                {"check": "observability_pack_present"},
                verification_class="presence",
            ),
        )
    tf_sketch = os.path.join(
        workspace_path, "terraform", "multiregion_sketch", "main.tf"
    )
    if os.path.isfile(tf_sketch):
        proof.append(
            _pi(
                "verification",
                "Security: multi-region Terraform sketch present (aws/gcp/azure module stubs)",
                {"check": "multiregion_terraform_sketch_present"},
                verification_class="presence",
            ),
        )

    score = 100 if not issues else max(55, 100 - len(issues) * 22)
    return _vr(len(issues) == 0, score, issues, proof)
