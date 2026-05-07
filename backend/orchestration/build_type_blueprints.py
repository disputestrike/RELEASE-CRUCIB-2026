"""Build-type folder blueprints.

These blueprints are the product-shape layer between intent and generation.
They keep a plain website from becoming a SaaS scaffold, and they keep backend
or mobile jobs from being judged by frontend-only route contracts.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "web_marketing_site": {
        "label": "Public marketing website",
        "folders": [
            "src/components/ui",
            "src/components/navigation",
            "src/components/marketing",
            "src/pages",
            "src/layouts",
            "src/styles",
            "src/design",
            "src/data",
            "proof/screenshots",
        ],
        "routes": ["/", "/features", "/pricing", "/testimonials", "/404"],
        "required_sections": ["hero", "features", "pricing", "testimonials", "footer", "cta"],
        "required_files": [
            "ideas.md",
            "src/styles/tokens.css",
            "src/styles/global.css",
            "src/design/tokens.json",
            "src/layouts/MarketingLayout.jsx",
            "src/components/navigation/MarketingNav.jsx",
            "src/components/marketing/Footer.jsx",
            "src/components/marketing/HeroSection.jsx",
            "src/components/marketing/FeatureGrid.jsx",
            "src/components/marketing/PricingCards.jsx",
            "src/components/marketing/TestimonialGrid.jsx",
            "src/components/marketing/CTASection.jsx",
            "src/pages/HomePage.jsx",
            "src/pages/FeaturesPage.jsx",
            "src/pages/PricingPage.jsx",
            "src/pages/TestimonialsPage.jsx",
            "src/pages/NotFoundPage.jsx",
        ],
    },
    "saas_frontend": {
        "label": "SaaS/product frontend",
        "routes": ["/", "/dashboard", "/analytics", "/team", "/pricing", "/settings", "/404"],
        "required_sections": ["marketing hero", "dashboard KPIs", "analytics charts", "team management", "settings"],
    },
    "internal_admin_tool": {
        "label": "Internal admin tool",
        "folders": [
            "src/components/layout",
            "src/components/tables",
            "src/components/forms",
            "src/components/approvals",
            "src/components/ui",
            "src/pages",
            "src/styles",
            "src/data",
            "backend",
            "db/migrations",
            "tests",
            "proof/screenshots",
        ],
        "routes": ["/", "/records", "/forms", "/approvals", "/settings", "/404"],
        "required_sections": ["admin overview", "data table", "data-entry form", "approval queue", "settings"],
        "backend": ["health", "records", "forms", "approvals"],
        "database": ["records", "form_submissions", "approval_workflows", "approval_requests", "audit_events"],
    },
    "fullstack_saas": {
        "label": "Full-stack SaaS",
        "routes": ["/", "/dashboard", "/analytics", "/team", "/pricing", "/settings", "/404"],
        "backend": ["auth", "product_api", "billing", "database"],
        "database": ["users", "organizations", "subscriptions", "audit_events"],
        "proof": ["BUILD_CONTRACT", "API_ALIGNMENT", "AUTH_RBAC_PROOF", "SECURITY_REVIEW"],
    },
    "regulated_saas": {
        "label": "Regulated SaaS",
        "routes": ["/", "/dashboard", "/analytics", "/audit", "/settings", "/404"],
        "backend": ["tenant_isolation", "crm", "audit", "workers", "integrations", "compliance"],
        "database": ["users", "organizations", "audit_events", "consent_logs", "access_reviews"],
        "proof": ["COMPLIANCE_READINESS", "SECURITY_REVIEW", "AUTH_RBAC_PROOF", "DATABASE_PROOF"],
    },
    "api_backend": {
        "label": "API/backend",
        "routes": [],
        "backend": ["server_entry", "route_map", "schema", "tests", "openapi"],
    },
    "mobile_expo": {
        "label": "Expo mobile app",
        "routes": [],
        "mobile": ["App.tsx", "screens", "navigation", "app.json", "eas.json"],
    },
    "automation": {
        "label": "Automation/workflow",
        "routes": [],
        "automation": ["workflow_schema", "triggers", "actions", "executor", "run_history"],
    },
    "automation_workflow": {
        "label": "Automation/workflow",
        "routes": ["/", "/workflows", "/runs", "/settings"],
        "backend": ["workflow_executor", "trigger_registry", "action_registry", "run_history"],
        "database": ["workflow_definitions", "workflow_runs", "workflow_events"],
    },
    "ecommerce": {
        "label": "E-commerce application",
        "routes": ["/", "/products", "/cart", "/checkout", "/account", "/404"],
        "backend": ["catalog", "cart", "orders", "billing", "webhooks"],
        "database": ["users", "products", "carts", "orders", "order_items", "payment_events"],
        "proof": ["API_ALIGNMENT", "DATABASE_PROOF", "BUILD_RESULTS"],
    },
    "marketplace": {
        "label": "Marketplace platform",
        "routes": ["/", "/marketplace", "/seller", "/cart", "/checkout", "/account", "/404"],
        "backend": ["listings", "orders", "payouts", "disputes", "billing"],
        "database": ["users", "sellers", "listings", "orders", "order_items", "payouts", "disputes"],
        "proof": ["API_ALIGNMENT", "DATABASE_PROOF", "SECURITY_REVIEW"],
    },
    "healthcare_platform": {
        "label": "Healthcare platform",
        "routes": ["/", "/patients", "/encounters", "/audit", "/settings", "/404"],
        "backend": ["auth", "rbac", "patient_records", "audit", "consent"],
        "database": ["users", "patients", "encounters", "consents", "phi_access_log", "audit_events"],
        "proof": ["COMPLIANCE_READINESS", "AUTH_RBAC_PROOF", "SECURITY_REVIEW", "DATABASE_PROOF"],
    },
    "fintech_platform": {
        "label": "Fintech platform",
        "routes": ["/", "/dashboard", "/accounts", "/ledger", "/payments", "/audit", "/404"],
        "backend": ["auth", "rbac", "accounts", "ledger", "payments", "audit"],
        "database": ["users", "accounts", "ledger_lines", "payment_events", "audit_events"],
        "proof": ["COMPLIANCE_READINESS", "API_ALIGNMENT", "SECURITY_REVIEW", "DATABASE_PROOF"],
    },
    "govtech_platform": {
        "label": "Government technology platform",
        "routes": ["/", "/dashboard", "/cases", "/reports", "/audit", "/settings", "/404"],
        "backend": ["auth", "rbac", "case_management", "audit", "reporting"],
        "database": ["users", "cases", "case_events", "reports", "audit_events"],
    },
    "defense_enterprise_system": {
        "label": "Defense enterprise system",
        "routes": ["/", "/dashboard", "/operations", "/audit", "/settings", "/404"],
        "backend": ["auth", "rbac", "operations", "audit", "incident_response"],
        "database": ["users", "operations", "operation_events", "audit_events", "access_reviews"],
    },
    "ai_agent_platform": {
        "label": "AI agent platform",
        "routes": ["/", "/agents", "/runs", "/tools", "/proof", "/settings", "/404"],
        "backend": ["agents", "tool_registry", "runs", "proof", "audit"],
        "database": ["users", "agents", "agent_runs", "tool_calls", "proof_events"],
    },
}


def get_blueprint(build_class: str) -> Dict[str, Any]:
    """Return a defensive copy of the blueprint for ``build_class``."""

    return deepcopy(BLUEPRINTS.get(build_class) or {})
