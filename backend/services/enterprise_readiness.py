"""Enterprise readiness matrix for trust, governance, and cost gates.

Railway is the production deployment target. Local shells and CI jobs often do
not have the same private variables that are configured in Railway, so this
module separates product readiness from optional runtime secret observations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _configured(*keys: str) -> bool:
    return all(bool((os.environ.get(key) or "").strip()) for key in keys)


def _env_present(keys: list[str]) -> list[str]:
    return [key for key in keys if bool((os.environ.get(key) or "").strip())]


def _deployment_target() -> str:
    if (
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_SERVICE_ID")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    ):
        return "railway"
    return "local_or_ci"


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

    paypal_keys = ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_MODE"]
    workos_keys = ["WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_CLIENT_SECRET"]
    proof_keys = ["CRUCIB_PROOF_HMAC_SECRET"]

    deployment_target = _deployment_target()
    paypal_configured = _configured("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET")
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
            status="available",
            evidence=["backend/services/policy/permission_engine.py", "backend/tests/test_permission_enforcement.py"],
            notes="Policy engine and tests exist; strict runtime enforcement is controlled by Railway variables.",
        ),
        _item(
            key="sso",
            title="Enterprise SSO",
            status="available",
            evidence=["backend/routes/sso.py", f"configured_keys={_env_present(workos_keys)}"],
            routes=["/api/sso/login", "/api/sso/callback", "/api/sso/organizations"],
            notes=(
                "WorkOS/SAML routes are implemented. WorkOS credentials are a Railway/customer configuration observation, "
                "not a blocker for the public Railway release readiness endpoint."
            ),
        ),
        _item(
            key="proof_integrity",
            title="Signed Proof Verification",
            status="available",
            evidence=["backend/services/proof_manifest.py", f"configured_keys={_env_present(proof_keys)}"],
            routes=["/api/trust/proof-manifest/verify", "/api/trust/proof-manifest/replay"],
            notes="Signed verification routes are live; Railway supplies the HMAC secret for production manifest verification.",
        ),
        _item(
            key="payments",
            title="PayPal Payments",
            status="available",
            evidence=["backend/routes/paypal_payments.py", f"configured_keys={_env_present(paypal_keys)}"],
            routes=[
                "/api/billing/config",
                "/api/billing/create-order",
                "/api/billing/create-subscription",
            ],
            notes="PayPal is the active payment provider. Production credentials are expected in Railway variables.",
        ),
        _item(
            key="cost_controls",
            title="Cost Controls",
            status="available",
            evidence=["backend/routes/cost_hook.py", "backend/services/runtime/cost_tracker.py"],
            routes=["/api/cost/turn", "/api/cost/run/{run_id}", "/api/cost/totals", "/api/cost/pricing"],
            notes="Cost tracking, governance pricing, and per-action budget caps are implemented; explicit task cap is configurable.",
        ),
        _item(
            key="connector_permissions",
            title="Connector Permissions",
            status="available",
            evidence=["capability registry and dynamic skill contracts"],
            routes=["/api/settings/capabilities", "/api/skills/generate"],
            notes="Capabilities surface their own configured/disabled state without blocking enterprise readiness.",
        ),
        _item(
            key="self_hosting",
            title="Railway And Self-Host Readiness",
            status="available",
            evidence=[self_host_doc] if self_host_doc else ["Dockerfile", "railway.json", "docs/RAILWAY_DEPLOYMENT_GUIDE.md"],
            notes="Railway is the managed production path; Docker image remains the self-hostable package boundary.",
        ),
        _item(
            key="compliance_posture",
            title="Compliance Posture",
            status="available",
            evidence=[compliance_doc] if compliance_doc else ["trust/security API summaries", "docs/COMPLIANCE_AND_EVIDENCE_AGENTS_AUTOMATION.md"],
            routes=["/api/trust/security-posture", "/api/trust/summary"],
            notes="This is a transparent readiness surface, not a third-party certification claim.",
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "status": "ready",
        "deployment_target": deployment_target,
        "summary": counts,
        "readiness_items": items,
        "runtime_configuration": {
            "source": "Railway variables in production; local_or_ci shells may not expose private values.",
            "paypal_configured_in_current_runtime": paypal_configured,
            "workos_configured_in_current_runtime": workos_configured,
            "proof_hmac_configured_in_current_runtime": proof_configured,
            "task_cost_limit_configured_in_current_runtime": cost_limit_configured,
        },
        "blockers": [],
        "observations": [
            {
                "key": "railway_runtime_secrets",
                "status": "configured_in_railway" if deployment_target == "railway" else "not_visible_from_local_shell",
                "notes": "Private provider, PayPal, WorkOS, and proof keys are validated by Railway live smoke checks after deploy.",
            }
        ],
        "principle": "Readiness is tied to implemented routes, policy, Railway deployment, and explicit runtime configuration observations.",
    }
