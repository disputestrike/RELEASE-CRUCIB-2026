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
    },
    "regulated_saas": {
        "label": "Regulated SaaS",
        "routes": ["/", "/dashboard", "/analytics", "/audit", "/settings", "/404"],
        "backend": ["tenant_isolation", "crm", "audit", "workers", "integrations", "compliance"],
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
}


def get_blueprint(build_class: str) -> Dict[str, Any]:
    """Return a defensive copy of the blueprint for ``build_class``."""

    return deepcopy(BLUEPRINTS.get(build_class) or {})
