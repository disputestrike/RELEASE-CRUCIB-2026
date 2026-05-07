"""Enterprise contract, proof, and delivery classification materialization.

This module is intentionally deterministic. It does not ask the model whether a
build is complete; it reads the workspace, compares it with the BuildContract,
checks frontend/backend wiring, classifies critical paths honestly, and writes
the proof bundle into the generated workspace.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .contract_artifacts import _read_text_files, persist_contract_artifacts


REQUIRED_PROOF_FILES = [
    "proof/ELITE_ANALYSIS.md",
    "proof/BUILD_CONTRACT.md",
    "proof/ARCHITECTURE_DECISIONS.md",
    "proof/API_ALIGNMENT.md",
    "proof/DATABASE_PROOF.md",
    "proof/AUTH_RBAC_PROOF.md",
    "proof/SECURITY_REVIEW.md",
    "proof/COMPLIANCE_READINESS.md",
    "proof/TEST_RESULTS.md",
    "proof/BUILD_RESULTS.md",
    "proof/DEPLOYMENT_READINESS.md",
    "proof/DELIVERY_CLASSIFICATION.md",
    "proof/KNOWN_LIMITATIONS.md",
    "proof/CONTINUATION_BLUEPRINT.md",
    "proof/ELITE_DELIVERY_CERT.md",
]

STRICT_DELIVERY_TERMS = (
    "enterprise",
    "full-stack",
    "fullstack",
    "backend",
    "database",
    "auth",
    "authentication",
    "login",
    "billing",
    "paypal",
    "payment",
    "checkout",
    "subscription",
    "compliance",
    "regulated",
    "hipaa",
    "soc2",
    "soc 2",
    "gdpr",
    "pci",
    "multi-tenant",
    "multitenant",
    "tenant",
    "ecommerce",
    "e-commerce",
    "marketplace",
    "healthcare",
    "fintech",
    "government",
    "defense",
    "automation",
    "agent platform",
)

SECRET_RE = re.compile(
    r"(ghp_[A-Za-z0-9_]{20,}|sk_live_[A-Za-z0-9_]{16,}|access_token\$production\$[A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)
FETCH_RE = re.compile(r"\bfetch\(\s*['\"](?P<url>/api/[^'\"]+)['\"]", re.IGNORECASE)
AXIOS_RE = re.compile(
    r"\baxios\.(?P<method>get|post|put|patch|delete)\(\s*['\"](?P<url>/api/[^'\"]+)['\"]",
    re.IGNORECASE,
)
CLIENT_METHOD_RE = re.compile(
    r"\b(?:api|client|http)\.(?P<method>get|post|put|patch|delete)\(\s*['\"](?P<url>/api/[^'\"]+)['\"]",
    re.IGNORECASE,
)
FASTAPI_PREFIX_RE = re.compile(r"APIRouter\([^)]*prefix\s*=\s*['\"](?P<prefix>/[^'\"]*)['\"]", re.DOTALL)
FASTAPI_ROUTE_RE = re.compile(
    r"@(?P<owner>router|app)\.(?P<method>get|post|put|patch|delete)\(\s*['\"](?P<path>/[^'\"]*)['\"]",
    re.IGNORECASE,
)
EXPRESS_ROUTE_RE = re.compile(
    r"\b(?:app|router)\.(?P<method>get|post|put|patch|delete)\(\s*['\"](?P<path>/[^'\"]*)['\"]",
    re.IGNORECASE,
)


def _goal(job: Mapping[str, Any]) -> str:
    return str(job.get("goal") or job.get("prompt") or job.get("description") or "")


def _safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _md_list(items: Iterable[Any]) -> str:
    values = [str(item) for item in items if str(item)]
    if not values:
        return "- None"
    return "\n".join(f"- {item}" for item in values)


def _status_table(rows: Iterable[Mapping[str, Any]]) -> str:
    out = ["| Item | Status | Evidence |", "| --- | --- | --- |"]
    for row in rows:
        out.append(
            "| {item} | {status} | {evidence} |".format(
                item=str(row.get("item") or row.get("feature") or "").replace("|", "/"),
                status=str(row.get("status") or "").replace("|", "/"),
                evidence=str(row.get("evidence") or row.get("note") or "").replace("|", "/"),
            )
        )
    return "\n".join(out)


def _normalize_path(path: str) -> str:
    path = (path or "").split("?", 1)[0].rstrip("/") or "/"
    path = re.sub(r"\{[^/]+\}", ":param", path)
    path = re.sub(r":[^/]+", ":param", path)
    return path


def _extract_frontend_calls(files: Mapping[str, str]) -> List[Dict[str, str]]:
    calls: List[Dict[str, str]] = []
    for rel, source in files.items():
        if not rel.endswith((".js", ".jsx", ".ts", ".tsx")):
            continue
        for match in FETCH_RE.finditer(source):
            tail = source[match.end() : match.end() + 180]
            method_match = re.search(r"method\s*:\s*['\"](?P<method>[A-Z]+)['\"]", tail, re.IGNORECASE)
            calls.append(
                {
                    "file": rel,
                    "method": (method_match.group("method") if method_match else "GET").upper(),
                    "path": _normalize_path(match.group("url")),
                }
            )
        for pattern in (AXIOS_RE, CLIENT_METHOD_RE):
            for match in pattern.finditer(source):
                calls.append(
                    {
                        "file": rel,
                        "method": match.group("method").upper(),
                        "path": _normalize_path(match.group("url")),
                    }
                )
    dedup: Dict[tuple[str, str, str], Dict[str, str]] = {}
    for call in calls:
        dedup[(call["file"], call["method"], call["path"])] = call
    return list(dedup.values())


def _join_prefix(prefix: str, route: str) -> str:
    if route.startswith("/api/"):
        return route
    if not prefix:
        return route
    return f"{prefix.rstrip('/')}/{route.lstrip('/')}"


def _extract_backend_routes(files: Mapping[str, str]) -> List[Dict[str, str]]:
    routes: List[Dict[str, str]] = []
    for rel, source in files.items():
        if not rel.endswith((".py", ".js", ".ts")):
            continue
        prefix_match = FASTAPI_PREFIX_RE.search(source)
        prefix = prefix_match.group("prefix") if prefix_match else ""
        for match in FASTAPI_ROUTE_RE.finditer(source):
            routes.append(
                {
                    "file": rel,
                    "method": match.group("method").upper(),
                    "path": _normalize_path(_join_prefix(prefix, match.group("path"))),
                }
            )
        for match in EXPRESS_ROUTE_RE.finditer(source):
            routes.append(
                {
                    "file": rel,
                    "method": match.group("method").upper(),
                    "path": _normalize_path(match.group("path")),
                }
            )
    dedup: Dict[tuple[str, str, str], Dict[str, str]] = {}
    for route in routes:
        dedup[(route["file"], route["method"], route["path"])] = route
    return list(dedup.values())


def analyze_api_alignment(files: Mapping[str, str]) -> Dict[str, Any]:
    calls = _extract_frontend_calls(files)
    routes = _extract_backend_routes(files)
    route_index = {(route["method"], route["path"]): route for route in routes}
    route_path_index = {route["path"]: route for route in routes}

    rows: List[Dict[str, Any]] = []
    missing: List[Dict[str, str]] = []
    for call in calls:
        exact = route_index.get((call["method"], call["path"]))
        path_only = route_path_index.get(call["path"])
        matched = exact or path_only
        status = "pass" if exact else "method-mismatch" if path_only else "missing"
        if status != "pass":
            missing.append(call)
        rows.append(
            {
                "frontend_call": f"{call['method']} {call['path']}",
                "frontend_file": call["file"],
                "backend_route": f"{matched['method']} {matched['path']}" if matched else "",
                "backend_file": matched["file"] if matched else "",
                "status": status,
            }
        )

    return {
        "passed": len(missing) == 0,
        "frontend_calls": calls,
        "backend_routes": routes,
        "rows": rows,
        "missing": missing,
    }


def _combined_text(files: Mapping[str, str]) -> str:
    return "\n".join(files.values()).lower()


def _has_file(files: Mapping[str, str], *needles: str) -> bool:
    lower_paths = [path.lower() for path in files]
    return any(any(needle.lower() in path for path in lower_paths) for needle in needles)


def classify_delivery(
    *,
    goal: str,
    files: Mapping[str, str],
    build_passed: bool,
    api_alignment: Mapping[str, Any],
) -> Dict[str, Any]:
    lower_goal = goal.lower()
    combined = _combined_text(files)

    features: List[Dict[str, str]] = [
        {
            "feature": "frontend_build",
            "status": "Implemented" if build_passed else "Blocked",
            "evidence": "Build command passed." if build_passed else "Build command did not pass.",
        },
        {
            "feature": "api_frontend_wiring",
            "status": "Implemented" if api_alignment.get("passed") else "Unverified",
            "evidence": "All detected frontend API calls map to backend routes."
            if api_alignment.get("passed")
            else f"{len(api_alignment.get('missing') or [])} frontend API call(s) have no exact backend route.",
        },
    ]

    requires_auth = any(term in lower_goal for term in ("auth", "login", "sso", "oauth", "user dashboard"))
    requires_billing = any(term in lower_goal for term in ("billing", "paypal", "payment", "checkout", "subscription"))
    requires_database = any(
        term in lower_goal
        for term in ("database", "persist", "crud", "backend", "fullstack", "full-stack", "auth", "billing")
    )
    requires_tenancy = any(term in lower_goal for term in ("multi-tenant", "multitenant", "tenant isolation"))
    requires_compliance = any(term in lower_goal for term in ("hipaa", "soc2", "soc 2", "gdpr", "pci", "compliance", "regulated"))

    if requires_auth:
        auth_files = _has_file(files, "auth", "session", "rbac")
        real_auth = bool(auth_files and re.search(r"\b(bcrypt|passlib|argon2|jwt|oauth)\b", combined))
        demo_auth = bool(re.search(r"\b(demo user|mock user|localstorage|fake auth|sample user)\b", combined))
        features.append(
            {
                "feature": "auth",
                "status": "Implemented" if real_auth and not demo_auth else "Mocked" if demo_auth else "Stubbed",
                "evidence": "Auth code with credential/session primitives detected."
                if real_auth and not demo_auth
                else "Auth-like UI/state is demo or local-only."
                if demo_auth
                else "Auth was requested but no real auth subsystem was detected.",
            }
        )

    if requires_billing:
        billing_files = _has_file(files, "billing", "paypal", "payment")
        has_webhook = "/webhook" in combined or "webhook" in combined
        has_signature = "signature" in combined and ("paypal" in combined or "webhook" in combined)
        provider_env = bool(re.search(r"(PAYPAL_|PAYMENT_|BILLING_)", "\n".join(files.values())))
        status = "Implemented" if billing_files and has_webhook and has_signature and provider_env else "Mocked" if billing_files else "Stubbed"
        features.append(
            {
                "feature": "billing",
                "status": status,
                "evidence": "Billing files, webhook, signature verification, and provider env are present."
                if status == "Implemented"
                else "Billing code exists but live settlement depends on provider credentials/test mode proof."
                if status == "Mocked"
                else "Billing was requested but no billing subsystem was detected.",
            }
        )

    if requires_database:
        has_migration = _has_file(files, "migration", "schema.sql", "prisma", "alembic", "db/schema")
        has_model = _has_file(files, "models", "schema", "repositories", "migrations")
        features.append(
            {
                "feature": "database_persistence",
                "status": "Implemented" if has_migration and has_model else "Stubbed",
                "evidence": "Schema/migration and model/repository files detected."
                if has_migration and has_model
                else "Database persistence was required but complete migrations/models were not detected.",
            }
        )

    if requires_tenancy:
        tenant_code = "tenant" in combined and ("organization" in combined or "org_id" in combined)
        features.append(
            {
                "feature": "tenant_isolation",
                "status": "Implemented" if tenant_code else "Stubbed",
                "evidence": "Tenant-scoped fields/control code detected."
                if tenant_code
                else "Tenant isolation was requested but tenant-scoped enforcement was not detected.",
            }
        )

    if requires_compliance:
        features.append(
            {
                "feature": "compliance_readiness",
                "status": "Unverified",
                "evidence": "Compliance readiness artifacts are generated; external certification is never claimed.",
            }
        )

    blocked = [f for f in features if f["status"] in {"Blocked", "Stubbed"}]
    mocked = [f for f in features if f["status"] == "Mocked"]
    unverified = [f for f in features if f["status"] == "Unverified"]
    return {
        "features": features,
        "blocked": blocked,
        "mocked": mocked,
        "unverified": unverified,
    }


def _strict_delivery_required(goal: str, build_class: str) -> bool:
    lower_goal = goal.lower()
    if any(term in lower_goal for term in STRICT_DELIVERY_TERMS):
        return True
    return build_class in {
        "regulated_saas",
        "fullstack_saas",
        "healthcare_platform",
        "fintech_platform",
        "govtech_platform",
        "defense_enterprise_system",
        "ecommerce",
        "marketplace",
        "automation_workflow",
        "ai_agent_platform",
        "api_backend",
        "api_rest",
        "automation",
        "browser_extension",
        "crm",
        "desktop_app",
        "erp",
        "game_2d",
        "game_3d",
        "internal_admin_tool",
        "iot_dashboard",
        "mobile_expo",
        "mobile_flutter",
        "mobile_react_native",
        "plugin_integration",
    }


def _secret_findings(files: Mapping[str, str]) -> List[str]:
    findings = []
    for rel, source in files.items():
        if SECRET_RE.search(source):
            findings.append(rel)
    return findings


def _manifest(files: Mapping[str, str]) -> Dict[str, Any]:
    entries = [{"path": rel, "size": len(source.encode("utf-8"))} for rel, source in sorted(files.items())]
    return {"total_files": len(entries), "entries": entries}


def _proof_index_payload(proof_files: Iterable[str], gate: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate": gate,
        "entries": [
            {
                "type": Path(path).stem.lower(),
                "path": path,
                "level": "runtime" if Path(path).name in {"BUILD_RESULTS.md", "TEST_RESULTS.md"} else "contract",
            }
            for path in proof_files
        ],
    }


def _api_alignment_markdown(alignment: Mapping[str, Any]) -> str:
    rows = ["| Frontend API call | Frontend file | Backend route | Backend file | Status |", "| --- | --- | --- | --- | --- |"]
    for row in alignment.get("rows") or []:
        rows.append(
            "| {frontend_call} | {frontend_file} | {backend_route} | {backend_file} | {status} |".format(
                frontend_call=row.get("frontend_call", ""),
                frontend_file=row.get("frontend_file", ""),
                backend_route=row.get("backend_route", "") or "MISSING",
                backend_file=row.get("backend_file", "") or "MISSING",
                status=row.get("status", ""),
            )
        )
    if len(rows) == 2:
        rows.append("| No frontend API calls detected | n/a | n/a | n/a | pass |")
    return "\n".join(rows)


def _classification_markdown(classification: Mapping[str, Any]) -> str:
    groups = {label: [] for label in ("Implemented", "Mocked", "Stubbed", "Unverified", "Blocked")}
    for feature in classification.get("features") or []:
        groups.setdefault(str(feature.get("status")), []).append(feature)

    sections = []
    for label in ("Implemented", "Mocked", "Stubbed", "Unverified", "Blocked"):
        items = groups.get(label) or []
        sections.append(f"## {label}")
        if not items:
            sections.append("- None")
        else:
            sections.extend(f"- {item['feature']}: {item['evidence']}" for item in items)
    return "\n\n".join(sections)


def _feature_lines(items: Iterable[Mapping[str, Any]]) -> List[str]:
    return [f"{item.get('feature')}: {item.get('evidence')}" for item in items]


def _domain_terms(goal: str, contract: Mapping[str, Any]) -> List[str]:
    lower_goal = goal.lower()
    terms = []
    for key in (
        "healthcare",
        "fintech",
        "legal",
        "government",
        "defense",
        "education",
        "ecommerce",
        "marketplace",
        "automation",
        "ai agent",
        "iot",
    ):
        if key in lower_goal:
            terms.append(key)
    build_class = str(contract.get("build_class") or "")
    if build_class and build_class not in terms:
        terms.append(build_class)
    return terms or ["general software"]


def _research_docs(goal: str, contract: Mapping[str, Any]) -> Dict[str, str]:
    domains = _domain_terms(goal, contract)
    workflows = contract.get("core_workflows") or []
    models = contract.get("data_models") or []
    compliance = contract.get("compliance_requirements") or []
    security = contract.get("security_controls") or []

    return {
        "docs/research_notes/DOMAIN_RESEARCH.md": (
            "# Domain Research\n\n"
            f"- Detected domains: {', '.join(domains)}\n"
            "- Research mode: deterministic domain-pack synthesis from the approved build contract.\n"
            "- Current/live external standards should be rechecked before regulated production use.\n\n"
            "## Extracted Workflows\n"
            f"{_md_list(workflows)}\n\n"
            "## Extracted Data Models\n"
            f"{_md_list(models)}"
        ),
        "docs/requirements/REQUIREMENTS_FROM_RESEARCH.md": (
            "# Requirements From Research\n\n"
            "## Product Shape\n"
            f"- Build class: {contract.get('build_class')}\n"
            f"- Target platforms: {', '.join(contract.get('target_platforms') or []) or 'not specified'}\n\n"
            "## Workflows\n"
            f"{_md_list(workflows)}\n\n"
            "## Security Controls\n"
            f"{_md_list(security)}"
        ),
        "docs/compliance/COMPLIANCE_NOTES.md": (
            "# Compliance Notes\n\n"
            "This is readiness documentation only and does not claim certification.\n\n"
            f"{_md_list(compliance or ['No regulated compliance obligation detected from the request.'])}"
        ),
        "docs/technical_spec/DOMAIN_TECHNICAL_SPEC.md": (
            "# Domain Technical Spec\n\n"
            f"- Stack: {json.dumps(contract.get('stack') or {}, sort_keys=True)}\n"
            f"- Deployment target: {contract.get('deployment_target') or 'zip_and_railway_ready'}\n\n"
            "## API Endpoints\n"
            f"{_md_list(contract.get('required_api_endpoints') or [])}\n\n"
            "## Database Tables\n"
            f"{_md_list(contract.get('required_database_tables') or [])}"
        ),
    }


def _compliance_docs(contract: Mapping[str, Any]) -> Dict[str, str]:
    controls = contract.get("security_controls") or []
    tables = contract.get("required_database_tables") or []
    roles = contract.get("roles") or []
    permissions = contract.get("permissions") or []
    requirements = contract.get("compliance_requirements") or []
    base_note = "Readiness artifact only. External certification requires external audit, counsel, and production evidence."
    return {
        "docs/compliance/CONTROL_MATRIX.md": "# Control Matrix\n\n" + base_note + "\n\n" + _md_list(controls),
        "docs/compliance/DATA_FLOW_MAP.md": "# Data Flow Map\n\n" + _md_list(tables),
        "docs/compliance/RISK_REGISTER.md": "# Risk Register\n\n" + _md_list(requirements or ["No regulated risk class detected."]),
        "docs/compliance/AUDIT_LOG_SPEC.md": "# Audit Log Spec\n\n- actor_id\n- action\n- resource_type\n- resource_id\n- tenant_id\n- timestamp\n- metadata\n",
        "docs/compliance/ACCESS_CONTROL_MATRIX.md": (
            "# Access Control Matrix\n\n"
            "## Roles\n"
            f"{_md_list(roles)}\n\n"
            "## Permissions\n"
            f"{_md_list(permissions)}"
        ),
        "docs/compliance/RETENTION_POLICY.md": "# Retention Policy\n\n" + base_note + "\n\n- Define retention by data class.\n- Support export/delete where applicable.\n",
        "docs/compliance/INCIDENT_RESPONSE_RUNBOOK.md": "# Incident Response Runbook\n\n- Detect\n- Contain\n- Eradicate\n- Recover\n- Notify where required\n",
        "docs/compliance/VENDOR_INTEGRATION_RISK.md": "# Vendor Integration Risk\n\n- Track provider credentials.\n- Verify webhook signatures.\n- Avoid logging sensitive payloads.\n",
        "docs/compliance/HIPAA_READINESS.md": "# HIPAA Readiness\n\n" + base_note + "\n\n- Minimum necessary access\n- PHI access audit\n- BAA review\n",
        "docs/compliance/SOC2_CONTROL_MAPPING.md": "# SOC2 Control Mapping\n\n" + base_note + "\n\n- Security\n- Availability\n- Confidentiality\n- Change management\n",
        "docs/compliance/GDPR_DATA_MAP.md": "# GDPR Data Map\n\n" + base_note + "\n\n- Data categories\n- Processing purpose\n- Retention\n- Export/delete workflow\n",
        "docs/compliance/SECURITY_CONTROLS.md": "# Security Controls\n\n" + _md_list(controls),
        "docs/compliance/AUDIT_EVIDENCE_PLAN.md": "# Audit Evidence Plan\n\n- Build proof\n- Test proof\n- Access logs\n- Change logs\n- Deployment logs\n",
    }


def _compute_delivery_gate(
    *,
    goal: str,
    contract: Mapping[str, Any],
    files: Mapping[str, str],
    build_passed: bool,
    api_alignment: Mapping[str, Any],
    classification: Mapping[str, Any],
    proof_files: List[str],
) -> Dict[str, Any]:
    build_class = str(contract.get("build_class") or "")
    strict = _strict_delivery_required(goal, build_class)
    failed: List[str] = []

    if not build_passed:
        failed.append("build_pass")
    missing_proofs = [path for path in REQUIRED_PROOF_FILES if path not in proof_files]
    if missing_proofs:
        failed.append("required_proof_files")
    if not api_alignment.get("passed"):
        failed.append("api_alignment")
    if _secret_findings(files):
        failed.append("secret_scan")
    if strict and (classification.get("blocked") or classification.get("mocked")):
        failed.append("critical_paths_not_fully_implemented")

    allowed = build_passed and not _secret_findings(files) and (not strict or not failed)
    blocks_completion = not allowed if strict or not build_passed else False
    status = "PASS" if allowed and not failed else "PASS_WITH_LIMITATIONS" if allowed else "FAILED_DELIVERY_GATE"
    return {
        "status": status,
        "allowed": allowed,
        "strict": strict,
        "blocks_completion": blocks_completion,
        "failed_checks": failed,
        "missing_proof_files": missing_proofs,
        "build_class": build_class,
    }


def generate_enterprise_proof_artifacts(
    workspace_path: str,
    job: Mapping[str, Any],
    *,
    plan: Optional[Mapping[str, Any]] = None,
    generation_result: Optional[Mapping[str, Any]] = None,
    assemble_result: Optional[Mapping[str, Any]] = None,
    verify_result: Optional[Mapping[str, Any]] = None,
    repair_result: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Write contract/proof/gate artifacts into a build workspace."""

    root = Path(workspace_path)
    root.mkdir(parents=True, exist_ok=True)
    goal = _goal(job)
    job_id = str(job.get("id") or job.get("job_id") or "build")
    build_passed = bool((verify_result or {}).get("passed"))

    contract_result = persist_contract_artifacts(str(root), job)
    contract = contract_result.get("contract_dict") or {}
    files = _read_text_files(str(root))
    api_alignment = analyze_api_alignment(files)
    classification = classify_delivery(
        goal=goal,
        files=files,
        build_passed=build_passed,
        api_alignment=api_alignment,
    )

    proof_files = list(REQUIRED_PROOF_FILES)
    gate = _compute_delivery_gate(
        goal=goal,
        contract=contract,
        files=files,
        build_passed=build_passed,
        api_alignment=api_alignment,
        classification=classification,
        proof_files=proof_files,
    )

    meta_dir = root / ".crucibai"
    meta_dir.mkdir(parents=True, exist_ok=True)
    proof_dir = root / "proof"
    proof_dir.mkdir(parents=True, exist_ok=True)

    manifest = _manifest(files)
    now = datetime.now(timezone.utc).isoformat()
    build_command = " ".join((plan or {}).get("build_command") or ["npm", "run", "build"])

    documents: Dict[str, str] = {
        "proof/ELITE_ANALYSIS.md": (
            "# Elite Analysis\n\n"
            f"- Build ID: {job_id}\n"
            f"- Product: {contract.get('product_name')}\n"
            f"- Build class: {contract.get('build_class')}\n"
            f"- Strict delivery gate: {gate['strict']}\n"
            f"- Generated at: {now}\n\n"
            "This build is judged by behavior, wiring, and proof. File presence alone is not enough."
        ),
        "proof/BUILD_CONTRACT.md": (
            "# Build Contract\n\n"
            f"- Original goal: {goal}\n"
            f"- Target platforms: {', '.join(contract.get('target_platforms') or []) or 'not specified'}\n"
            f"- Stack: {json.dumps(contract.get('stack') or {}, sort_keys=True)}\n\n"
            "## Users\n"
            f"{_md_list(contract.get('users') or [])}\n\n"
            "## Roles\n"
            f"{_md_list(contract.get('roles') or [])}\n\n"
            "## Core Workflows\n"
            f"{_md_list(contract.get('core_workflows') or [])}\n\n"
            "## Required API Endpoints\n"
            f"{_md_list(contract.get('required_api_endpoints') or [])}\n\n"
            "## Required Proof Types\n"
            f"{_md_list(contract.get('required_proof_types') or [])}"
        ),
        "proof/ARCHITECTURE_DECISIONS.md": (
            "# Architecture Decisions\n\n"
            f"- Build class: {contract.get('build_class')}\n"
            f"- Deployment target: {contract.get('deployment_target') or 'zip_and_railway_ready'}\n"
            "- The generated workspace must include the proof folder so export/download carries evidence with code.\n"
            "- Critical integrations are classified rather than silently treated as production-live."
        ),
        "proof/API_ALIGNMENT.md": "# API Alignment\n\n" + _api_alignment_markdown(api_alignment),
        "proof/DATABASE_PROOF.md": (
            "# Database Proof\n\n"
            f"{_status_table([{'item': item, 'status': 'required', 'evidence': 'declared by BuildContract'} for item in contract.get('required_database_tables') or []])}\n\n"
            "Detected database files:\n"
            f"{_md_list(path for path in files if any(token in path.lower() for token in ('db', 'migration', 'schema', 'model', 'repository')))}"
        ),
        "proof/AUTH_RBAC_PROOF.md": (
            "# Auth RBAC Proof\n\n"
            f"{_md_list(contract.get('auth_requirements') or [])}\n\n"
            f"{_md_list(contract.get('permissions') or [])}"
        ),
        "proof/SECURITY_REVIEW.md": (
            "# Security Review\n\n"
            f"{_status_table([{'item': control, 'status': 'required', 'evidence': 'declared by BuildContract'} for control in contract.get('security_controls') or []])}\n\n"
            f"- Secret scan findings: {len(_secret_findings(files))}"
        ),
        "proof/COMPLIANCE_READINESS.md": (
            "# Compliance Readiness\n\n"
            "This is readiness evidence only. It does not claim external certification.\n\n"
            f"{_md_list(contract.get('compliance_requirements') or ['No regulated compliance pack required by the detected intent.'])}"
        ),
        "proof/TEST_RESULTS.md": (
            "# Test Results\n\n"
            f"- Install command success: {bool((assemble_result or {}).get('success'))}\n"
            f"- Build command: `{build_command}`\n"
            f"- Build passed: {build_passed}\n"
            f"- Repair attempted: {repair_result is not None}"
        ),
        "proof/BUILD_RESULTS.md": (
            "# Build Results\n\n"
            f"- Return code: {(verify_result or {}).get('returncode')}\n"
            f"- Dist exists: {(verify_result or {}).get('dist_exists')}\n"
            f"- Build passed: {build_passed}\n\n"
            "## Error Excerpt\n\n"
            "```text\n"
            f"{str((verify_result or {}).get('stderr') or (verify_result or {}).get('stdout') or '')[:2000]}\n"
            "```"
        ),
        "proof/DEPLOYMENT_READINESS.md": (
            "# Deployment Readiness\n\n"
            f"- Deployment target: {contract.get('deployment_target') or 'zip_and_railway_ready'}\n"
            f"- Dockerfile present: {'Dockerfile' in files}\n"
            f"- Environment example present: {'.env.example' in files}\n"
            "- Railway/custom-domain deployment still depends on the connected production project and configured variables."
        ),
        "proof/DELIVERY_CLASSIFICATION.md": "# Delivery Classification\n\n" + _classification_markdown(classification),
        "proof/KNOWN_LIMITATIONS.md": (
            "# Known Limitations\n\n"
            "## Mocked\n"
            f"{_md_list(_feature_lines(classification.get('mocked') or []))}\n\n"
            "## Stubbed or Blocked\n"
            f"{_md_list(_feature_lines(classification.get('blocked') or []))}\n\n"
            "## Unverified\n"
            f"{_md_list(_feature_lines(classification.get('unverified') or []))}"
        ),
        "proof/CONTINUATION_BLUEPRINT.md": (
            "# Continuation Blueprint\n\n"
            f"- Gate status: {gate['status']}\n"
            f"- Failed checks: {', '.join(gate.get('failed_checks') or []) or 'none'}\n\n"
            "## Next Repair Targets\n"
            f"{_md_list(gate.get('failed_checks') or ['No blocking repair target.'])}"
        ),
        "proof/ELITE_DELIVERY_CERT.md": (
            "# Elite Delivery Certificate\n\n"
            f"- Status: {gate['status']}\n"
            f"- Export allowed: {gate['allowed']}\n"
            f"- Completion blocked: {gate['blocks_completion']}\n"
            f"- Build passed: {build_passed}\n"
            f"- API alignment passed: {api_alignment.get('passed')}\n\n"
            "Never treat this certificate as an external compliance certification."
        ),
    }
    documents.update(_research_docs(goal, contract))
    documents.update(_compliance_docs(contract))

    if repair_result is not None:
        proof_files.append("proof/REPAIR_LOG.md")
        documents["proof/REPAIR_LOG.md"] = (
            "# Repair Log\n\n"
            f"- Repair passed: {bool(repair_result.get('passed'))}\n"
            f"- Re-verify passed: {bool((repair_result.get('re_verify') or {}).get('passed'))}\n"
            f"- Repair iterations: {((repair_result.get('repair_result') or {}).get('iterations'))}"
        )

    for rel, content in documents.items():
        _safe_write(root / rel, content)

    proof_index = _proof_index_payload(proof_files, gate)
    _safe_write(proof_dir / "proof_index.json", json.dumps(proof_index, indent=2, sort_keys=True))
    _safe_write(meta_dir / "enterprise_proof.json", json.dumps({
        "job_id": job_id,
        "generated_at": now,
        "manifest": manifest,
        "api_alignment": api_alignment,
        "classification": classification,
        "proof_files": proof_files,
    }, indent=2, sort_keys=True))
    _safe_write(meta_dir / "delivery_gate.json", json.dumps(gate, indent=2, sort_keys=True))

    return {
        "contract": contract,
        "contract_result": contract_result,
        "api_alignment": api_alignment,
        "classification": classification,
        "delivery_gate": gate,
        "proof_files": proof_files,
        "manifest": manifest,
    }
