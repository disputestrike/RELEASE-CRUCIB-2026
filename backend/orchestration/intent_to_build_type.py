"""
intent_to_build_type.py — Unlimited build type inference from any natural language goal.

Replaces the fixed 8-type catalog with a dynamic classification system.
ANY goal maps to a concrete scaffold type + stack config. The catalog is not
a ceiling — it's a starting point. The classify() function handles goals we've
never seen before by falling through to smart defaults.

Usage:
    from backend.orchestration.intent_to_build_type import classify_goal
    result = classify_goal("Build a Shopify-like multi-vendor marketplace with vendor dashboards")
    # => { "type": "marketplace", "stack": "react+vite+ts", "label": "Multi-vendor Marketplace",
    #      "scaffolds": [...], "timeout_multiplier": 1.5, "build_command": ["npm","run","build"] }
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# ── Classification rules ─────────────────────────────────────────────────────
# Each rule: (keywords, type_id, label, stack, timeout_multiplier)
# Rules are evaluated in order — first match wins for explicit keywords.
# The fallback at the end catches everything else.

_RULES: List[Tuple[List[str], str, str, str, float]] = [
    # ── Enterprise / complex SaaS ─────────────────────────────────────────
    (["multi-tenant", "multitenant", "enterprise saas", "b2b saas", "regulated", "row-level security", "rls", "tenant isolation"],
     "enterprise_saas", "Enterprise B2B SaaS", "react+vite+ts+fastapi", 2.5),

    # ── E-commerce ────────────────────────────────────────────────────────
    (["ecommerce", "e-commerce", "shopify", "woocommerce", "product catalog", "shopping cart", "checkout", "stripe checkout", "vendor marketplace", "multi-vendor"],
     "ecommerce", "E-Commerce Store", "react+vite+ts", 1.5),

    # ── Marketplace ───────────────────────────────────────────────────────
    (["marketplace", "multi-vendor", "buyer", "seller", "listing platform", "airbnb", "etsy", "fiverr"],
     "marketplace", "Two-Sided Marketplace", "react+vite+ts", 2.0),

    # ── CRM / Sales ───────────────────────────────────────────────────────
    (["crm", "customer relationship", "sales pipeline", "deal pipeline", "contacts", "lead management", "account management", "salesforce", "hubspot"],
     "crm", "CRM & Sales Platform", "react+vite+ts", 1.5),

    # ── Analytics / BI dashboard ──────────────────────────────────────────
    (["analytics dashboard", "bi dashboard", "business intelligence", "metrics dashboard", "kpi", "data visualization", "charts", "reporting dashboard", "tableau", "looker"],
     "analytics_dashboard", "Analytics Dashboard", "react+vite+ts", 1.2),

    # ── Admin / internal tool ─────────────────────────────────────────────
    (["admin panel", "admin tool", "internal tool", "back-office", "backoffice", "operations dashboard", "employee portal", "staff portal", "retool"],
     "internal_admin_tool", "Internal Admin Tool", "react+vite+ts", 1.2),

    # ── Fintech / payments ────────────────────────────────────────────────
    (["fintech", "banking", "neobank", "ledger", "wallet", "payment gateway", "money transfer", "lending", "loan", "underwriting", "kyc", "aml"],
     "fintech_app", "Fintech Application", "react+vite+ts+fastapi", 2.0),

    # ── Healthcare ────────────────────────────────────────────────────────
    (["healthcare", "health app", "patient portal", "ehr", "emr", "telehealth", "medical", "clinical", "hipaa", "phi"],
     "healthcare_app", "Healthcare Application", "react+vite+ts+fastapi", 2.0),

    # ── Social / community ────────────────────────────────────────────────
    (["social network", "community platform", "forum", "discord", "reddit", "twitter", "social feed", "newsfeed", "follow", "followers"],
     "social_platform", "Social / Community Platform", "react+vite+ts", 1.8),

    # ── Real-time / chat ──────────────────────────────────────────────────
    (["chat app", "messaging app", "real-time chat", "slack", "discord clone", "websocket", "live chat", "instant message"],
     "realtime_chat", "Real-Time Chat App", "react+vite+ts", 1.3),

    # ── Project management ────────────────────────────────────────────────
    (["project management", "task manager", "kanban", "jira", "trello", "asana", "sprint", "issue tracker", "ticket system"],
     "project_management", "Project Management Tool", "react+vite+ts", 1.5),

    # ── Booking / scheduling ──────────────────────────────────────────────
    (["booking", "appointment", "scheduling", "calendar app", "reservation", "time slot", "calendly", "booking system"],
     "booking_system", "Booking & Scheduling", "react+vite+ts", 1.2),

    # ── Content / blog / CMS ──────────────────────────────────────────────
    (["blog", "cms", "content management", "headless cms", "wordpress", "ghost", "article", "publishing platform", "newsletter"],
     "content_platform", "Content / Blog Platform", "react+vite+ts", 1.2),

    # ── Education / LMS ──────────────────────────────────────────────────
    (["lms", "learning management", "course platform", "e-learning", "online course", "udemy", "teachable", "quiz", "lesson", "curriculum"],
     "lms", "Learning Management System", "react+vite+ts", 1.5),

    # ── DevOps / developer tool ───────────────────────────────────────────
    (["devops", "ci/cd", "pipeline", "deployment", "monitoring", "observability", "grafana", "datadog", "log viewer", "infrastructure", "kubernetes dashboard"],
     "devops_tool", "DevOps / Developer Tool", "react+vite+ts", 1.5),

    # ── API backend only ──────────────────────────────────────────────────
    (["rest api", "graphql api", "api backend", "fastapi", "express api", "node api", "flask api", "django rest", "api server", "microservice"],
     "api_backend", "API Backend", "fastapi+python", 1.0),

    # ── Mobile app ────────────────────────────────────────────────────────
    (["mobile app", "react native", "expo app", "ios app", "android app", "flutter"],
     "mobile_expo", "Mobile App (Expo/React Native)", "expo+react-native", 1.5),

    # ── Next.js / SSR ─────────────────────────────────────────────────────
    (["nextjs", "next.js", "next app router", "server-side rendering", "ssr", "ssg", "static site generation"],
     "next_app_router", "Next.js App Router", "nextjs+ts", 1.3),

    # ── Static / marketing site ───────────────────────────────────────────
    (["landing page", "marketing site", "static site", "portfolio", "product page", "waitlist", "coming soon"],
     "static_marketing", "Static / Marketing Site", "react+vite+ts", 1.0),

    # ── File / document management ────────────────────────────────────────
    (["file manager", "document management", "file upload", "file sharing", "dropbox", "google drive", "storage"],
     "file_manager", "File / Document Manager", "react+vite+ts", 1.2),

    # ── HR / people ops ───────────────────────────────────────────────────
    (["hr platform", "human resources", "payroll", "employee management", "onboarding", "performance review", "time tracking"],
     "hr_platform", "HR & People Ops Platform", "react+vite+ts+fastapi", 1.8),

    # ── IoT / hardware dashboard ──────────────────────────────────────────
    (["iot", "sensor", "device dashboard", "telemetry", "industrial", "smart home", "raspberry pi"],
     "iot_dashboard", "IoT / Device Dashboard", "react+vite+ts", 1.3),

    # ── Todo / simple CRUD ────────────────────────────────────────────────
    (["todo", "to-do", "task list", "notes app", "simple app", "crud app", "basic app"],
     "todo_crud", "Todo / Simple CRUD App", "react+vite+ts", 1.0),

    # ── Game / interactive ────────────────────────────────────────────────
    (["game", "interactive", "canvas", "animation", "simulation", "puzzle", "quiz game"],
     "interactive_app", "Interactive / Game App", "react+vite+ts", 1.2),

    # ── AI / ML product ───────────────────────────────────────────────────
    (["ai app", "ml dashboard", "ai tool", "llm", "gpt", "chatgpt", "ai assistant", "prompt", "model playground", "vector search", "rag"],
     "ai_product", "AI / ML Product", "react+vite+ts+fastapi", 1.8),

    # ── Supply chain / logistics ─────────────────────────────────────────
    (["supply chain", "logistics", "warehouse", "inventory", "order management", "fulfillment", "shipping"],
     "supply_chain", "Supply Chain & Logistics", "react+vite+ts+fastapi", 2.0),

    # ── Real estate ────────────────────────────────────────────────────────
    (["real estate", "property listing", "mls", "zillow", "realty", "rent", "mortgage"],
     "real_estate", "Real Estate Platform", "react+vite+ts", 1.5),
]

# Fallback for anything that doesn't match — produces a generic SaaS scaffold
_FALLBACK = ("fullstack_web", "Fullstack Web Application", "react+vite+ts", 1.0)


# ── Stack → build commands ───────────────────────────────────────────────────

_STACK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "react+vite+ts": {
        "install_command": ["npm", "install"],
        "build_command": ["npm", "run", "build"],
        "dev_command": ["npm", "run", "dev"],
        "entry_point": "src/main.tsx",
        "timeout_base": 900,
    },
    "react+vite+ts+fastapi": {
        "install_command": ["npm", "install"],
        "build_command": ["npm", "run", "build"],
        "dev_command": ["npm", "run", "dev"],
        "entry_point": "src/main.tsx",
        "timeout_base": 900,
        "has_backend": True,
    },
    "nextjs+ts": {
        "install_command": ["npm", "install"],
        "build_command": ["npm", "run", "build"],
        "dev_command": ["npm", "run", "dev"],
        "entry_point": "app/page.tsx",
        "timeout_base": 1200,
    },
    "fastapi+python": {
        "install_command": ["pip", "install", "-r", "requirements.txt"],
        "build_command": ["python", "-c", "import app; print('ok')"],
        "dev_command": ["uvicorn", "app.main:app", "--reload"],
        "entry_point": "app/main.py",
        "timeout_base": 600,
    },
    "expo+react-native": {
        "install_command": ["npm", "install"],
        "build_command": ["npx", "expo", "export"],
        "dev_command": ["npx", "expo", "start"],
        "entry_point": "App.tsx",
        "timeout_base": 1200,
    },
}


def classify_goal(goal: str) -> Dict[str, Any]:
    """
    Classify any natural language build goal into a concrete build type.

    Returns a dict with:
      type             : internal type id (e.g. "enterprise_saas")
      label            : human-readable label
      stack            : technology stack key
      install_command  : e.g. ["npm", "install"]
      build_command    : e.g. ["npm", "run", "build"]
      dev_command      : e.g. ["npm", "run", "dev"]
      entry_point      : main file path
      timeout_seconds  : adjusted build timeout
      has_backend      : True if full-stack with separate backend
      is_complex       : True for enterprise/multi-module builds
    """
    goal_lower = (goal or "").lower()

    matched_type = _FALLBACK[0]
    matched_label = _FALLBACK[1]
    matched_stack = _FALLBACK[2]
    matched_multiplier = _FALLBACK[3]

    for keywords, type_id, label, stack, multiplier in _RULES:
        for kw in keywords:
            if kw in goal_lower:
                matched_type = type_id
                matched_label = label
                matched_stack = stack
                matched_multiplier = multiplier
                break
        else:
            continue
        break  # matched

    stack_cfg = _STACK_CONFIGS.get(matched_stack, _STACK_CONFIGS["react+vite+ts"])
    base_timeout = stack_cfg["timeout_base"]
    timeout = int(base_timeout * matched_multiplier)

    return {
        "type": matched_type,
        "label": matched_label,
        "stack": matched_stack,
        "install_command": stack_cfg["install_command"],
        "build_command": stack_cfg["build_command"],
        "dev_command": stack_cfg["dev_command"],
        "entry_point": stack_cfg["entry_point"],
        "timeout_seconds": timeout,
        "has_backend": stack_cfg.get("has_backend", False),
        "is_complex": matched_multiplier >= 1.8,
        "timeout_multiplier": matched_multiplier,
    }


def get_all_type_labels() -> List[Dict[str, str]]:
    """Return all known build types for UI display (open-ended — not a ceiling)."""
    seen = set()
    result = []
    for _, type_id, label, stack, _ in _RULES:
        if type_id not in seen:
            seen.add(type_id)
            result.append({"type": type_id, "label": label, "stack": stack})
    result.append({"type": _FALLBACK[0], "label": _FALLBACK[1], "stack": _FALLBACK[2]})
    return result
