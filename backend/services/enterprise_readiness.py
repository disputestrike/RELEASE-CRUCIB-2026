"""Enterprise readiness matrix for trust, governance, and cost gates.

This module is intentionally environment-aware and non-invasive: it reports
what is live, what is foundation-only, and what still requires configuration.
It does not make readiness claims by implication.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _configured(*keys: str) -> bool:
    return all(bool((os.environ.get(key) or "").strip()) for key in keys)


def _env_present(keys: list[str]) -> list[str]:
    return [key for key in keys if bool((os.environ.get(key) or "").strip())]


def _first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists():
            return str(path)
    return None


def _item(
    *,
    key: str,
    title: str,
    status: str,
    evidence: list[str],
    required_config: list[str] | None = None,
    routes: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "status": status,
        "evidence": evidence,
        "required_config": required_config or [],
        "routes": routes or [],
        "notes": notes,
    }


def build_enterprise_readiness(root_dir: Path) -> dict[str, Any]:
    """Return the buyer-facing enterprise/cost readiness contract."""
    repo_root = root_dir.parent
    self_host_doc = _first_existing(
        [
            repo_root / "docs" / "SELF_HOSTING.md",
            repo_root / "docs" / "ENTERPRISE_SELF_HOSTING.md",
            repo_root / "docs" / "enterprise" / "SELF_HOSTING.md",
        ]
    )
    compliance_doc = _first_existing(
        [
            repo_root / "docs" / "SECURITY_AND_TRUST.md",
            repo_root / "docs" / "ENTERPRISE_TRUST.md",
            repo_root / "docs" / "SECURITY.md",
        ]
    )

    braintree_keys = [
        "BRAINTREE_MERCHANT_ID",
        "BRAINTREE_PUBLIC_KEY",
        "BRAINTREE_PRIVATE_KEY",
        "BRAINTREE_ENVIRONMENT",
    ]
    workos_keys = ["WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_CLIENT_SECRET"]
    proof_keys = ["CRUCIB_PROOF_HMAC_SECRET"]

    braintree_configured = _configured(
        "BRAINTREE_MERCHANT_ID",
        "BRAINTREE_PUBLIC_KEY",
        "BRAINTREE_PRIVATE_KEY",
    )
    workos_configured = _configured("WORKOS_API_KEY", "WORKOS_CLIENT_ID")
    proof_configured = _configured("CRUCIB_PROOF_HMAC_SECRET")
    cost_limit_configured = bool((os.environ.get("CRUCIB_TASK_COST_LIMIT") or "").strip())

    items = [
        _item(
            key="auth",
            title="Authentication",
            status="available",
            evidence=["JWT auth routes, guest auth, Google OAuth configuration, protected API dependencies"],
            routes=["/api/auth/me", "/api/auth/guest", "/api/auth/google/login"],
            notes="Core authentication is active; provider availability depends on configured OAuth credentials.",
        ),
        _item(
            key="audit_logs",
            title="Audit Logs",
            status="available",
            evidence=["backend/services/audit_log_service.py", "audit export services"],
            routes=["/api/audit/logs", "/api/audit/export"],
            notes="Audit service exists and returns empty/readiness-safe output when logger storage is unavailable.",
        ),
        _item(
            key="rbac_permissions",
            title="RBAC And Tool Policy",
            status="foundation",
            evidence=["backend/services/policy/permission_engine.py", "backend/tests/test_permission_enforcement.py"],
            required_config=["CRUCIB_ENABLE_TOOL_POLICY for strict runtime tool enforcement"],
            notes="Policy engine and tests exist; production strictness is controlled by environment flags and role wiring.",
        ),
        _item(
            key="sso",
            title="Enterprise SSO",
            status="available" if workos_configured else "requires_config",
            evidence=["backend/routes/sso.py", f"configured_keys={_env_present(workos_keys)}"],
            required_config=[] if workos_configured else workos_keys,
            routes=["/api/sso/login", "/api/sso/callback", "/api/sso/organizations"],
            notes="WorkOS/SAML routes are implemented. They intentionally return SSO_NOT_CONFIGURED until credentials are present.",
        ),
        _item(
            key="proof_integrity",
            title="Signed Proof Verification",
            status="available" if proof_configured else "requires_config",
            evidence=["backend/services/proof_manifest.py", f"configured_keys={_env_present(proof_keys)}"],
            required_config=[] if proof_configured else proof_keys,
            routes=["/api/trust/proof-manifest/verify", "/api/trust/proof-manifest/replay"],
            notes="Proof HMAC must be configured before public proof verification can accept signed manifests.",
        ),
        _item(
            key="payments",
            title="Braintree Payments",
            status="available" if braintree_configured else "requires_config",
            evidence=["backend/routes/braintree_payments.py", f"configured_keys={_env_present(braintree_keys)}"],
            required_config=[] if braintree_configured else braintree_keys,
            routes=[
                "/api/payments/braintree/status",
                "/api/payments/braintree/client-token",
                "/api/payments/braintree/checkout",
            ],
            notes="Stripe is not the active payment provider. Checkout requires Braintree credentials and DB availability.",
        ),
        _item(
            key="cost_controls",
            title="Cost Controls",
            status="available" if cost_limit_configured else "foundation",
            evidence=["backend/routes/cost_hook.py", "backend/services/runtime/cost_tracker.py"],
            required_config=[] if cost_limit_configured else ["CRUCIB_TASK_COST_LIMIT for explicit per-task cap"],
            routes=["/api/cost/turn", "/api/cost/run/{run_id}", "/api/cost/totals", "/api/cost/pricing"],
            notes="In-process cost tracking and per-task cap checks exist; durable billing ledger is separate from runtime spend tracking.",
        ),
        _item(
            key="connector_permissions",
            title="Connector Permissions",
            status="foundation",
            evidence=["capability registry and dynamic skill contracts"],
            required_config=["connector OAuth apps and credential storage for Gmail, Calendar, Notion, computer-use runner"],
            routes=["/api/settings/capabilities", "/api/skills/generate"],
            notes="Capabilities are shown honestly as available, requires_config, disabled, or coming_soon.",
        ),
        _item(
            key="self_hosting",
            title="Self-Host And VPC Readiness",
            status="available" if self_host_doc else "foundation",
            evidence=[self_host_doc] if self_host_doc else ["Docker/Railway deployment path exists; dedicated self-host document not found"],
            required_config=[] if self_host_doc else ["self-host/VPC deployment guide"],
            notes="Enterprise buyers need this surfaced as an explicit deployment package before 10/10.",
        ),
        _item(
            key="compliance_posture",
            title="Compliance Posture",
            status="available" if compliance_doc else "foundation",
            evidence=[compliance_doc] if compliance_doc else ["trust/security API summaries exist; dedicated compliance document not found"],
            required_config=[] if compliance_doc else ["security and compliance posture page"],
            routes=["/api/trust/security-posture", "/api/trust/summary"],
            notes="This is not a certification claim; it is a transparent readiness surface.",
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    blockers = [
        item
        for item in items
        if item["status"] in {"requires_config", "disabled", "coming_soon"}
    ]
    return {
        "status": "ready" if not blockers else "partial",
        "summary": counts,
        "readiness_items": items,
        "blockers": [
            {
                "key": item["key"],
                "title": item["title"],
                "status": item["status"],
                "required_config": item["required_config"],
            }
            for item in blockers
        ],
        "principle": "No enterprise, payment, connector, or proof claim is marked live unless its runtime configuration is present.",
    }
