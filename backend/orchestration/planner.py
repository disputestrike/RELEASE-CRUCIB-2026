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


def _detect_risk_flags(goal: str, project_state: Optional[Dict] = None) -> list:
    flags = []
    g = goal.lower()
    if "stripe" in g and not (project_state or {}).get("env_vars", {}).get("STRIPE_SECRET_KEY"):
        flags.append("stripe_keys_missing")
    if len(goal) < 20:
        flags.append("goal_too_vague")
    thresh = _goal_len_advisory_threshold(project_state)
    if thresh is not None and len(goal) > thresh:
        flags.append("goal_too_long_consider_splitting")
    return flags


# ── Phase builders ────────────────────────────────────────────────────────────

def _build_phases(goal: str, build_kind: str, integrations: list) -> list:
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
            "key": "verification",
            "label": "Verification",
            "steps": [
                {"key": "verification.compile", "agent": "Verifier",
                 "name": "Compile check", "description": "Verify frontend and backend compile cleanly",
                 "depends_on": ["frontend.routing", "backend.auth", "database.migration"]},
                {"key": "verification.api_smoke", "agent": "Verifier",
                 "name": "API smoke test", "description": "Hit key endpoints, check responses",
                 "depends_on": ["verification.compile"]},
                {"key": "verification.preview", "agent": "Verifier",
                 "name": "Preview render check", "description": "Confirm preview iframe loads",
                 "depends_on": ["verification.compile"]},
                {"key": "verification.security", "agent": "Security Checker",
                 "name": "Security scan", "description": "Check CORS, auth headers, input validation",
                 "depends_on": ["verification.api_smoke"]},
            ]
        },
        {
            "key": "deploy",
            "label": "Deploy",
            "steps": [
                {"key": "deploy.build", "agent": "Deployment Agent",
                 "name": "Build artifacts", "description": "Run production build",
                 "depends_on": ["verification.security"]},
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
    build_kind = _detect_build_kind(goal)
    integrations = _detect_integrations(goal)
    risk_flags = _detect_risk_flags(goal, project_state)
    phases = _build_phases(goal, build_kind, integrations)

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

    tier = os.environ.get("CRUCIB_QUALITY_TIER", "mvp").strip().lower()
    if tier not in ("prototype", "mvp", "production", "enterprise"):
        tier = "mvp"

    plan = {
        "goal": goal,
        "build_kind": build_kind,
        "phases": phases,
        "dependencies": integrations,
        "acceptance_criteria": acceptance_criteria,
        "required_integrations": integrations,
        "risk_flags": risk_flags,
        "estimated_steps": total_steps,
        "missing_inputs": missing_inputs,
        "summary": f"Building a {build_kind} application: {goal[:100]}",
        "quality_tier": tier,
    }

    return enrich_plan_with_node_manifests(plan)


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
