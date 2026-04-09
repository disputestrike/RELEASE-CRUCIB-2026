"""
planner.py — Structured build planner for CrucibAI.
Produces a normalized plan JSON before any execution starts.

Pre-launch checklist policy (missing_inputs):
- Every item is advisory: blocking is always False. Users run and test in dev with mocks;
  they wire real keys/services before production. Optional strict mode: set
  CRUCIBAI_STRICT_PLAN_BLOCKERS=1 to allow blocking=True on individual items (future use).
"""
import logging
import json
import os
import re
from typing import Dict, Any, Optional

from pricing_plans import CREDIT_PLANS

from .trust.node_manifest import enrich_plan_with_node_manifests
from .multiregion_terraform_sketch import multiregion_terraform_intent
from .observability_workspace_pack import observability_intent as observability_goal_intent
from .generation_contract import parse_generation_contract
from .agent_selection_logic import explain_agent_selection, should_route_to_agent_selection
from .spec_guardian import evaluate_goal_against_runner, merge_plan_risk_flags_into_report
from .swarm_agent_runner import build_agent_swarm_phases, uses_agent_swarm
from .controller_brain import build_plan_controller_summary

logger = logging.getLogger(__name__)

_STRICT_PLAN_BLOCKERS = os.environ.get("CRUCIBAI_STRICT_PLAN_BLOCKERS", "").strip().lower() in (
    "1", "true", "yes",
)


def _advisory_missing(key: str, description: str, *, blocking: bool = False) -> Dict[str, Any]:
    """Single checklist row; blocking only honored when CRUCIBAI_STRICT_PLAN_BLOCKERS is set."""
    b = bool(blocking) and _STRICT_PLAN_BLOCKERS
    return {"key": key, "description": description, "blocking": b}


# ── Canonical plan schema ─────────────────────────────────────────────────────

def empty_plan(goal: str) -> Dict[str, Any]:
    return {
        "goal": goal,
        "build_kind": "fullstack",
        "phases": [],
        "dependencies": [],
        "acceptance_criteria": [],
        "required_integrations": [],
        "risk_flags": [],
        "estimated_steps": 0,
        "missing_inputs": [],
    }


# ── Intent detection helpers ──────────────────────────────────────────────────

def _detect_build_kind(goal: str) -> str:
    g = goal.lower()
    if any(k in g for k in ["mobile", "ios", "android", "expo", "react native"]):
        return "mobile"
    if any(k in g for k in ["automate", "cron", "scheduler", "workflow", "pipeline"]):
        return "automation"
    if any(k in g for k in ["landing", "portfolio", "marketing", "site"]):
        return "frontend"
    return "fullstack"


def _detect_integrations(goal: str) -> list:
    """Word-boundary matching avoids substring false positives (e.g. 'payment' in unrelated words)."""
    g = goal.lower()
    integrations = []
    if re.search(r"\b(stripe|payments?|billing|checkout)\b", g):
        integrations.append("stripe")
    if re.search(r"\b(auth|authentication|login|sign[\s-]?up|oauth|jwt)\b", g):
        integrations.append("auth")
    if re.search(r"\b(database|postgres|postgresql|mysql|mongodb|sqlite|storage)\b", g):
        integrations.append("database")
    if re.search(r"\b(email|smtp|notification|notify)\b", g):
        integrations.append("email")
    if re.search(r"\b(llm|gpt|openai|claude|cerebras|anthropic)\b", g) or re.search(r"\bai\b", g):
        integrations.append("llm")
    if re.search(
        r"\b(multi[\s-]?tenant|multitenant|tenant isolation|row[\s-]?level|rls)\b",
        g,
    ):
        integrations.append("multi_tenant")
    if re.search(
        r"\b(fintech|pci[\s-]?dss|pci\b|hipaa|soc\s*2|soc2|gdpr|glba|"
        r"regulated|financial services|healthcare|phi\b|banking|lending|insurtech)\b",
        g,
    ):
        integrations.append("compliance_sensitive")
    if observability_goal_intent(goal):
        integrations.append("observability")
    if multiregion_terraform_intent(goal):
        integrations.append("multiregion_terraform")
    return integrations


# Free-tier default credits (see server.GUEST_TIER_CREDITS); above this implies purchase/top-up/referral.
_FREE_BUCKET_MAX_CREDITS = int(CREDIT_PLANS.get("free", {}).get("credits") or 200)
_PAID_PLANS = frozenset(k for k in CREDIT_PLANS if k != "free")
# Free users with only the default allowance: still allow long specs; warn only on extreme payloads (DoS-ish).
_FREE_USER_GOAL_LEN_ADVISORY = 24_000


def _goal_len_advisory_threshold(project_state: Optional[Dict]) -> Optional[int]:
    """
    Max goal length (chars) before we add goal_too_long_consider_splitting.
    None = no length-based advisory (paid plan or user has topped-up credits).
    """
    billing = (project_state or {}).get("billing") or {}
    plan = (billing.get("plan") or "free").strip().lower()
    if plan in _PAID_PLANS:
        return None
    credits = int(billing.get("credits") or 0)
    if credits > _FREE_BUCKET_MAX_CREDITS:
        return None
    return _FREE_USER_GOAL_LEN_ADVISORY


def _detect_spec_vs_runner_template_mismatch(goal: str, use_agent_swarm: bool = False) -> list:
    """
    Auto-Runner always emits the same scaffold family (Vite + React + Python FastAPI sketch).
    Long enterprise specs often request a different stack — flag so UI/plan reviewers see the gap.
    """
    if use_agent_swarm:
        return []
    flags: list = []
    g = (goal or "").lower()
    if any(k in g for k in ("next.js", "nextjs", "next-auth", "nextauth", "auth.js v5", "app router")):
        flags.append("goal_spec_nextjs_autorunner_template_is_vite_react")
    if "typescript" in g and any(
        k in g for k in ("fastify", "nestjs", "express", "node backend", "rest + openapi")
    ):
        flags.append("goal_spec_ts_node_api_autorunner_backend_is_python_sketch")
    if any(k in g for k in ("prisma", "drizzle orm", "drizzle")):
        flags.append("goal_spec_orm_autorunner_writes_sql_sketch_not_orm")
    # Remaining gaps vs template (runner now emits RLS, multitenant SQL, CI workflow, observability stubs, TF sketches).
    if any(k in g for k in ("bullmq", "testcontainers", "k6")):
        flags.append("goal_spec_infra_or_tenancy_not_generated_by_autorunner")
    return flags


def _should_use_agent_selection(goal: str, stack_contract: Optional[Dict[str, Any]] = None) -> bool:
    """Route to selected-agent swarm when the selector sees any specialized need."""
    routed = should_route_to_agent_selection(goal, stack_contract)
    if routed:
        explanation = explain_agent_selection(goal, stack_contract)
        matched = (explanation.get("matched_keywords") or [])[:5]
        logger.info("Agent selection triggered by selector registry: %s", ", ".join(matched) or "specialized_rules")
        return True
    logger.info("Agent selection not triggered; using fixed_autorunner unless swarm markers apply")
    return False


def _uses_intelligent_orchestration(goal: str, stack_contract: Optional[Dict[str, Any]] = None) -> bool:
    return _should_use_agent_selection(goal, stack_contract) or uses_agent_swarm(goal, stack_contract)


def _detect_risk_flags(goal: str, project_state: Optional[Dict] = None,
                       stack_contract: Optional[Dict[str, Any]] = None) -> list:
    flags = []
    g = goal.lower()
    if "stripe" in g and not (project_state or {}).get("env_vars", {}).get("STRIPE_SECRET_KEY"):
        flags.append("stripe_keys_missing")
    if len(goal) < 20:
        flags.append("goal_too_vague")
    thresh = _goal_len_advisory_threshold(project_state)
    if thresh is not None and len(goal) > thresh:
        flags.append("goal_too_long_consider_splitting")
    flags.extend(_detect_spec_vs_runner_template_mismatch(goal, _uses_intelligent_orchestration(goal, stack_contract)))
    return flags


def _architecture_outline(build_kind: str, integrations: list,
                          stack_contract: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Pre-code architecture brain (honest template — not generated from LLM)."""
    ints = list(integrations or [])
    goal_for_selection = (stack_contract or {}).get("goal") or ""
    swarm_mode = _uses_intelligent_orchestration(goal_for_selection, stack_contract)
    data_notes = [
        "Demo items / user preferences (client storage + sketch API)",
    ]
    if "multi_tenant" in ints:
        data_notes.append(
            "Goal suggests tenancy — runner adds tenants + tenant_id + PostgreSQL RLS on app_items (app.tenant_id GUC); extend to other tables as needed",
        )
    else:
        data_notes.append("No automatic tenant_id / RLS unless goal triggers multi_tenant integration")
    if "compliance_sensitive" in ints:
        data_notes.append(
            "Regulated-domain keywords detected — deploy.build adds docs/COMPLIANCE_SKETCH.md (educational; not legal advice)",
        )
    if "observability" in ints:
        data_notes.append(
            "Observability keywords — deploy.build adds deploy/observability/* stubs + docs/OBSERVABILITY_PACK.md (OTel/Prometheus/Grafana)",
        )
    if "multiregion_terraform" in ints:
        data_notes.append(
            "Multi-region / cloud + Terraform keywords — deploy.build adds terraform/modules/{aws,gcp,azure}_region_stub + multiregion_sketch",
        )
    return {
        "data_model_intent": data_notes,
        "api_contract_intent": (
            "Multi-agent swarm emits API/backend artifacts across requested services."
            if swarm_mode
            else "REST JSON sketch under backend/main.py (health + sample routes)"
        ),
        "auth_flow_intent": (
            "Agent swarm should emit auth artifacts requested by the prompt; verify refresh/MFA/SSO explicitly."
            if swarm_mode
            else "AuthProvider + localStorage demo token; MFA / OIDC not generated"
        ),
        "tenancy": "multi_tenant_sketch" if "multi_tenant" in ints else "single_tenant_template",
        "billing_intent": "Stripe stubs + idempotency SQL sketch if stripe integration detected",
        "frontend_stack": (
            "agent_swarm_requested_stack"
            if swarm_mode
            else "vite_react_react_router_zustand"
        ),
        "backend_stack": (
            "agent_swarm_requested_stack"
            if swarm_mode
            else "python_fastapi_sketch"
        ),
        "build_kind": build_kind,
        "integrations_detected": list(integrations or []),
        "orchestration_mode": "agent_swarm" if swarm_mode else "fixed_autorunner",
    }


def _controller_summary(goal: str, selected_agents: list, phases: list) -> Dict[str, Any]:
    """Central controller metadata for the live planner output."""
    selection_explanation = explain_agent_selection(goal, {})
    return build_plan_controller_summary(
        goal=goal,
        phases=phases,
        selected_agents=selected_agents,
        selection_explanation=selection_explanation,
    )


# ── Phase builders ────────────────────────────────────────────────────────────

def _build_phases(goal: str, build_kind: str, integrations: list,
                  stack_contract: Optional[Dict[str, Any]] = None,
                  selected_agents: Optional[list] = None) -> list:
    if _uses_intelligent_orchestration(goal, stack_contract):
        logger.info("Routing to intelligent agent selection / swarm path")
        phases = build_agent_swarm_phases(goal, stack_contract, selected_agents=selected_agents)
        logger.info(
            "Generated %s phases from DAG for %s selected agents",
            len(phases),
            len(selected_agents or []),
        )
        phases.append(
            {
                "key": "implementation",
                "label": "Delivery manifest",
                "steps": [
                    {
                        "key": "implementation.delivery_manifest",
                        "agent": "Delivery",
                        "name": "Delivery classification",
                        "description": "Write proof/DELIVERY_CLASSIFICATION.md (Implemented/Mocked/Stubbed/Unverified)",
                    }
                ],
            }
        )
        phases.append(
            {
                "key": "verification",
                "label": "Verification",
                "steps": [
                    {
                        "key": "verification.compile",
                        "agent": "Verifier",
                        "name": "Compile check",
                        "description": "Verify generated workspace compiles cleanly",
                    },
                    {
                        "key": "verification.api_smoke",
                        "agent": "Verifier",
                        "name": "API smoke test",
                        "description": "Hit key endpoints, check responses",
                        "depends_on": ["verification.compile"],
                    },
                    {
                        "key": "verification.preview",
                        "agent": "Verifier",
                        "name": "Preview render check",
                        "description": "Confirm preview iframe loads",
                        "depends_on": ["verification.compile"],
                    },
                    {
                        "key": "verification.security",
                        "agent": "Security Checker",
                        "name": "Security scan",
                        "description": "Check CORS, auth headers, input validation",
                        "depends_on": ["verification.api_smoke"],
                    },
                    {
                        "key": "verification.elite_builder",
                        "agent": "Verifier",
                        "name": "Elite builder gate",
                        "description": "Delivery classifications, elite directive materialized, critical proof depth",
                        "depends_on": ["verification.api_smoke"],
                        "soft_depends_on": ["verification.preview", "verification.security"],
                    },
                ],
            }
        )
        phases.append(
            {
                "key": "deploy",
                "label": "Deploy",
                "steps": [
                    {
                        "key": "deploy.build",
                        "agent": "Deployment Agent",
                        "name": "Build artifacts",
                        "description": "Run production build after verification passes",
                        "depends_on": ["verification.elite_builder"],
                    },
                    {
                        "key": "deploy.publish",
                        "agent": "Deployment Agent",
                        "name": "Publish to target",
                        "description": "Deploy to Railway/Vercel/Netlify",
                        "depends_on": ["deploy.build"],
                    },
                ],
            }
        )
        return phases

    phases = [
        {
            "key": "planning",
            "label": "Planning",
            "steps": [
                {"key": "planning.analyze", "agent": "Planner", "name": "Analyze goal",
                 "description": "Parse goal, detect stack, identify required modules", "depends_on": []},
                {"key": "planning.requirements", "agent": "Requirements Clarifier",
                 "name": "Clarify requirements",
                 "description": "Produce acceptance criteria and required inputs", "depends_on": ["planning.analyze"]},
            ]
        },
        {
            "key": "frontend",
            "label": "Frontend",
            "steps": [
                {"key": "frontend.scaffold", "agent": "Frontend Generation",
                 "name": "Scaffold UI", "description": "Generate React component tree and pages",
                 "depends_on": ["planning.requirements"]},
                {"key": "frontend.styling", "agent": "Design Agent",
                 "name": "Apply styling", "description": "Apply design system, colors, typography",
                 "depends_on": ["frontend.scaffold"]},
                {"key": "frontend.routing", "agent": "Frontend Generation",
                 "name": "Wire routing", "description": "Add React Router routes",
                 "depends_on": ["frontend.scaffold"]},
            ]
        },
        {
            "key": "backend",
            "label": "Backend",
            "steps": [
                {"key": "backend.models", "agent": "Database Agent",
                 "name": "Define data models", "description": "Create DB schema and models",
                 "depends_on": ["planning.requirements"]},
                {"key": "backend.routes", "agent": "Backend Generation",
                 "name": "Generate API routes", "description": "Create FastAPI/Express route handlers",
                 "depends_on": ["backend.models"]},
                {"key": "backend.auth", "agent": "Auth Setup Agent",
                 "name": "Wire auth", "description": "JWT auth, protected routes, RBAC",
                 "depends_on": ["backend.routes"]},
            ]
        },
        {
            "key": "database",
            "label": "Database",
            "steps": [
                {"key": "database.migration", "agent": "Database Agent",
                 "name": "Create migration", "description": "Write and apply DB migration",
                 "depends_on": ["backend.models"]},
                {"key": "database.seed", "agent": "Database Agent",
                 "name": "Seed data", "description": "Insert initial/demo data",
                 "depends_on": ["database.migration"]},
            ]
        },
        {
            "key": "implementation",
            "label": "Delivery manifest",
            "steps": [
                {"key": "implementation.delivery_manifest", "agent": "Delivery",
                 "name": "Delivery classification",
                 "description": "Write proof/DELIVERY_CLASSIFICATION.md (Implemented/Mocked/Stubbed/Unverified)",
                 "depends_on": ["database.seed"]},
            ]
        },
        {
            "key": "verification",
            "label": "Verification",
            "steps": [
                {"key": "verification.compile", "agent": "Verifier",
                 "name": "Compile check", "description": "Verify frontend and backend compile cleanly",
                 "depends_on": ["frontend.routing", "backend.auth", "database.migration",
                                "implementation.delivery_manifest"]},
                {"key": "verification.api_smoke", "agent": "Verifier",
                 "name": "API smoke test", "description": "Hit key endpoints, check responses",
                 "depends_on": ["verification.compile"]},
                {"key": "verification.preview", "agent": "Verifier",
                 "name": "Preview render check", "description": "Confirm preview iframe loads",
                 "depends_on": ["verification.compile"]},
                {"key": "verification.security", "agent": "Security Checker",
                 "name": "Security scan", "description": "Check CORS, auth headers, input validation",
                 "depends_on": ["verification.api_smoke"]},
                {"key": "verification.elite_builder", "agent": "Verifier",
                 "name": "Elite builder gate",
                 "description": "Delivery classifications, elite directive materialized, critical proof depth",
                 "depends_on": ["verification.api_smoke"],
                 "soft_depends_on": ["verification.preview", "verification.security"]},
            ]
        },
        {
            "key": "deploy",
            "label": "Deploy",
            "steps": [
                {"key": "deploy.build", "agent": "Deployment Agent",
                 "name": "Build artifacts",
                 "description": "Run production build (after security + behavioral bundle in verifier)",
                 "depends_on": ["verification.elite_builder"]},
                {"key": "deploy.publish", "agent": "Deployment Agent",
                 "name": "Publish to target", "description": "Deploy to Vercel/Netlify/Railway",
                 "depends_on": ["deploy.build"]},
            ]
        },
    ]

    # Add Stripe steps if needed
    if "stripe" in integrations:
        phases[2]["steps"].append({
            "key": "backend.stripe", "agent": "Payment Setup Agent",
            "name": "Stripe integration", "description": "Checkout, webhooks, billing portal",
            "depends_on": ["backend.routes"]
        })

    return phases


# ── Main planner entry ────────────────────────────────────────────────────────

async def generate_plan(goal: str,
                        project_state: Optional[Dict] = None,
                        llm_call=None) -> Dict[str, Any]:
    """
    Generate a structured build plan for the given goal.
    llm_call: optional async callable(prompt) -> str for AI-enhanced planning.
    """
    stack_contract = parse_generation_contract(goal)
    stack_contract["goal"] = goal
    build_kind = _detect_build_kind(goal)
    integrations = _detect_integrations(goal)
    risk_flags = _detect_risk_flags(goal, project_state, stack_contract)
    selection_explanation = explain_agent_selection(goal, stack_contract) if _uses_intelligent_orchestration(goal, stack_contract) else {}
    selected_agents = list(selection_explanation.get("selected_agents") or [])
    phases = _build_phases(goal, build_kind, integrations, stack_contract, selected_agents)

    # Count total steps
    total_steps = sum(len(p["steps"]) for p in phases)

    # Pre-launch checklist (never blocks runs unless CRUCIBAI_STRICT_PLAN_BLOCKERS=1)
    missing_inputs: list = []
    env_vars = (project_state or {}).get("env_vars", {})

    if "stripe" in integrations and not env_vars.get("STRIPE_SECRET_KEY"):
        missing_inputs.append(
            _advisory_missing(
                "STRIPE_SECRET_KEY",
                "For live charges add to backend/.env; dev builds can use checkout mocks / placeholders.",
                blocking=True,
            )
        )

    if "email" in integrations and not env_vars.get("SMTP_HOST"):
        missing_inputs.append(
            _advisory_missing(
                "SMTP_HOST",
                "For real outbound email set SMTP_* in backend/.env; local runs can log or no-op.",
                blocking=True,
            )
        )

    if "llm" in integrations and not any(
        env_vars.get(k) for k in ("ANTHROPIC_API_KEY", "CEREBRAS_API_KEY", "LLAMA_API_KEY", "OPENAI_API_KEY")
    ):
        missing_inputs.append(
            _advisory_missing(
                "LLM_API_KEYS",
                "Set ANTHROPIC_API_KEY, CEREBRAS_API_KEY, and/or LLAMA_API_KEY for full AI steps; "
                "CRUCIBAI_DEV can use stubs when no keys are set.",
                blocking=True,
            )
        )

    if not _STRICT_PLAN_BLOCKERS:
        for row in missing_inputs:
            row["blocking"] = False

    # Acceptance criteria
    acceptance_criteria = [
        "All frontend pages load without errors",
        "All API routes return expected response shapes",
        "Database migrations applied successfully",
        "Authentication flow works end-to-end",
        "Preview iframe renders the application",
    ]
    if "stripe" in integrations:
        acceptance_criteria.append("Stripe checkout flow reachable")
    if "compliance_sensitive" in integrations:
        acceptance_criteria.append(
            "Regulated-domain sketch doc present (docs/COMPLIANCE_SKETCH.md) — review with counsel before production",
        )
    if "observability" in integrations:
        acceptance_criteria.append(
            "Observability stubs under deploy/observability — configure scrape targets, OTLP, and dashboards before production",
        )
    if "multiregion_terraform" in integrations:
        acceptance_criteria.append(
            "Terraform multi-region sketch under terraform/ — run terraform fmt/validate and extend for VPC, data replication, DNS",
        )
    if stack_contract.get("requires_full_system_builder"):
        acceptance_criteria.append(
            "Requested stack components are emitted as real files across application, services, tests, docs, and infrastructure.",
        )
    if _uses_intelligent_orchestration(goal, stack_contract):
        acceptance_criteria.append(
            "Complex requests route through the full AGENT_DAG swarm instead of pack/scaffold fallback.",
        )
    if stack_contract.get("queues"):
        acceptance_criteria.append("Requested queue/worker technology is represented in generated worker or adapter files.")
    if stack_contract.get("realtime"):
        acceptance_criteria.append("Realtime client and server wiring is generated for the requested transport.")
    if stack_contract.get("payments"):
        acceptance_criteria.append("Payment flows include server handlers, configuration, and integration notes.")

    tier = os.environ.get("CRUCIB_QUALITY_TIER", "mvp").strip().lower()
    if tier not in ("prototype", "mvp", "production", "enterprise"):
        tier = "mvp"

    recommended_target = stack_contract.get("recommended_build_target")
    spec_guard = merge_plan_risk_flags_into_report(
        risk_flags,
        evaluate_goal_against_runner(goal, build_target=recommended_target),
        build_target=recommended_target,
    )

    plan = {
        "goal": goal,
        "build_kind": build_kind,
        "phases": phases,
        "phase_count": len(phases),
        "dependencies": integrations,
        "acceptance_criteria": acceptance_criteria,
        "required_integrations": integrations,
        "risk_flags": risk_flags,
        "estimated_steps": total_steps,
        "missing_inputs": missing_inputs,
        "summary": f"Building a {build_kind} application: {goal[:100]}",
        "quality_tier": tier,
        "spec_guard": spec_guard,
        "architecture_outline": _architecture_outline(build_kind, integrations, stack_contract),
        "controller_summary": _controller_summary(goal, selected_agents, phases),
        "selection_explanation": selection_explanation,
        "stack_contract": stack_contract,
        "generation_mode": "full_system_builder" if stack_contract.get("requires_full_system_builder") else "targeted_pack",
        "recommended_build_target": recommended_target,
        "orchestration_mode": "agent_swarm" if _uses_intelligent_orchestration(goal, stack_contract) else "fixed_autorunner",
        "selected_agents": selected_agents,
        "selected_agent_count": len(selected_agents),
    }

    enriched_plan = enrich_plan_with_node_manifests(plan)

    try:
        from memory.service import get_memory_service

        memory = await get_memory_service()
        controller_summary = enriched_plan.get("controller_summary") or {}
        await memory.store_controller_checkpoint(
            project_id=str((project_state or {}).get("project_id") or ""),
            job_id=str((project_state or {}).get("job_id") or "planner-preview"),
            text=(
                f"goal={goal[:200]}\n"
                f"mode={controller_summary.get('controller_mode', 'unknown')}\n"
                f"selected_agents={controller_summary.get('selected_agent_count', 0)}\n"
                f"focus={', '.join(controller_summary.get('recommended_focus') or [])}\n"
                f"next_actions={', '.join(controller_summary.get('next_actions') or [])}"
            ),
            phase="planning",
            checkpoint_type="plan_summary",
            metadata={
                "orchestration_mode": enriched_plan.get("orchestration_mode"),
                "phase_count": str(enriched_plan.get("phase_count") or 0),
            },
        )
    except Exception:
        logger.debug("planner: controller checkpoint memory skipped", exc_info=True)

    return enriched_plan


def estimate_tokens(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate token cost for executing this plan."""
    steps = plan.get("estimated_steps", 10)
    build_kind = plan.get("build_kind", "fullstack")

    # Base tokens per step by type
    base_per_step = {"fullstack": 4000, "frontend": 2500, "mobile": 5000, "automation": 3000}
    tokens_per_step = base_per_step.get(build_kind, 4000)
    integrations = len(plan.get("required_integrations", []))

    estimated_tokens = steps * tokens_per_step + integrations * 2000
    # 1 credit = 1000 tokens (from pricing_plans.py)
    estimated_credits = max(1, round(estimated_tokens / 1000))

    return {
        "estimated_tokens": estimated_tokens,
        "estimated_credits": estimated_credits,
        "estimated_steps": steps,
        "build_kind": build_kind,
        "cost_range": {
            "min_credits": max(1, round(estimated_credits * 0.7)),
            "max_credits": round(estimated_credits * 1.5),
            "typical_credits": estimated_credits,
        },
        "note": "Final cost depends on complexity encountered during execution."
    }
