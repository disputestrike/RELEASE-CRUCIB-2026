"""
IntentClassifier - Decomposes user prompts into dimensions.

No domain registry lookups.
No template selection.
Pure synthesis from intent.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import json
import re


@dataclass
class IntentDimensions:
    """
    Multi-dimensional decomposition of user intent.
    
    This is NOT a domain_id. It is a vector of capabilities.
    """
    values: Dict[str, Any]
    auto_approve: bool = False
    risk_factors: List[str] = None
    uncertainty_flags: List[str] = None
    suggested_clarifications: List[str] = None
    
    def __post_init__(self):
        if self.risk_factors is None:
            self.risk_factors = []
        if self.uncertainty_flags is None:
            self.uncertainty_flags = []
        if self.suggested_clarifications is None:
            self.suggested_clarifications = []


class IntentClassifier:
    """
    Classifies intent by decomposing into dimensions.
    
    Does not select from a domain registry.
    Generates dimensions from prompt analysis.
    """
    
    # Keywords that map to dimensions
    DIMENSION_KEYWORDS = {
        # Tenancy
        "tenancy": ["multi-tenant", "multitenant", "tenant isolation", "org", "workspace", "organization"],
        
        # CRM
        "crm": ["crm", "customer", "contact", "lead", "deal", "account", "pipeline", "opportunity"],
        
        # Compliance
        "compliance": ["gdpr", "hipaa", "soc2", "audit", "compliance", "regulatory", "policy"],
        
        # Workers/Background Jobs
        "workers": ["worker", "job queue", "background", "async", "scheduled", "cron", "batch"],
        
        # Real-time
        "real_time": ["websocket", "sse", "real-time", "live updates", "streaming"],
        
        # Integrations
        "integrations": ["integration", "api connector", "webhook", "oauth", "adapter"],
        
        # Analytics
        "analytics": ["analytics", "dashboard", "metrics", "reporting", "charts", "kpi"],
        
        # Auth
        "auth": ["auth", "login", "authentication", "jwt", "session", "sso", "oauth"],
        
        # Billing
        "billing": ["billing", "payment", "subscription", "stripe", "invoice", "pricing"],
        
        # Frontend
        "frontend": ["react", "vue", "angular", "frontend", "spa", "dashboard", "admin panel", "admin tool"],

        # Internal operations/admin tools
        "internal_admin": [
            "internal admin",
            "admin tool",
            "admin panel",
            "back office",
            "backoffice",
            "operations tool",
            "internal tool",
            "approval workflow",
            "approval workflows",
            "data tables",
            "table management",
            "forms",
        ],

        # Public / marketing websites
        "marketing_site": [
            "website",
            "web site",
            "multi-page website",
            "multipage website",
            "marketing site",
            "landing page",
            "homepage",
            "hero",
            "features grid",
            "feature grid",
            "pricing",
            "testimonials",
            "footer",
            "public site",
            "portfolio",
            "storefront",
        ],
        
        # Backend
        "backend": ["fastapi", "express", "django", "backend", "api", "rest", "graphql", "collect emails", "newsletter signup", "form submission", "admin tool", "approval workflow", "approval workflows", "node", "nodejs", "node.js"],

        # Explicit language requests
        "language_python": ["python", "fastapi", "django", "flask", "py "],
        "language_node": ["node.js", "nodejs", "express", "nestjs", "javascript backend"],
        "language_go": [" golang", "go ", "go,", "gin framework", "echo framework"],
        "language_rust": ["rust", "cargo", "actix", "rocket web"],
        "language_cpp": ["c++", "cpp", "g++", "cmake", "clang"],
        "language_c": [" c programming", "gcc", "makefile"],
        
        # Database
        "database": ["database", "postgres", "mysql", "mongodb", "sqlite", "redis", "store signups", "collect data", "save emails", "subscribers", "data tables", "admin records", "form submissions"],
        
        # Mobile
        "mobile": ["mobile", "ios app", "android", "react native", "flutter", "expo"],
        
        # CLI. Keep this narrow: "tool" alone can mean a web/admin product.
        "cli": ["cli", "command line", "terminal", "shell script", "command-line tool", "command line tool"],
        
        # Game
        "game": ["game", "unity", "unreal", "godot", "phaser", "2d", "3d"],
        
        # Data Pipeline
        "data_pipeline": ["etl", "pipeline", "airflow", "spark", "data processing"]
    }
    
    # Risk factors that require human approval
    RISK_KEYWORDS = {
        "payment": ["payment", "billing", "stripe", "braintree", "transaction", "money"],
        "compliance": ["gdpr", "hipaa", "pci", "soc2", "regulatory", "audit"],
        "production_deploy": ["production", "deploy", "live", "customer-facing"],
        "security_critical": ["auth", "encryption", "security", "sensitive data"],
        "high_scale": ["million users", "enterprise", "scale", "high traffic"]
    }
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def classify(self, prompt: str) -> IntentDimensions:
        """
        Decompose prompt into dimensions.
        
        Returns IntentDimensions, not a domain_id.
        """
        prompt_lower = prompt.lower()
        
        # Extract dimensions from keywords
        dimensions = {}
        for dimension, keywords in self.DIMENSION_KEYWORDS.items():
            dimensions[dimension] = any(kw in prompt_lower for kw in keywords)
        
        # Detect specific patterns for richer dimensions
        dimensions.update(self._extract_specific_patterns(prompt))
        if "api" not in dimensions:
            dimensions["api"] = any(
                token in prompt_lower for token in (" api", "api ", "rest", "endpoint")
            )
        
        # Detect risk factors
        risk_factors = self._detect_risk_factors(prompt_lower)
        
        # Determine auto-approval
        auto_approve = len(risk_factors) == 0 and self._is_low_complexity(dimensions)
        
        # Detect uncertainties
        uncertainties = self._detect_uncertainties(prompt)
        
        return IntentDimensions(
            values=dimensions,
            auto_approve=auto_approve,
            risk_factors=risk_factors,
            uncertainty_flags=uncertainties,
            suggested_clarifications=self._generate_clarifications(dimensions, uncertainties)
        )
    
    def _extract_specific_patterns(self, prompt: str) -> Dict[str, Any]:
        """
        Extract specific patterns that enrich dimensions.
        """
        prompt_lower = prompt.lower()
        patterns = {}
        
        # Tenancy patterns
        if "org → workspace → project" in prompt_lower or "organization" in prompt_lower:
            patterns["tenancy_model"] = "org_workspace_project"
        elif "tenant" in prompt_lower:
            patterns["tenancy_model"] = "simple_tenant"
        
        # Database patterns
        if "postgres" in prompt_lower:
            patterns["database_engine"] = "PostgreSQL"
        elif "mysql" in prompt_lower:
            patterns["database_engine"] = "MySQL"
        elif "mongodb" in prompt_lower:
            patterns["database_engine"] = "MongoDB"
        elif "redis" in prompt_lower:
            patterns["queue"] = "redis"
        
        # Stack patterns
        if "fastapi" in prompt_lower:
            patterns["backend_framework"] = "FastAPI"
            patterns["backend_language"] = "python"
        elif "express" in prompt_lower or "node" in prompt_lower or "node.js" in prompt_lower:
            patterns["backend_framework"] = "Express"
            patterns["backend_language"] = "node.js"
        elif "django" in prompt_lower:
            patterns["backend_framework"] = "Django"
            patterns["backend_language"] = "python"
        elif "nestjs" in prompt_lower or "nest.js" in prompt_lower:
            patterns["backend_framework"] = "NestJS"
            patterns["backend_language"] = "node.js"
        elif "c++" in prompt_lower or "cpp" in prompt_lower or "cmake" in prompt_lower:
            patterns["backend_framework"] = "CMake/g++"
            patterns["backend_language"] = "cpp"
        elif "golang" in prompt_lower or " go " in prompt_lower or "go," in prompt_lower:
            patterns["backend_framework"] = "Gin/Echo"
            patterns["backend_language"] = "go"
        elif "rust" in prompt_lower or "cargo" in prompt_lower:
            patterns["backend_framework"] = "Actix/Rocket"
            patterns["backend_language"] = "rust"
        
        if "react" in prompt_lower:
            patterns["frontend_framework"] = "React"
            if "typescript" in prompt_lower or "ts" in prompt_lower:
                patterns["frontend_framework"] = "React+TypeScript"
        elif "vue" in prompt_lower:
            patterns["frontend_framework"] = "Vue"
        elif "angular" in prompt_lower:
            patterns["frontend_framework"] = "Angular"
        
        # Specific feature patterns
        marketing_sections = []
        for label, needles in {
            "hero": ("hero", "headline"),
            "features": ("features grid", "feature grid", "features", "benefits"),
            "pricing": ("pricing", "plans", "price"),
            "testimonials": ("testimonials", "testimonial", "customer quotes"),
            "footer": ("footer", "contact"),
            "cta": ("cta", "call to action", "conversion"),
        }.items():
            if any(needle in prompt_lower for needle in needles):
                marketing_sections.append(label)
        if marketing_sections:
            patterns["marketing_sections"] = sorted(set(marketing_sections))
            patterns["frontend_framework"] = patterns.get("frontend_framework") or "React"
            patterns["marketing_site"] = True

        if any(
            needle in prompt_lower
            for needle in (
                "internal admin",
                "admin tool",
                "admin panel",
                "internal tool",
                "back office",
                "backoffice",
                "data tables",
                "approval workflow",
                "approval workflows",
            )
        ):
            patterns["internal_admin"] = True
            patterns["frontend"] = patterns.get("frontend") or "React"
            patterns["backend"] = patterns.get("backend") or "FastAPI"
            patterns["database"] = patterns.get("database") or "PostgreSQL"
        if "form" in prompt_lower and patterns.get("internal_admin"):
            patterns["forms"] = True

        if "quote workflow" in prompt_lower or "approval" in prompt_lower:
            patterns["workflow_engine"] = True
        
        if "audit trail" in prompt_lower or "immutable" in prompt_lower:
            patterns["audit_system"] = True
        
        if "policy engine" in prompt_lower or "role-based" in prompt_lower:
            patterns["policy_engine"] = True
        
        if "mock erp" in prompt_lower or "integration adapter" in prompt_lower:
            patterns["integration_framework"] = True
        
        return patterns
    
    def _detect_risk_factors(self, prompt_lower: str) -> List[str]:
        """Detect risk factors that require human approval."""
        risks = []
        for risk_type, keywords in self.RISK_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                risks.append(risk_type)
        return risks
    
    def _is_low_complexity(self, dimensions: Dict[str, Any]) -> bool:
        """Determine if build is low complexity enough for auto-approval."""
        # Count enabled dimensions
        enabled = sum(1 for v in dimensions.values() if v is True)
        
        # Auto-approve if fewer than 5 major dimensions
        return enabled < 5
    
    def _detect_uncertainties(self, prompt: str) -> List[str]:
        """Detect ambiguous or missing information."""
        uncertainties = []
        
        # Check for missing stack specification
        prompt_lower = prompt.lower()
        is_public_site = any(
            word in prompt_lower
            for word in ["website", "web site", "landing page", "hero", "features", "pricing", "testimonials"]
        )
        is_internal_admin = any(
            word in prompt_lower
            for word in ["internal admin", "admin tool", "admin panel", "internal tool", "back office", "data tables"]
        )
        if not is_public_site and not is_internal_admin and not any(word in prompt_lower for word in ["react", "vue", "angular", "fastapi", "express", "django"]):
            uncertainties.append("frontend_framework_not_specified")
            uncertainties.append("backend_framework_not_specified")
        
        # Check for vague requirements
        if len(prompt.split()) < 20:
            uncertainties.append("prompt_too_short")
        
        # Check for missing auth specification
        if not is_public_site and not is_internal_admin and "auth" not in prompt_lower and "login" not in prompt_lower:
            uncertainties.append("auth_requirement_unclear")
        
        return uncertainties
    
    def _generate_clarifications(self, dimensions: Dict, uncertainties: List[str]) -> List[str]:
        """Generate clarifying questions for uncertainties."""
        questions = []
        
        if "frontend_framework_not_specified" in uncertainties:
            questions.append("What frontend framework? (React, Vue, Angular)")
        
        if "backend_framework_not_specified" in uncertainties:
            questions.append("What backend framework? (FastAPI, Express, Django)")
        
        if "auth_requirement_unclear" in uncertainties:
            questions.append("What authentication method? (email/password, OAuth, SSO)")
        
        if dimensions.get("tenancy") and not dimensions.get("tenancy_model"):
            questions.append("What tenancy model? (org/workspace/project, simple multi-tenant)")
        
        return questions


# Example classification for testing
if __name__ == "__main__":
    classifier = IntentClassifier()
    
    # Test Helios prompt
    helios_prompt = """Build Helios Operations Cloud — an elite autonomous multi-tenant B2B SaaS for regulated teams.

MULTI-TENANT & ISOLATION: Strict tenant isolation per organization (Org → Workspace → Project).
CRM & PIPELINES: Full CRM module (accounts, contacts, deals, activities, tasks).
COMPLIANCE & AUDIT: Immutable audit trail for security-relevant actions.
BACKGROUND JOBS & WORKERS: Worker/job system for long tasks.
INTEGRATION ADAPTERS: Pluggable integration adapters — REST connector framework.
ANALYTICS & REPORTING: Analytics/reporting dashboards.
PRODUCT SURFACES: React + TypeScript SPA, FastAPI backend, PostgreSQL, Redis.
DEPLOYMENT & OPS: Dockerized services."""
    
    result = classifier.classify(helios_prompt)
    print("Helios Classification:")
    print(f"  Dimensions: {result.values}")
    print(f"  Risk Factors: {result.risk_factors}")
    print(f"  Auto Approve: {result.auto_approve}")
    
    # Test API-only prompt
    api_prompt = "Build a REST API for user management with FastAPI and PostgreSQL"
    result2 = classifier.classify(api_prompt)
    print("\nAPI Classification:")
    print(f"  Dimensions: {result2.values}")
    print(f"  Auto Approve: {result2.auto_approve}")
