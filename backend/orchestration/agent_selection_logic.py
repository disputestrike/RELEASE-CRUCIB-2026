"""Intelligent swarm agent selection for complex CrucibAI builds.

This module narrows the full AGENT_DAG to the agents that matter for a goal,
then expands the set to include all required dependencies so execution stays
honest and complete.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from backend.agent_dag import AGENT_DAG, get_execution_phases

from .agent_audit_registry import agents_excluded_from_autorunner_selection
from .brain_policy import agent_selection_hard_cap
from .directory_contracts import (
    directory_profile_from_contract,
    stack_profile_from_contract,
)
from .generation_policy import legacy_broad_agent_support_enabled

BASE_AGENTS = [
    "Planner",
    "Requirements Clarifier",
    "Stack Selector",
    "Frontend Generation",
    "Backend Generation",
    "Database Agent",
    "File Tool Agent",
]

DEFAULT_SUPPORT_AGENTS = [
    "Code Review Agent",
    "Security Checker",
    "UX Auditor",
    "Performance Analyzer",
    "Deployment Agent",
    "Memory Agent",
    "Build Orchestrator Agent",
    "Deployment Safety Agent",
    "Quality Metrics Aggregator Agent",
]

ALWAYS_INCLUDED_AGENT_SET = frozenset(BASE_AGENTS + DEFAULT_SUPPORT_AGENTS)

# Explicit WebGL / 3D stack goals: allow agents the audit marks as 3D "orphans" so
# Three.js / Babylon / Cesium builds still get a render-capable swarm.
RENDER_STACK_SELECTION_KEYWORDS = frozenset(
    {"3d", "webgl", "three.js", "babylon", "cesium", "webgpu"}
)


AGENT_KEYWORDS = {
    # 3D / rendering
    "3d": [
        "3D Engine Selector Agent",
        "3D Model Agent",
        "3D Scene Agent",
        "3D Interaction Agent",
    ],
    "webgl": ["3D Engine Selector Agent", "WebGL Shader Agent", "3D Performance Agent"],
    "three.js": [
        "3D Engine Selector Agent",
        "3D Model Agent",
        "3D Scene Agent",
        "3D Physics Agent",
    ],
    "babylon": ["3D Engine Selector Agent", "3D Model Agent", "3D Physics Agent"],
    "cesium": ["3D Engine Selector Agent", "3D Scene Agent"],
    "canvas": ["Canvas/SVG Rendering Agent"],
    "svg": ["Canvas/SVG Rendering Agent"],
    "ar": ["3D AR/VR Agent"],
    "vr": ["3D AR/VR Agent"],
    "augmented reality": ["3D AR/VR Agent"],
    "virtual reality": ["3D AR/VR Agent"],
    # ML / AI
    "ml": [
        "ML Framework Selector Agent",
        "ML Data Pipeline Agent",
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Evaluation Agent",
    ],
    "machine learning": [
        "ML Framework Selector Agent",
        "ML Data Pipeline Agent",
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Evaluation Agent",
    ],
    "tensorflow": [
        "ML Framework Selector Agent",
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Model Export Agent",
    ],
    "pytorch": [
        "ML Framework Selector Agent",
        "ML Model Definition Agent",
        "ML Training Agent",
    ],
    "sklearn": [
        "ML Framework Selector Agent",
        "ML Data Pipeline Agent",
        "ML Preprocessing Agent",
    ],
    "scikit-learn": [
        "ML Framework Selector Agent",
        "ML Data Pipeline Agent",
        "ML Preprocessing Agent",
    ],
    "xgboost": [
        "ML Framework Selector Agent",
        "ML Data Pipeline Agent",
        "ML Training Agent",
    ],
    "neural network": ["ML Model Definition Agent", "ML Training Agent"],
    "deep learning": [
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Explainability Agent",
    ],
    "prediction": [
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Evaluation Agent",
    ],
    # Avoid bare "model" — false positives on "tenant model", "domain model", "data model".
    "ml model": [
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Model Export Agent",
    ],
    "predictive model": [
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Evaluation Agent",
    ],
    "trained model": [
        "ML Model Definition Agent",
        "ML Training Agent",
        "ML Model Monitoring Agent",
    ],
    "feature engineering": ["ML Data Pipeline Agent", "ML Preprocessing Agent"],
    "embedding": ["Embeddings/Vectorization Agent"],
    "vector": ["Embeddings/Vectorization Agent"],
    "recommendation": ["Recommendation Engine Agent", "Embeddings/Vectorization Agent"],
    "sentiment analysis": ["ML Training Agent", "ML Explainability Agent"],
    "nlp": ["ML Model Definition Agent", "Embeddings/Vectorization Agent"],
    "computer vision": ["ML Model Definition Agent", "ML Training Agent"],
    "classification": ["ML Model Definition Agent", "ML Evaluation Agent"],
    "regression": ["ML Model Definition Agent", "ML Evaluation Agent"],
    "clustering": ["ML Data Pipeline Agent", "ML Training Agent"],
    "forecast": ["Time Series Forecasting Agent"],
    "time series": ["Time Series Forecasting Agent"],
    # Blockchain / Web3
    "blockchain": [
        "Blockchain Selector Agent",
        "Smart Contract Agent",
        "Contract Testing Agent",
    ],
    "smart contract": [
        "Smart Contract Agent",
        "Contract Testing Agent",
        "Contract Deployment Agent",
    ],
    "smart contracts": [
        "Smart Contract Agent",
        "Contract Testing Agent",
        "Contract Deployment Agent",
    ],
    "ethereum": [
        "Blockchain Selector Agent",
        "Smart Contract Agent",
        "Web3 Frontend Agent",
    ],
    "solidity": ["Smart Contract Agent", "Contract Testing Agent"],
    "web3": ["Web3 Frontend Agent", "Blockchain Data Agent", "DeFi Integration Agent"],
    "crypto": [
        "Blockchain Selector Agent",
        "Smart Contract Agent",
        "Web3 Frontend Agent",
    ],
    "defi": ["DeFi Integration Agent", "Smart Contract Agent", "Web3 Frontend Agent"],
    "nft": ["Smart Contract Agent", "Web3 Frontend Agent"],
    # Avoid bare "token" — false positives on JWT/session/access tokens.
    "erc-20": ["Smart Contract Agent", "Web3 Frontend Agent"],
    "erc20": ["Smart Contract Agent", "Web3 Frontend Agent"],
    "spl token": ["Blockchain Selector Agent", "Smart Contract Agent"],
    "wallet": ["Web3 Frontend Agent", "Blockchain Data Agent"],
    "dapp": [
        "Web3 Frontend Agent",
        "Smart Contract Agent",
        "Contract Deployment Agent",
    ],
    "polygon": ["Blockchain Selector Agent", "Smart Contract Agent"],
    "solana": ["Blockchain Selector Agent", "Smart Contract Agent"],
    # IoT / hardware
    "iot": [
        "IoT Platform Selector Agent",
        "Microcontroller Firmware Agent",
        "IoT Communication Agent",
        "IoT Cloud Backend Agent",
    ],
    "arduino": [
        "IoT Platform Selector Agent",
        "Microcontroller Firmware Agent",
        "IoT Sensor Agent",
    ],
    "raspberry pi": ["IoT Platform Selector Agent", "Microcontroller Firmware Agent"],
    "sensor": ["IoT Sensor Agent", "IoT Data Pipeline Agent"],
    # Bare "device" matches SaaS copy ("device fingerprint", etc.) — use explicit IoT phrases only.
    "iot device": [
        "IoT Platform Selector Agent",
        "Microcontroller Firmware Agent",
        "IoT Cloud Backend Agent",
    ],
    "connected device": [
        "IoT Platform Selector Agent",
        "IoT Sensor Agent",
        "IoT Cloud Backend Agent",
    ],
    "mqtt": ["IoT Communication Agent"],
    "ble": ["IoT Communication Agent", "IoT Mobile App Agent"],
    "bluetooth": ["IoT Communication Agent", "IoT Mobile App Agent"],
    "lora": ["IoT Communication Agent"],
    "firmware": ["Microcontroller Firmware Agent", "IoT Security Agent"],
    "edge": ["Edge Computing Agent", "Edge Deployment Agent"],
    "embedded": ["Microcontroller Firmware Agent", "IoT Sensor Agent"],
    # Data / analytics (avoid bare "data" — matches almost every spec; use phrases)
    "data warehouse": [
        "Data Quality Agent",
        "Data Warehouse Agent",
        "Report Generation Agent",
    ],
    "data pipeline": ["ML Data Pipeline Agent", "Data Pipeline Agent"],
    "analytics": [
        "Data Visualization Agent",
        "Statistical Analysis Agent",
        "Jupyter Notebook Agent",
    ],
    "jupyter": ["Jupyter Notebook Agent"],
    "notebook": ["Jupyter Notebook Agent"],
    "statistical": ["Statistical Analysis Agent"],
    # "visualization" alone is usually charts/KPIs, not 3D — Three/WebGL keywords cover 3D.
    "visualization": ["Data Visualization Agent"],
    "data visualization": ["Data Visualization Agent"],
    "chart": ["Data Visualization Agent"],
    "dashboard": ["Data Visualization Agent"],
    "iot dashboard": ["IoT Dashboard Agent", "Data Visualization Agent"],
    "report": ["Report Generation Agent", "Data Visualization Agent"],
    "eda": ["Jupyter Notebook Agent", "Statistical Analysis Agent"],
    "warehouse": [
        "Data Quality Agent",
        "Report Generation Agent",
        "Statistical Analysis Agent",
    ],
    # Infrastructure / ops
    "kubernetes": ["Kubernetes Advanced Agent", "DevOps Agent"],
    "k8s": ["Kubernetes Advanced Agent", "DevOps Agent"],
    "serverless": ["Serverless Deployment Agent"],
    "lambda": ["Serverless Deployment Agent"],
    "cloudflare": ["Edge Deployment Agent"],
    "edge function": ["Edge Deployment Agent"],
    "istio": ["Kubernetes Advanced Agent"],
    "service mesh": ["Kubernetes Advanced Agent"],
    "docker": ["DevOps Agent"],
    "container": ["DevOps Agent"],
    "load balance": ["Load Balancer Agent"],
    "database optimization": ["Database Optimization Agent"],
    "kafka": ["Message Queue Advanced Agent"],
    "rabbitmq": ["Message Queue Advanced Agent"],
    "queue": ["Queue Agent", "Message Queue Advanced Agent"],
    "bullmq": ["Queue Agent", "Message Queue Advanced Agent"],
    "celery": ["Queue Agent", "Message Queue Advanced Agent"],
    "cache": ["Caching Agent", "Database Optimization Agent"],
    "redis": ["Caching Agent", "Database Optimization Agent"],
    # Generic "security" is handled by rule:security_scan / rule:security_headers — do not
    # pull blockchain/network agents from every "security features" SaaS prompt.
    "network security": ["Network Security Agent", "Security Checker"],
    "penetration test": ["Network Security Agent", "Security Scanning Agent"],
    "vpc": ["Network Security Agent"],
    "firewall": ["Network Security Agent"],
    "disaster recovery": ["Disaster Recovery Agent"],
    "backup": ["Backup Agent", "Disaster Recovery Agent"],
    "deploy": ["Deployment Agent", "Deployment Tool Agent", "DevOps Agent"],
    "production": ["Deployment Agent", "Staging Agent"],
    "devops": ["DevOps Agent"],
    "ci/cd": ["DevOps Agent"],
    "monitoring": ["Monitoring Agent", "Metrics Agent", "Logging Agent"],
    "observability": ["Monitoring Agent", "Metrics Agent", "Logging Agent"],
    "metrics": ["Metrics Agent"],
    "logging": ["Logging Agent"],
    "tracing": ["Monitoring Agent"],
    "apm": ["Monitoring Agent"],
    # Testing
    "test": ["Test Generation", "Test Executor", "E2E Agent", "Load Test Agent"],
    "testing": ["Test Generation", "Test Executor", "E2E Agent", "Smoke Test Agent"],
    "unit test": ["Test Generation"],
    "e2e": ["E2E Agent"],
    "integration test": ["Test Generation", "Contract Testing Agent"],
    "load test": ["Load Test Agent", "Chaos Engineering Agent"],
    "chaos": ["Chaos Engineering Agent"],
    "property-based": ["Property-Based Testing Agent"],
    "mutation": ["Mutation Testing Agent"],
    "contract test": ["Contract Testing Agent"],
    "synthetic": ["Synthetic Monitoring Agent"],
    "smoke test": ["Smoke Test Agent"],
    # Business / enterprise
    "workflow": ["Workflow Engine Agent", "Workflow Agent"],
    "state machine": ["Workflow Engine Agent"],
    "approval": ["Approval Flow Agent"],
    "rules": ["Business Rules Engine Agent"],
    "business logic": ["Business Rules Engine Agent"],
    "scheduling": ["Scheduling Agent"],
    "calendar": ["Scheduling Agent"],
    "search": ["Search Relevance Agent", "Search Agent"],
    "notification": ["Notification Rules Agent", "Notification Agent"],
    "audit": ["Audit & Compliance Engine Agent", "Audit Trail Agent"],
    "compliance": ["Audit & Compliance Engine Agent", "Legal Compliance Agent"],
    "enterprise": [
        "Multi-tenant Agent",
        "RBAC Agent",
        "Approval Flow Agent",
        "Audit & Compliance Engine Agent",
    ],
    "multi-tenant": ["Multi-tenant Agent", "RBAC Agent"],
    "multitenant": ["Multi-tenant Agent", "RBAC Agent"],
    "tenant isolation": ["Multi-tenant Agent", "RBAC Agent", "Audit Trail Agent"],
    "crm": ["Form Builder Agent", "Table Agent", "Search Agent", "Workflow Agent"],
    "quote": [
        "Approval Flow Agent",
        "Business Rules Engine Agent",
        "Form Builder Agent",
        "Audit Trail Agent",
    ],
    "quotes": [
        "Approval Flow Agent",
        "Business Rules Engine Agent",
        "Form Builder Agent",
        "Audit Trail Agent",
    ],
    "project": [
        "Workflow Agent",
        "Scheduling Agent",
        "Table Agent",
        "Notification Agent",
    ],
    "projects": [
        "Workflow Agent",
        "Scheduling Agent",
        "Table Agent",
        "Notification Agent",
    ],
    "policy": [
        "Business Rules Engine Agent",
        "Approval Flow Agent",
        "Audit & Compliance Engine Agent",
    ],
    "operator": [
        "Table Agent",
        "Workflow Agent",
        "Notification Agent",
        "Audit Trail Agent",
    ],
    "operators": [
        "Table Agent",
        "Workflow Agent",
        "Notification Agent",
        "Audit Trail Agent",
    ],
    "background jobs": ["Queue Agent", "Workflow Engine Agent", "Notification Agent"],
    "worker/job system": ["Queue Agent", "Workflow Engine Agent"],
    # Design / UI
    "design": ["Design Agent", "Layout Agent", "UX Auditor", "Accessibility Agent"],
    "ui": ["Frontend Generation", "Design Agent", "Layout Agent"],
    "ux": ["UX Auditor", "Design Agent"],
    "styling": ["Design Agent", "Frontend Generation"],
    "css": ["Frontend Generation", "Design Agent", "Layout Agent"],
    "brand": ["Brand Agent", "Design Agent"],
    "dark mode": ["Dark Mode Agent", "Frontend Generation"],
    "animation": ["Animation Agent", "3D Animation Agent"],
    "responsive": ["Mobile Responsive Agent", "Frontend Generation"],
    "image": ["Image Generation", "Layout Agent"],
    "images": ["Image Generation", "Layout Agent"],
    "video": ["Video Generation"],
    # Security / auth
    "auth": ["Auth Setup Agent", "Security Checker"],
    "authentication": ["Auth Setup Agent", "Security Checker"],
    "oauth": ["OAuth Provider Agent"],
    "2fa": ["2FA Agent"],
    "password": ["Auth Setup Agent"],
    "encryption": ["Network Security Agent", "Security Checker"],
    "iot security": ["IoT Security Agent", "Network Security Agent"],
    "rbac": ["RBAC Agent"],
    "permission": ["RBAC Agent"],
    # Payments / comms
    "payment": ["Payment Setup Agent", "Braintree Subscription Agent"],
    "braintree": ["Payment Setup Agent", "Braintree Subscription Agent"],
    "billing": ["Braintree Subscription Agent", "Invoice Agent"],
    "invoice": ["Invoice Agent"],
    "email": ["Email Agent", "Notification Agent"],
    "sendgrid": ["Email Agent", "Notification Agent"],
    "twilio": ["Notification Agent"],
    "websocket": ["WebSocket Agent"],
    "websockets": ["WebSocket Agent"],
    "realtime": ["WebSocket Agent"],
    "real-time": ["WebSocket Agent"],
    # Mobile
    "mobile": [
        "Native Config Agent",
        "Store Prep Agent",
        "Mobile Responsive Agent",
    ],
    "iot mobile": ["IoT Mobile App Agent", "IoT Communication Agent"],
    "ios": ["Native Config Agent", "Store Prep Agent"],
    "android": ["Native Config Agent", "Store Prep Agent"],
    "react native": ["Native Config Agent"],
    "expo": ["Native Config Agent", "Store Prep Agent"],
    "flutter": ["Native Config Agent"],
    "app store": ["Store Prep Agent"],
    # Docs / content
    "documentation": ["Documentation Agent"],
    "docs": ["Documentation Agent"],
    "openapi": ["API Documentation Agent", "API Integration"],
    "swagger": ["API Documentation Agent", "API Integration"],
    "graphql": ["GraphQL Agent", "API Integration"],
    "grpc": ["API Integration"],
    "content": ["Content Agent", "SEO Agent"],
    "seo": ["SEO Agent", "Content Agent"],
    "marketing": ["Content Agent", "SEO Agent"],
    "copy": ["Content Agent"],
}


# Single-keyword hits that appear in almost every SaaS spec; they still add agents inside
# explain_agent_selection, but must not alone flip should_route_to_agent_selection — otherwise
# every generic app expands into dozens of specialized DAG nodes.
ROUTING_NOISE_KEYWORDS: frozenset[str] = frozenset(
    {
        "dashboard",
        "analytics",
        "report",
        "visualization",
        "data visualization",
        "chart",
        "search",
        "auth",
        "authentication",
        "password",
        "mobile",
        "responsive",
        "design",
        "ui",
        "ux",
        "styling",
        "css",
        "production",
        "deploy",
        "test",
        "testing",
        "documentation",
        "docs",
        "email",
        "notification",
        "realtime",
        "real-time",
        "websocket",
        "websockets",
        "Braintree",
        "payment",
        "billing",
        "oauth",
        "rbac",
        "permission",
        "invoice",
        "api",
        "graphql",
        "openapi",
        "swagger",
        "content",
        "seo",
        "marketing",
        "copy",
        "workflow",
        "scheduling",
        "admin",
        "portal",
        "landing",
        "dark mode",
        "animation",
        "brand",
        "cache",
        "metrics",
        "logging",
        "monitoring",
        "tracing",
        "apm",
        "queue",
        "docker",
        "container",
        "devops",
        "ci/cd",
        "kubernetes",
        "k8s",
        "postgres",
        "database",
        "redis",
        "sqlite",
        "graphql",
    }
)


def _dependency_closure(initial: Set[str]) -> Set[str]:
    block = agents_excluded_from_autorunner_selection()
    selected = set(initial)
    queue = list(initial)
    while queue:
        name = queue.pop()
        for dep in AGENT_DAG.get(name, {}).get("depends_on", []):
            if dep in AGENT_DAG and dep not in selected and dep not in block:
                selected.add(dep)
                queue.append(dep)
    return selected


def _apply_hard_agent_cap(
    selected: Set[str], cap: int, matched_rules: List[str]
) -> Set[str]:
    """Trim specialized agents (never ALWAYS_INCLUDED) until count <= cap or stable."""
    if len(selected) <= cap:
        return selected
    before = len(selected)
    s = set(selected)
    iterations = 0
    while len(s) > cap and iterations < 400:
        iterations += 1
        removable = sorted(a for a in s if a not in ALWAYS_INCLUDED_AGENT_SET)
        if not removable:
            break
        s.discard(removable[-1])
        s = _dependency_closure(s)
    if len(s) < before:
        matched_rules.append(f"governor:hard_max_trimmed_{before}_to_{len(s)}_cap_{cap}")
    if len(s) > cap:
        matched_rules.append(f"governor:hard_cap_partial_core_only_{len(s)}")
    return s


def _keyword_match(keyword: str, text: str) -> bool:
    """Match keyword with word boundaries to avoid substring false positives."""
    normalized = (keyword or "").lower()
    haystack = (text or "").lower()
    escaped = re.escape(normalized)
    if not escaped:
        return False

    negation_patterns = (
        rf"\b(?:not|no|without)\s+(?:an?\s+)?{escaped}\b",
        rf"\b(?:exclude|excluding)\s+(?:an?\s+)?{escaped}\b",
    )
    if any(re.search(pattern, haystack) for pattern in negation_patterns):
        return False

    if normalized == "ar":
        return (
            bool(re.search(r"\bar\b", haystack))
            and not re.search(r"\b(?:not|no|without)\s+(?:an?\s+)?ar\b", haystack)
        ) or (
            "augmented reality" in haystack
            and not re.search(
                r"\b(?:not|no|without)\s+(?:an?\s+)?augmented reality\b", haystack
            )
        )
    if normalized == "vr":
        return (
            bool(re.search(r"\bvr\b", haystack))
            and not re.search(r"\b(?:not|no|without)\s+(?:an?\s+)?vr\b", haystack)
        ) or (
            "virtual reality" in haystack
            and not re.search(
                r"\b(?:not|no|without)\s+(?:an?\s+)?virtual reality\b", haystack
            )
        )
    pattern = rf"\b{escaped}\b"
    return bool(re.search(pattern, haystack))


def _record_rule_hit(
    selected: Set[str],
    matched_rules: List[str],
    label: str,
    agents: tuple[str, ...] | list[str],
    *,
    bypass_exclusion: bool = False,
) -> None:
    block = agents_excluded_from_autorunner_selection()
    additions = [
        agent
        for agent in agents
        if agent in AGENT_DAG and (bypass_exclusion or agent not in block)
    ]
    if not additions:
        return
    before = len(selected)
    selected.update(additions)
    if len(selected) != before:
        matched_rules.append(label)


def explain_agent_selection(
    goal: str, stack_contract: Dict | None = None
) -> Dict[str, object]:
    selected: Set[str] = set(BASE_AGENTS)
    goal_text = goal or ""
    goal_lower = goal_text.lower()
    contract = stack_contract or {}
    matched_keywords: List[str] = []
    matched_rules: List[str] = []

    for keyword, agents in AGENT_KEYWORDS.items():
        if _keyword_match(keyword, goal_text):
            _record_rule_hit(
                selected,
                matched_rules,
                f"keyword:{keyword}",
                agents,
                bypass_exclusion=keyword in RENDER_STACK_SELECTION_KEYWORDS,
            )
            matched_keywords.append(keyword)

    if contract.get("mobile"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:mobile",
            ("Native Config Agent", "Store Prep Agent", "Mobile Responsive Agent"),
        )

    if contract.get("requires_full_system_builder"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:full_system_builder",
            (
                "File Tool Agent",
                "Code Review Agent",
                "Security Checker",
                "UX Auditor",
                "Performance Analyzer",
                "Deployment Agent",
                "Memory Agent",
            ),
        )

    if contract.get("queues"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:queues",
            ("Queue Agent", "Message Queue Advanced Agent"),
        )
    if contract.get("caches"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:caches",
            ("Caching Agent", "Database Optimization Agent"),
        )
    if contract.get("payments"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:payments",
            (
                "Payment Setup Agent",
                "Braintree Subscription Agent",
                "Braintree Integration Agent",
                "Subscription Management Agent",
            ),
        )
    if contract.get("realtime"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:realtime",
            ("WebSocket Agent", "Real-Time Collaboration Agent"),
        )
    if contract.get("vector_databases"):
        _record_rule_hit(
            selected,
            matched_rules,
            "contract:vector_databases",
            (
                "Embeddings/Vectorization Agent",
                "Recommendation Engine Agent",
                "RAG Agent",
            ),
        )

    # Use word-boundary check for short tokens ("ui", "ux") to avoid
    # matching substrings like "ui" inside "build" or "ux" inside "luxury"
    _design_words_long = ("design", "landing", "website")
    _design_words_short = ("ui", "ux")
    if any(w in goal_lower for w in _design_words_long) or any(
        re.search(r"\b" + w + r"\b", goal_lower) for w in _design_words_short
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:design_surface",
            (
                "Design Agent",
                "Layout Agent",
                "Brand Agent",
                "UX Auditor",
                "Dark Mode Agent",
                "Animation Agent",
                "CSS Modern Standards Agent",
                "Typography System Agent",
                "Color Palette System Agent",
                "Responsive Breakpoints Agent",
            ),
        )

    if any(
        word in goal_lower
        for word in ("content", "seo", "marketing", "landing", "blog")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:content_surface",
            (
                "Content Agent",
                "SEO Agent",
                "Image Generation",
                "Image Optimization Agent",
                "Icon System Agent",
            ),
        )

    if any(
        word in goal_lower
        for word in ("enterprise", "compliance", "hipaa", "soc2", "gdpr")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:enterprise_compliance",
            (
                "Legal Compliance Agent",
                "Audit Trail Agent",
                "Audit & Compliance Engine Agent",
                "Multi-tenant Agent",
                "RBAC Agent",
                "Secret Management Agent",
                "CORS & Security Headers Agent",
                "Input Validation Agent",
                "Rate Limiting Agent",
            ),
        )

    if any(
        word in goal_lower
        for word in (
            "scale",
            "kubernetes",
            "microservice",
            "distributed",
            "high-availability",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:scale_infra",
            (
                "Kubernetes Advanced Agent",
                "Load Balancer Agent",
                "Message Queue Advanced Agent",
                "Database Optimization Agent",
                "Disaster Recovery Agent",
                "Monitoring Agent",
                "Docker Setup Agent",
                "GitHub Actions CI Agent",
            ),
        )

    if (
        any(word in goal_lower for word in ("analytics", "bigdata", "warehouse"))
        or "data warehouse" in goal_lower
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:data_analytics",
            (
                "Data Quality Agent",
                "Data Visualization Agent",
                "Report Generation Agent",
                "Statistical Analysis Agent",
                "Analytics Events Schema Agent",
                "Data Pipeline Agent",
                "Data Warehouse Agent",
            ),
        )

    # EXPANSION AGENTS - Add based on keywords
    if any(
        word in goal_lower
        for word in (
            "compile",
            "vite",
            "npm",
            "dependency",
            "dependencies",
            "import path",
            "import validation",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:build_validation",
            (
                "Build Validator Agent",
                "Dependency Conflict Resolver Agent",
                "Import Path Validator Agent",
                "Compilation Dry-Run Agent",
            ),
        )

    if any(word in goal_lower for word in ("dark mode", "theme", "dark", "night")):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:dark_mode",
            ("Dark Mode Theme Agent", "Color Palette System Agent"),
        )

    if any(
        word in goal_lower
        for word in ("animation", "transition", "motion", "micro-interaction")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:animation",
            ("Animation & Transitions Agent",),
        )

    if any(
        word in goal_lower
        for word in ("image optimization", "webp", "compress", "optimized image")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:image_optimization",
            ("Image Optimization Agent",),
        )

    if any(word in goal_lower for word in ("icon", "icons", "symbol", "svg sprite")):
        _record_rule_hit(
            selected, matched_rules, "rule:icon_system", ("Icon System Agent",)
        )

    if any(word in goal_lower for word in ("docker", "container", "kubernetes")):
        _record_rule_hit(
            selected, matched_rules, "rule:docker_setup", ("Docker Setup Agent",)
        )

    if any(
        word in goal_lower for word in ("ci", "cd", "github", "actions", "workflow")
    ):
        _record_rule_hit(
            selected, matched_rules, "rule:ci_cd", ("GitHub Actions CI Agent",)
        )

    if any(
        word in goal_lower for word in ("env", "environment", "config", "configuration")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:environment_config",
            ("Environment Configuration Agent",),
        )

    if any(
        word in goal_lower
        for word in ("test", "unit", "integration", "e2e", "end-to-end")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:test_suite",
            (
                "Unit Test Agent",
                "Integration Test Agent",
                "E2E Test Agent",
                "Performance Test Agent",
            ),
        )

    if any(
        word in goal_lower for word in ("performance", "load", "stress", "benchmark")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:performance",
            ("Performance Test Agent", "Lighthouse Performance Agent"),
        )

    if any(
        word in goal_lower for word in ("security", "scan", "vulnerability", "audit")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:security_scan",
            ("Security Scanning Agent", "Code Quality Gate Agent"),
        )

    if any(
        word in goal_lower
        for word in ("cors", "security headers", "csp", "hsts", "x-frame-options")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:security_headers",
            ("CORS & Security Headers Agent",),
        )

    if any(
        word in goal_lower
        for word in (
            "input validation",
            "request validation",
            "sanitize input",
            "sanitization",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:input_validation",
            ("Input Validation Agent",),
        )

    if any(
        word in goal_lower
        for word in ("rate limiting", "ratelimit", "throttle", "ddos")
    ):
        _record_rule_hit(
            selected, matched_rules, "rule:rate_limiting", ("Rate Limiting Agent",)
        )

    if any(word in goal_lower for word in ("email", "template", "mjml")):
        _record_rule_hit(
            selected, matched_rules, "rule:email_templates", ("Email Template Agent",)
        )

    if any(word in goal_lower for word in ("sms", "push", "notification", "twilio")):
        _record_rule_hit(
            selected, matched_rules, "rule:sms_push", ("SMS & Push Agent",)
        )

    if any(word in goal_lower for word in ("api", "contract", "schema", "openapi")):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:api_contract",
            ("API Contract Validator Agent", "API Documentation Generation Agent"),
        )

    if any(
        word in goal_lower
        for word in (
            "database",
            "schema",
            "migration",
            "sql",
            "postgres",
            "postgresql",
            "sqlite",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:database_schema",
            ("Database Schema Validator Agent", "ORM Setup Agent"),
        )

    if any(word in goal_lower for word in ("search", "elasticsearch", "algolia")):
        _record_rule_hit(
            selected, matched_rules, "rule:search_engine", ("Search Engine Agent",)
        )

    if any(word in goal_lower for word in ("recommendation", "ml", "personalization")):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:recommendation_engine",
            ("Recommendation Engine Agent",),
        )

    # Avoid matching "file" inside unrelated words (e.g. "profile").
    if any(word in goal_lower for word in ("upload", "s3", "storage", "blob storage")):
        _record_rule_hit(
            selected, matched_rules, "rule:file_storage", ("File Storage Agent",)
        )

    if any(word in goal_lower for word in ("webhook", "event", "callback")):
        _record_rule_hit(
            selected, matched_rules, "rule:webhooks", ("Webhook Management Agent",)
        )

    if any(
        word in goal_lower
        for word in ("monitoring", "logging", "observability", "datadog", "sentry")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:observability",
            ("Monitoring & Logging Agent", "Lighthouse Performance Agent"),
        )

    if any(
        word in goal_lower
        for word in ("secret management", "vault", "key rotation", "secrets vault")
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:secret_management",
            ("Secret Management Agent",),
        )

    if any(word in goal_lower for word in ("accessibility", "a11y", "wcag", "aria")):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:accessibility",
            ("Accessibility Audit Agent",),
        )

    if any(word in goal_lower for word in ("braintree", "payment", "billing", "checkout")):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:payments",
            ("Braintree Integration Agent", "Subscription Management Agent"),
        )

    if any(
        word in goal_lower
        for word in (
            "realtime",
            "real-time",
            "collaboration",
            "shared presence",
            "socket.io",
            "websocket",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:realtime_collaboration",
            ("Real-Time Collaboration Agent",),
        )

    if any(
        word in goal_lower
        for word in (
            "adr",
            "architecture decision",
            "decision record",
            "technical decision",
        )
    ):
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:architecture_decisions",
            ("Architecture Decision Records Agent",),
        )

    if legacy_broad_agent_support_enabled():
        _record_rule_hit(
            selected,
            matched_rules,
            "rule:default_support_legacy",
            DEFAULT_SUPPORT_AGENTS,
        )
    selected = _dependency_closure(selected)
    cap = agent_selection_hard_cap()
    # Explicit 3D / WebGL render stack (Three.js, etc.) must keep specialized agents;
    # the hard cap is for generic SaaS noise, not real-time 3D work.
    explicit_render_stack = bool(
        set(matched_keywords) & RENDER_STACK_SELECTION_KEYWORDS
    )
    # Full-system contract explicitly opts into broad DAG — do not trim (still warn in planner).
    if (
        cap
        and not contract.get("requires_full_system_builder")
        and not explicit_render_stack
    ):
        selected = _apply_hard_agent_cap(selected, cap, matched_rules)
    selected_agents = sorted(selected)
    specialized_agents = sorted(
        agent for agent in selected_agents if agent not in ALWAYS_INCLUDED_AGENT_SET
    )
    return {
        "selected_agents": selected_agents,
        "selected_agent_count": len(selected_agents),
        "matched_keywords": matched_keywords,
        "matched_rules": matched_rules,
        "specialized_agents": specialized_agents,
        "specialized_agent_count": len(specialized_agents),
        "stack_profile": stack_profile_from_contract(contract),
        "directory_profile": directory_profile_from_contract(contract),
    }


def select_agents_for_goal(goal: str, stack_contract: Dict | None = None) -> List[str]:
    return list(
        explain_agent_selection(goal, stack_contract).get("selected_agents") or []
    )


def should_route_to_agent_selection(
    goal: str, stack_contract: Dict | None = None
) -> bool:
    """
    Route to selected-agent swarm when non-cosmetic rules fire, ignoring keyword:* hits
    that are common in generic fullstack specs (ROUTING_NOISE_KEYWORDS).

    Phrase-based rules (rule:*) still signal real specialized intent (e.g. blockchain,
    enterprise compliance, realtime collaboration).
    """
    contract = stack_contract or {}
    if contract.get("requires_full_system_builder"):
        return True
    if (
        contract.get("mobile")
        or contract.get("queues")
        or contract.get("caches")
        or contract.get("payments")
        or contract.get("realtime")
        or contract.get("vector_databases")
    ):
        return True
    explanation = explain_agent_selection(goal, contract)
    COSMETIC_ONLY_RULES = {
        "rule:design_surface",
        "rule:content_surface",
        "rule:default_support",
        "rule:default_support_legacy",
    }
    meaningful_rules: List[str] = []
    for r in explanation.get("matched_rules") or []:
        if r in COSMETIC_ONLY_RULES:
            continue
        if r.startswith("keyword:"):
            kw = r.split(":", 1)[1]
            if kw in ROUTING_NOISE_KEYWORDS:
                continue
        meaningful_rules.append(r)
    # Keyword hits expand the agent set even when _record_rule_hit did not add a rule
    # (e.g. agents were already covered by BASE_AGENTS + deps).
    meaningful_keywords = [
        k
        for k in (explanation.get("matched_keywords") or [])
        if k not in ROUTING_NOISE_KEYWORDS
    ]
    return bool(meaningful_keywords) or len(meaningful_rules) > 0


def build_full_phases_from_dag(
    selected_agents: List[str], agent_dag: Dict
) -> List[List[str]]:
    filtered_dag = {
        name: config
        for name, config in agent_dag.items()
        if name in set(selected_agents)
    }
    return get_execution_phases(filtered_dag)
