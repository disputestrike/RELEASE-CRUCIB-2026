"""Transparent cost governance for build, simulation, and agent actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.pricing_plans import CREDIT_PLANS, CREDITS_PER_TOKEN


SIMULATION_DEPTHS: dict[str, dict[str, Any]] = {
    "fast": {
        "label": "Fast",
        "core_agents": "6-8",
        "rounds": "2-3",
        "modeled_perspectives": "250-1000",
        "evidence_policy": "official APIs and cached evidence only",
        "credit_cap": 8,
        "timeout_seconds": 90,
    },
    "balanced": {
        "label": "Balanced",
        "core_agents": "10-12",
        "rounds": "4-5",
        "modeled_perspectives": "1000-3000",
        "evidence_policy": "targeted search plus official sources",
        "credit_cap": 18,
        "timeout_seconds": 180,
    },
    "deep": {
        "label": "Deep",
        "core_agents": "14-18",
        "rounds": "6-7",
        "modeled_perspectives": "3000-7500",
        "evidence_policy": "targeted crawl, richer evidence extraction, retries",
        "credit_cap": 35,
        "timeout_seconds": 360,
    },
    "maximum": {
        "label": "Maximum",
        "core_agents": "18-24",
        "rounds": "8+",
        "modeled_perspectives": "7500-10000",
        "evidence_policy": "broad evidence plan with strict budget controls",
        "credit_cap": 60,
        "timeout_seconds": 600,
    },
}

ACTION_BUDGETS: dict[str, dict[str, Any]] = {
    "build": {
        "label": "App/software build",
        "credit_cap": 120,
        "requires_budget": True,
        "gates": ["plan", "files", "install", "build", "preview", "proof", "export"],
    },
    "simulation": {
        "label": "Reality Engine simulation",
        "credit_cap": SIMULATION_DEPTHS["balanced"]["credit_cap"],
        "requires_budget": True,
        "gates": ["route", "evidence", "agents", "debate", "population", "trust", "report"],
    },
    "preview": {
        "label": "Live preview boot",
        "credit_cap": 12,
        "requires_budget": True,
        "gates": ["install", "run", "smoke", "logs"],
    },
    "proof": {
        "label": "Proof bundle",
        "credit_cap": 18,
        "requires_budget": True,
        "gates": ["tests", "lint", "build", "manifest"],
    },
    "automation": {
        "label": "Automation run",
        "credit_cap": 25,
        "requires_budget": True,
        "gates": ["steps", "approvals", "audit", "results"],
    },
    "connector_sync": {
        "label": "Connector sync",
        "credit_cap": 15,
        "requires_budget": True,
        "gates": ["credentials", "scope", "rate_limit", "audit"],
    },
}

MODEL_ROUTING_POLICY = {
    "lite": {
        "use_for": ["classification", "small edits", "simple summaries", "capability checks"],
        "principle": "cheap model first when risk is low and no tool-heavy reasoning is required",
    },
    "pro": {
        "use_for": ["normal builds", "code repair", "medium simulations", "requirements extraction"],
        "principle": "balanced model for production work where quality matters but depth is bounded",
    },
    "max": {
        "use_for": ["complex architecture", "deep code generation", "high-stakes simulation", "release gates"],
        "principle": "deep model only when complexity, evidence, or proof requirements justify the cost",
    },
}


@dataclass(frozen=True)
class CostEstimate:
    action: str
    plan: str
    depth: str | None
    estimated_tokens: int
    estimated_credits: float
    policy_credit_cap: float
    plan_monthly_credits: int

    @property
    def within_action_cap(self) -> bool:
        return self.estimated_credits <= self.policy_credit_cap

    @property
    def within_plan_monthly_credit_pool(self) -> bool:
        return self.estimated_credits <= self.plan_monthly_credits


def plan_catalog() -> list[dict[str, Any]]:
    """Return approved public credit plans without legacy price names."""
    plans: list[dict[str, Any]] = []
    for key in ("free", "builder", "pro", "scale", "teams"):
        plan = CREDIT_PLANS[key]
        plans.append(
            {
                "key": key,
                "name": plan["name"],
                "price_usd": plan["price"],
                "monthly_credits": plan["credits"],
                "monthly_tokens": plan["credits"] * CREDITS_PER_TOKEN,
                "credit_rate_usd": 0.05 if key != "free" else 0,
            }
        )
    return plans


def cost_governance_payload() -> dict[str, Any]:
    return {
        "status": "ready",
        "pricing": {
            "plans": plan_catalog(),
            "bulk_credit_rate_usd": 0.05,
            "approved_price_floor": "$20 Builder plan",
            "legacy_prices_allowed": False,
        },
        "simulation_depths": SIMULATION_DEPTHS,
        "action_budgets": ACTION_BUDGETS,
        "model_routing": MODEL_ROUTING_POLICY,
        "guardrails": [
            "Every expensive action must choose or infer a budget.",
            "Deep/Maximum runs must expose higher cost and time expectations.",
            "Simulation depth controls agents, rounds, evidence depth, and modeled perspectives.",
            "No hidden Stripe dependency: payments are Braintree and require Braintree runtime configuration.",
        ],
    }


def estimate_cost(
    *,
    action: str,
    plan: str = "free",
    depth: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict[str, Any]:
    action_key = action.lower().strip()
    plan_key = plan.lower().strip()
    depth_key = depth.lower().strip() if depth else None
    if action_key not in ACTION_BUDGETS:
        raise ValueError(f"Unknown action: {action}")
    if plan_key not in CREDIT_PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    if depth_key and depth_key not in SIMULATION_DEPTHS:
        raise ValueError(f"Unknown simulation depth: {depth}")

    estimated_tokens = max(0, int(input_tokens)) + max(0, int(output_tokens))
    estimated_credits = estimated_tokens / CREDITS_PER_TOKEN
    cap = float(ACTION_BUDGETS[action_key]["credit_cap"])
    if action_key == "simulation" and depth_key:
        cap = float(SIMULATION_DEPTHS[depth_key]["credit_cap"])
    estimate = CostEstimate(
        action=action_key,
        plan=plan_key,
        depth=depth_key,
        estimated_tokens=estimated_tokens,
        estimated_credits=estimated_credits,
        policy_credit_cap=cap,
        plan_monthly_credits=int(CREDIT_PLANS[plan_key]["credits"]),
    )
    return {
        "action": estimate.action,
        "plan": estimate.plan,
        "depth": estimate.depth,
        "estimated_tokens": estimate.estimated_tokens,
        "estimated_credits": round(estimate.estimated_credits, 4),
        "estimated_usd_at_public_rate": round(estimate.estimated_credits * 0.05, 4),
        "policy_credit_cap": estimate.policy_credit_cap,
        "plan_monthly_credits": estimate.plan_monthly_credits,
        "within_action_cap": estimate.within_action_cap,
        "within_plan_monthly_credit_pool": estimate.within_plan_monthly_credit_pool,
        "requires_approval": not estimate.within_action_cap,
    }
