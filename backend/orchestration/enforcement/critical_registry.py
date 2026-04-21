"""
Central registry of critical software features and the proof they require.

Each row is active when `in_scope(...)` matches the job goal, parsed claims, or bundle shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

CRITICAL_REGISTRY_VERSION = "1.0.0"


@dataclass(frozen=True)
class CriticalFeature:
    id: str
    name: str
    goal_keywords: Tuple[str, ...] = ()
    """Lowercase substrings; any match activates scope from goal text."""
    claim_regex_ids: Tuple[str, ...] = ()
    """Keys into claim_parser.CLAIM_PATTERNS that also activate scope."""
    required_proof_classes: Tuple[str, ...] = (
        "runtime",
        "behavior_assertion",
    )
    """Minimum proof *types* that should appear in the bundle for a pass (see proof_hierarchy)."""
    allow_presence_only: bool = False
    allow_skipped: bool = False
    must_have_negative_test: bool = False
    must_have_runtime_execution: bool = True
    block_if_stubbed: bool = True
    block_if_mocked_but_claimed_real: bool = True
    # payload `check` values that satisfy runtime/behavior for this feature
    satisfying_checks: Tuple[str, ...] = ()
    negative_checks: Tuple[str, ...] = ()
    # When this skip check appears in flat proof, feature is treated as skipped test path
    skip_signal_checks: Tuple[str, ...] = ()
    # Substrings in flat item title (lower) that count as weak presence-only hooks
    presence_hint_substrings: Tuple[str, ...] = ()


CRITICAL_FEATURES: Tuple[CriticalFeature, ...] = (
    CriticalFeature(
        id="auth",
        name="Authentication",
        goal_keywords=(
            "auth",
            "jwt",
            "oauth",
            "login",
            "session",
            "sign in",
            "signin",
            "bearer",
        ),
        claim_regex_ids=("secure_auth", "production_ready"),
        satisfying_checks=("rbac_anonymous_blocked", "rbac_escalation_blocked"),
        negative_checks=("rbac_anonymous_blocked", "invalid_token", "unauthorized"),
        skip_signal_checks=("rbac_smoke_skipped",),
        presence_hint_substrings=("auth", "jwt", "login", "token", "session"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="rbac",
        name="Role-based access control",
        goal_keywords=("rbac", "role", "permission", "admin", "privilege"),
        claim_regex_ids=("policy_enforced",),
        satisfying_checks=("rbac_escalation_blocked", "rbac_anonymous_blocked"),
        negative_checks=("rbac_escalation_blocked", "rbac_anonymous_blocked"),
        skip_signal_checks=("rbac_smoke_skipped",),
        presence_hint_substrings=("rbac", "role", "admin"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="tenant_isolation",
        name="Tenant isolation",
        goal_keywords=(
            "tenant",
            "multi-tenant",
            "multitenant",
            "rls",
            "row-level",
            "org isolation",
        ),
        claim_regex_ids=("tenant_safe", "production_ready"),
        satisfying_checks=("tenancy_isolation_proven",),
        negative_checks=("tenancy_isolation_proven",),
        skip_signal_checks=("tenancy_smoke_skipped",),
        presence_hint_substrings=("tenant", "rls", "isolation"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="core_api_behavior",
        name="Core API behavior",
        goal_keywords=("api", "rest", "fastapi", "backend", "endpoint", "graphql"),
        claim_regex_ids=("deployment_ready",),
        satisfying_checks=("health_endpoint", "health_path_literal"),
        negative_checks=(),
        skip_signal_checks=(),
        presence_hint_substrings=("route", "endpoint", "api", "health"),
        must_have_negative_test=False,
        must_have_runtime_execution=True,
    ),
    CriticalFeature(
        id="approval_boundary",
        name="Approval / workflow boundary",
        goal_keywords=(
            "approval",
            "sign-off",
            "signoff",
            "workflow gate",
            "maker checker",
        ),
        claim_regex_ids=("policy_enforced",),
        satisfying_checks=("approval", "workflow", "forbidden"),
        negative_checks=("approval_denied", "forbidden_before_approval", "403"),
        skip_signal_checks=(),
        presence_hint_substrings=("approval", "workflow"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="state_machine_logic",
        name="State machine / lifecycle",
        goal_keywords=(
            "state machine",
            "statemachine",
            "lifecycle",
            "status transition",
            "workflow state",
        ),
        claim_regex_ids=(),
        satisfying_checks=("state_transition", "transition", "invalid_transition"),
        negative_checks=(
            "invalid_transition",
            "illegal_transition",
            "duplicate_terminal",
        ),
        skip_signal_checks=(),
        presence_hint_substrings=("state", "transition"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="integration_behavior",
        name="External integration",
        goal_keywords=(
            "stripe",
            "webhook",
            "payment",
            "twilio",
            "sendgrid",
            "oauth provider",
            "third-party",
        ),
        claim_regex_ids=("integration_complete", "production_ready"),
        satisfying_checks=(
            "stripe_webhook_idempotency_proven",
            "webhook",
            "integration",
        ),
        negative_checks=("stripe_webhook_idempotency_proven", "provider_error"),
        skip_signal_checks=("stripe_replay_skipped",),
        presence_hint_substrings=("stripe", "webhook", "integration"),
        must_have_negative_test=False,
    ),
    CriticalFeature(
        id="async_jobs",
        name="Async jobs / workers",
        goal_keywords=(
            "celery",
            "rq",
            "sidekiq",
            "bullmq",
            "queue",
            "background job",
            "worker",
            "async job",
        ),
        claim_regex_ids=("deployment_ready",),
        satisfying_checks=("job", "worker", "duplicate", "retry"),
        negative_checks=("duplicate_terminal", "job_idempotency"),
        skip_signal_checks=(),
        presence_hint_substrings=("worker", "queue", "job"),
        must_have_negative_test=True,
    ),
    CriticalFeature(
        id="security_controls",
        name="Security controls",
        goal_keywords=(
            "encrypt",
            "csrf",
            "xss",
            "cipher",
            "aes",
            "security audit",
            "pen test",
        ),
        claim_regex_ids=("secure_auth",),
        satisfying_checks=("npm_audit", "security", "rls_syntax_valid"),
        negative_checks=(),
        skip_signal_checks=(),
        presence_hint_substrings=("security", "encrypt"),
        must_have_negative_test=False,
    ),
    CriticalFeature(
        id="analytics_truth",
        name="Analytics / telemetry truth",
        goal_keywords=(
            "analytics",
            "amplitude",
            "mixpanel",
            "segment",
            "telemetry",
            "metrics pipeline",
        ),
        claim_regex_ids=(),
        satisfying_checks=("analytics", "telemetry", "event"),
        negative_checks=(),
        skip_signal_checks=(),
        presence_hint_substrings=("analytics", "telemetry"),
        must_have_negative_test=False,
    ),
)


def feature_in_scope(
    feat: CriticalFeature,
    goal_lower: str,
    active_claim_ids: Sequence[str],
    bundle: Dict[str, List],
) -> bool:
    if any(k in goal_lower for k in feat.goal_keywords):
        return True
    if any(cid in active_claim_ids for cid in feat.claim_regex_ids):
        return True
    # API surface implied by many declared routes
    if feat.id == "core_api_behavior":
        routes = bundle.get("routes") or []
        if len(routes) >= 4 and any(
            x in goal_lower for x in ("app", "saas", "service", "platform")
        ):
            return True
    return False


def matching_features(
    goal: str,
    active_claim_ids: Sequence[str],
    bundle: Dict[str, List],
) -> List[CriticalFeature]:
    g = (goal or "").lower()
    return [
        f for f in CRITICAL_FEATURES if feature_in_scope(f, g, active_claim_ids, bundle)
    ]
