"""
Spec Guardian — compares user goal text to what the Auto-Runner can actually emit.

Modes (CRUCIBAI_SPEC_GUARD_MODE):
- off:     no violations recorded (not recommended)
- advisory: violations + compliance %; run always allowed
- strict:  stack / tenancy / infra claims that the template cannot satisfy → blocks run (default)

This is Layer 1 "spec enforcement" — honest gatekeeping, not magic codegen.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .multiregion_terraform_sketch import multiregion_terraform_intent


RUNNER_TRUTH = (
    "CrucibAI Auto-Runner emits a fixed scaffold: Vite + React (JS), Python FastAPI sketch, "
    "SQL migration/seed files, template auth/store, verification gates. "
    "For multitenant goals it emits PostgreSQL RLS on generated app_items (session GUC app.tenant_id) — "
    "not schema-per-tenant or custom table graphs. "
    "For observability keywords it adds deploy/observability stubs (OTel collector, Prometheus, Grafana) and docs. "
    "For multi-region + cloud + Terraform-style goals it adds terraform/multiregion_sketch and aws/gcp/azure region stubs — not production VPC/DR. "
    "It does not generate Next.js App Router, TypeScript Node services, Prisma/Drizzle projects, or BullMQ/Testcontainers/k6 harnesses from prompts."
)


def _mode() -> str:
    m = os.environ.get("CRUCIBAI_SPEC_GUARD_MODE", "strict").strip().lower()
    if m in ("off", "advisory", "strict"):
        return m
    return "strict"


def evaluate_goal_against_runner(goal: str) -> Dict[str, Any]:
    """
    Returns violations (with severity), compliance score, and whether run must be blocked in strict mode.
    """
    if _mode() == "off":
        return {
            "schema": "crucibai.spec_guard/v1",
            "mode": "off",
            "runner_truth": RUNNER_TRUTH,
            "violations": [],
            "spec_compliance_percent": 100.0,
            "blocks_run": False,
            "block_reasons": [],
        }

    g = (goal or "").lower()
    violations: List[Dict[str, Any]] = []

    def add(code: str, message: str, remediation: str, *, strict_blocker: bool) -> None:
        sev = "blocker" if strict_blocker and _mode() == "strict" else "warning"
        violations.append(
            {
                "code": code,
                "severity": sev,
                "message": message,
                "remediation": remediation,
            }
        )

    # Stack mismatches (always warnings in advisory; blockers in strict)
    if any(k in g for k in ("next.js", "nextjs", "app router", "next-auth", "nextauth")):
        add(
            "stack_nextjs_requested",
            "Goal requests Next.js / NextAuth — runner template is Vite + React.",
            "Use this scaffold as UI shell or narrow the goal; full Next.js codegen is not in this pipeline.",
            strict_blocker=True,
        )
    if ("typescript" in g or " typeScript" in (goal or "")) and any(
        x in g for x in ("fastify", "nestjs", "express", "node api", "openapi 3")
    ):
        add(
            "stack_ts_backend_requested",
            "Goal requests a TypeScript Node API — runner emits Python FastAPI sketch only.",
            "Port manually or extend runner with a TS stack pack (future).",
            strict_blocker=True,
        )
    if "prisma" in g or "drizzle" in g:
        add(
            "orm_requested",
            "Goal requests Prisma/Drizzle — runner writes plain SQL files only.",
            "Add ORM in a follow-up project or custom pack.",
            strict_blocker=True,
        )
    if any(
        k in g
        for k in (
            "typeorm",
            "sequelize",
            "mongoose",
            "objection.js",
            "objectionjs",
            "waterline",
            "bookshelf.js",
        )
    ):
        add(
            "orm_js_requested",
            "Goal requests a JS/TS ORM stack — runner emits Python + plain SQL only.",
            "Use the generated SQL sketch or add a custom ORM pack.",
            strict_blocker=True,
        )

    # Enterprise / tenancy — template RLS is single-table; schema-per-tenant is not automated
    if "schema per tenant" in g or "schema-per-tenant" in g:
        add(
            "tenancy_schema_per_tenant",
            "Goal requests schema-per-tenant isolation — runner uses shared-schema tenant_id + RLS on app_items only.",
            "Add per-tenant schemas or databases outside this template.",
            strict_blocker=True,
        )
    if any(
        k in g
        for k in (
            "row-level security",
            "rls",
            "multi-tenant",
            "multitenant",
            "tenant isolation",
        )
    ):
        add(
            "tenancy_template_scope",
            "Goal mentions tenancy/RLS — runner emits db/migrations/002_multitenancy_rls.sql (RLS on app_items via app.tenant_id).",
            "Extend policies to your other tables and wire set_config from the API; run integration tests in CI.",
            strict_blocker=False,
        )

    if multiregion_terraform_intent(goal or ""):
        add(
            "multiregion_terraform_sketch_emitted",
            "Goal matches multi-region / Terraform + cloud — runner adds terraform/multiregion_sketch and module stubs on deploy.build.",
            "Configure remote state, IAM, networking, data replication, and DNS before any apply.",
            strict_blocker=False,
        )
    elif any(
        k in g
        for k in (
            "terraform",
            "aws ecs",
            "fargate",
            "elasticache",
            "route53",
        )
    ):
        add(
            "infra_depth_beyond_template",
            "Goal names Terraform or AWS services without the multi-region sketch trigger — full ECS/ElastiCache/Route53 modules are not auto-generated.",
            "Narrow the goal to include multi-region + cloud keywords for terraform stubs, or author infra separately.",
            strict_blocker=False,
        )

    if any(k in g for k in ("bullmq", "testcontainers", "k6")):
        add(
            "queues_or_load_harness_not_in_template",
            "Goal requests BullMQ, Testcontainers, or k6 — not emitted by this Auto-Runner scaffold.",
            "Add worker processes and load tests in a separate repo or phase.",
            strict_blocker=False,
        )

    if any(
        k in g
        for k in (
            "opentelemetry",
            "open telemetry",
            "otel",
            "prometheus",
            "grafana",
            "structured log",
            "json log",
            "distributed trace",
            "tracing",
            "metrics",
            "observability",
        )
    ):
        add(
            "observability_pack_scope",
            "Goal mentions observability — runner adds deploy/observability/* stubs + docs/OBSERVABILITY_PACK.md on deploy.build.",
            "Configure OTLP endpoints, Prometheus scrape targets, and Grafana dashboards for your stack.",
            strict_blocker=False,
        )

    if any(k in g for k in ("datadog", "new relic", "honeycomb")):
        add(
            "observability_vendor_saas",
            "Vendor APM named — stubs target OpenTelemetry + Prometheus/Grafana; install vendor agents or exporters separately.",
            "See vendor docs for FastAPI/Python instrumentation.",
            strict_blocker=False,
        )

    if "mfa" in g or "totp" in g or "auth.js" in g:
        add(
            "auth_depth_mismatch",
            "Goal mentions MFA / Auth.js depth — runner provides client-demo auth pattern only.",
            "Harden auth before production.",
            strict_blocker=False,
        )

    if "idempotent" in g and "stripe" in g:
        add(
            "stripe_production_depth",
            "Goal requires production-grade Stripe idempotency — runner adds route stubs only.",
            "Implement webhook dedupe table and signature verification before live charges.",
            strict_blocker=False,
        )

    n = len(violations)
    # Compliance: start at 100, subtract per violation (cap 0)
    spec_compliance = max(0.0, round(100.0 - min(100.0, n * 15.0 + sum(5 for v in violations if v["severity"] == "blocker")), 1))

    blockers = [v for v in violations if v["severity"] == "blocker"]
    blocks_run = _mode() == "strict" and len(blockers) > 0

    return {
        "schema": "crucibai.spec_guard/v1",
        "mode": _mode(),
        "runner_truth": RUNNER_TRUTH,
        "violations": violations,
        "spec_compliance_percent": spec_compliance,
        "blocks_run": blocks_run,
        "block_reasons": [b["message"] for b in blockers],
    }


def merge_plan_risk_flags_into_report(plan_risk_flags: List[str], base: Dict[str, Any]) -> Dict[str, Any]:
    """If planner already tagged mismatch flags, reflect them as violations if missing."""
    out = dict(base)
    flag_to_violation = {
        "goal_spec_nextjs_autorunner_template_is_vite_react": (
            "stack_nextjs_requested",
            "Planner: goal specifies Next.js; template is Vite + React.",
        ),
        "goal_spec_ts_node_api_autorunner_backend_is_python_sketch": (
            "stack_ts_backend_requested",
            "Planner: goal specifies TS Node API; template is Python sketch.",
        ),
        "goal_spec_orm_autorunner_writes_sql_sketch_not_orm": (
            "orm_requested",
            "Planner: goal specifies ORM; template emits SQL files only.",
        ),
        "goal_spec_infra_or_tenancy_not_generated_by_autorunner": (
            "tenancy_or_infra_requested",
            "Planner: goal mentions infra/tenancy beyond runner scope.",
        ),
    }
    seen_codes = {v["code"] for v in out.get("violations") or []}
    for rf in plan_risk_flags or []:
        if rf not in flag_to_violation:
            continue
        code, msg = flag_to_violation[rf]
        if code in seen_codes:
            continue
        strict_blocker = _mode() == "strict" and code in (
            "stack_nextjs_requested",
            "stack_ts_backend_requested",
            "orm_requested",
            "tenancy_or_infra_requested",
        )
        sev = "blocker" if strict_blocker else "warning"
        out["violations"] = list(out.get("violations") or [])
        out["violations"].append(
            {
                "code": code,
                "severity": sev,
                "message": msg,
                "remediation": "See runner_truth or narrow goal.",
            }
        )
        seen_codes.add(code)
    n = len(out["violations"])
    out["spec_compliance_percent"] = max(
        0.0,
        round(100.0 - min(100.0, n * 15.0), 1),
    )
    blockers = [v for v in out["violations"] if v["severity"] == "blocker"]
    out["blocks_run"] = _mode() == "strict" and len(blockers) > 0
    out["block_reasons"] = [b["message"] for b in blockers]
    return out
