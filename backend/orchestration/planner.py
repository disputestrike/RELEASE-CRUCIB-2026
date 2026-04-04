"""
planner.py — Structured build planner for CrucibAI.
Produces a normalized plan JSON before any execution starts.
"""
import logging
import json
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
    g = goal.lower()
    integrations = []
    if any(k in g for k in ["stripe", "payment", "billing", "checkout"]):
        integrations.append("stripe")
    if any(k in g for k in ["auth", "login", "signup", "user"]):
        integrations.append("auth")
    if any(k in g for k in ["database", "db", "postgres", "mysql", "storage"]):
        integrations.append("database")
    if any(k in g for k in ["email", "notification", "smtp"]):
        integrations.append("email")
    if any(k in g for k in ["ai", "llm", "gpt", "claude", "openai"]):
        integrations.append("llm")
    return integrations


def _detect_risk_flags(goal: str, project_state: Optional[Dict] = None) -> list:
    flags = []
    g = goal.lower()
    if "stripe" in g and not (project_state or {}).get("env_vars", {}).get("STRIPE_SECRET_KEY"):
        flags.append("stripe_keys_missing")
    if len(goal) < 20:
        flags.append("goal_too_vague")
    if len(goal) > 1000:
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

    # Missing inputs
    missing_inputs = []
    if "stripe" in integrations:
        env_vars = (project_state or {}).get("env_vars", {})
        if not env_vars.get("STRIPE_SECRET_KEY"):
            missing_inputs.append({
                "key": "STRIPE_SECRET_KEY",
                "description": "Required for Stripe payments",
                "blocking": True
            })

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
    }

    return plan


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
