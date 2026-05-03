"""
BuildContractGenerator - Synthesizes contracts from intent dimensions.

No template selection.
No domain registry.
Pure synthesis from dimensions.
"""

from typing import Dict, List, Any, Optional
from .build_contract import BuildContract, ContractDelta
from .intent_classifier import IntentDimensions


class BuildContractGenerator:
    """
    Generates BuildContract FROM IntentDimensions.
    
    This is synthesis, not template selection.
    The contract is constructed piece by piece from the dimensions.
    """
    
    def generate(self, dimensions: IntentDimensions, prompt: str, build_id: str) -> BuildContract:
        """
        Generate a complete BuildContract from intent dimensions.
        
        Args:
            dimensions: IntentDimensions from classifier
            prompt: Original user prompt
            build_id: Unique build identifier
            
        Returns:
            BuildContract in "draft" status (not yet approved/frozen)
        """
        dims = dimensions.values
        
        # Build the contract piece by piece from dimensions
        contract = BuildContract(
            build_id=build_id,
            version=1,
            status="draft",
            build_class=self._determine_build_class(dims),
            product_name=self._extract_product_name(prompt),
            original_goal=prompt,
            dimensions=dims,
            stack=self._synthesize_stack(dims),
            
            # Synthesize all required artifacts from dimensions
            required_files=self._synthesize_files(dims),
            required_folders=self._synthesize_folders(dims),
            required_routes=self._synthesize_routes(dims),
            required_pages=self._synthesize_pages(dims),
            required_backend_modules=self._synthesize_backend_modules(dims),
            required_api_endpoints=self._synthesize_api_endpoints(dims),
            required_database_tables=self._synthesize_database_tables(dims),
            required_migrations=self._synthesize_migrations(dims),
            required_workers=self._synthesize_workers(dims),
            required_integrations=self._synthesize_integrations(dims),
            required_tests=self._synthesize_tests(dims),
            required_docs=self._synthesize_docs(dims),
            
            # Visual QA requirements
            required_preview_routes=self._synthesize_preview_routes(dims),
            required_visual_checks=self._synthesize_visual_checks(dims),
            required_mobile_viewports=self._synthesize_mobile_viewports(dims),
            required_screenshots=self._synthesize_screenshots(dims),
            required_deploy_artifacts=self._synthesize_deploy_artifacts(dims),
            required_proof_types=self._synthesize_proof_types(dims),
            
            # Forbidden patterns
            forbidden_patterns=self._synthesize_forbidden_patterns(dims),
            forbidden_providers=self._synthesize_forbidden_providers(dims),
            
            # Verification
            verifiers_required=self._synthesize_verifiers(dims),
            verifiers_blocking=self._synthesize_blocking_verifiers(dims),
            
            # Repair routing
            repair_routes=self._synthesize_repair_routes(dims),
            
            # Scoring
            scoring_weights=self._default_scoring_weights(),
            minimum_score=85,
            hard_cap_rules=self._default_hard_cap_rules(),
            
            # Export policy
            export_policy=self._synthesize_export_policy(dims),
            
            # Goal success criteria
            goal_success_criteria=self._synthesize_goal_criteria(dims, prompt),
            
            # Progress tracking (starts empty)
            contract_progress=self._init_contract_progress(dims),
            
            # Approval policy
            approval_policy={
                "auto_approve": dimensions.auto_approve,
                "requires_human_approval": not dimensions.auto_approve,
                "risk_factors": dimensions.risk_factors,
                "approval_checkpoints": ["contract_generated", "before_heavy_generation"]
            }
        )
        
        return contract
    
    def _determine_build_class(self, dims: Dict) -> str:
        """Determine build class from dimensions (emergent, not from registry)."""
        if dims.get("internal_admin"):
            return "internal_admin_tool"
        if dims.get("marketing_site"):
            return "web_marketing_site"
        if dims.get("game"):
            return "game_2d" if dims.get("2d") else "game_3d"
        elif dims.get("cli"):
            return "cli_tool"
        elif dims.get("mobile"):
            return "mobile_react_native" if dims.get("react") else "mobile_flutter"
        elif dims.get("api") and not dims.get("frontend"):
            return "api_rest"
        elif dims.get("data_pipeline"):
            return "data_pipeline"
        elif dims.get("tenancy") and dims.get("compliance"):
            return "regulated_saas"
        elif dims.get("crm") or dims.get("analytics"):
            return "saas"
        elif dims.get("frontend"):
            return "web_app"
        else:
            return "generic"
    
    def _extract_product_name(self, prompt: str) -> str:
        """Extract product name from prompt, or generate default."""
        # Look for quoted names or "Name - description" pattern
        import re
        prompt = re.sub(r"^\s*build\s+", "", prompt or "", flags=re.IGNORECASE).strip()
        lower = (prompt or "").lower()

        if any(k in lower for k in ("internal admin", "admin tool", "admin panel", "internal tool")):
            return "Internal Admin Tool"
        if any(k in lower for k in ("marketing site", "landing page", "website", "hero", "features", "testimonials")):
            return "Marketing Website"
        
        # Try "Name - " or "Name — " pattern
        match = re.search(r'^([\w\s]+)[\-—]', prompt)
        if match:
            return match.group(1).strip()
        
        # Try "Build Name " pattern
        match = re.search(r'Build\s+([\w\s]+?)(?:\s|$)', prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return "Untitled Project"
    
    def _synthesize_stack(self, dims: Dict) -> Dict[str, str]:
        """Synthesize stack from dimensions."""
        stack = {}

        if dims.get("marketing_site"):
            return {
                "frontend": "React+Vite",
                "styling": "CSS tokens",
                "routing": "browser-addressable public routes",
            }
        if dims.get("internal_admin"):
            return {
                "frontend": "React+Vite",
                "backend": dims.get("backend_framework") or "FastAPI",
                "database": dims.get("database_engine") or "PostgreSQL",
                "styling": "CSS tokens",
                "routing": "browser-addressable admin routes",
            }
        
        # Frontend
        if dims.get("frontend"):
            stack["frontend"] = dims.get("frontend_framework") or "React+TypeScript"
        
        # Backend
        if dims.get("backend"):
            stack["backend"] = dims.get("backend_framework") or "FastAPI"
        elif dims.get("api"):
            stack["backend"] = "FastAPI"
        
        # Database
        if dims.get("database"):
            stack["database"] = dims.get("database_engine") or "PostgreSQL"
        
        # Queue
        if dims.get("workers") or dims.get("real_time"):
            stack["queue"] = dims.get("queue", "Redis")
        
        # Deployment
        if dims.get("deployment") or dims.get("docker"):
            stack["deployment"] = "Docker"
        
        return stack
    
    def _synthesize_files(self, dims: Dict) -> List[str]:
        """Synthesize required files from dimensions."""
        files = []

        if dims.get("marketing_site"):
            sections = set(dims.get("marketing_sections") or [])
            files.extend([
                "package.json",
                "index.html",
                "vite.config.js",
                "README.md",
                "ideas.md",
                "src/main.jsx",
                "src/App.jsx",
                "src/routes.jsx",
                "src/styles/tokens.css",
                "src/styles/global.css",
                "src/design/tokens.json",
                "src/data/siteContent.js",
                "src/layouts/MarketingLayout.jsx",
                "src/components/navigation/MarketingNav.jsx",
                "src/components/marketing/Footer.jsx",
                "src/components/marketing/CTASection.jsx",
                "src/pages/HomePage.jsx",
                "src/pages/FeaturesPage.jsx",
                "src/pages/PricingPage.jsx",
                "src/pages/TestimonialsPage.jsx",
                "src/pages/NotFoundPage.jsx",
            ])
            if "hero" in sections or not sections:
                files.append("src/components/marketing/HeroSection.jsx")
            if "features" in sections or not sections:
                files.append("src/components/marketing/FeatureGrid.jsx")
            if "pricing" in sections or not sections:
                files.append("src/components/marketing/PricingCards.jsx")
            if "testimonials" in sections or not sections:
                files.append("src/components/marketing/TestimonialGrid.jsx")
            files.extend([
                "src/components/ui/Button.jsx",
                "src/components/ui/Card.jsx",
                "src/components/ui/Container.jsx",
                "src/components/ui/Section.jsx",
            ])
            if not (
                dims.get("backend")
                or dims.get("api")
                or dims.get("database")
                or dims.get("workers")
                or dims.get("integrations")
                or dims.get("deployment")
                or dims.get("docker")
            ):
                return files

        if dims.get("internal_admin"):
            return [
                "package.json",
                "index.html",
                "vite.config.js",
                "README.md",
                "src/main.jsx",
                "src/App.jsx",
                "src/styles/tokens.css",
                "src/styles/global.css",
                "src/data/adminData.js",
                "src/components/layout/AdminShell.jsx",
                "src/components/tables/DataTable.jsx",
                "src/components/forms/AdminRecordForm.jsx",
                "src/components/approvals/ApprovalQueue.jsx",
                "src/components/ui/Button.jsx",
                "src/components/ui/Card.jsx",
                "src/components/ui/Input.jsx",
                "src/components/ui/Select.jsx",
                "src/pages/AdminDashboardPage.jsx",
                "src/pages/RecordsPage.jsx",
                "src/pages/FormsPage.jsx",
                "src/pages/ApprovalsPage.jsx",
                "src/pages/SettingsPage.jsx",
                "src/pages/NotFoundPage.jsx",
                "backend/main.py",
                "backend/requirements.txt",
                "db/migrations/001_initial.sql",
                "tests/test_app.py",
            ]
        
        # Entry points
        if dims.get("frontend") and not dims.get("marketing_site"):
            files.extend([
                "client/src/main.tsx",
                "client/src/App.tsx",
                "client/src/index.css",
                "client/index.html",
                "client/package.json",
                "client/vite.config.ts"
            ])
        
        # Backend entry
        if dims.get("backend") or dims.get("api"):
            files.extend([
                "backend/main.py",
                "backend/requirements.txt"
            ])
        
        # Database
        if dims.get("database"):
            files.append("backend/db/schema.py")
        
        # Workers
        if dims.get("workers"):
            files.extend([
                "backend/workers/job_queue.py",
                "backend/workers/handlers.py"
            ])
        
        # Integrations
        if dims.get("integrations"):
            files.extend([
                "backend/integrations/adapter.py",
                "backend/integrations/webhook.py"
            ])
        
        # Deployment
        if dims.get("deployment") or dims.get("docker"):
            files.extend([
                "Dockerfile",
                "docker-compose.yml"
            ])
        
        # Documentation
        files.append("README.md")
        if (dims.get("backend") or dims.get("api")) and "Dockerfile" not in files:
            files.append("Dockerfile")
        
        return files
    
    def _synthesize_folders(self, dims: Dict) -> List[str]:
        """Synthesize required folder structure."""
        if dims.get("marketing_site"):
            return [
                "src/components/ui",
                "src/components/navigation",
                "src/components/marketing",
                "src/pages",
                "src/layouts",
                "src/styles",
                "src/design",
                "src/data",
                "proof/screenshots",
            ]

        if dims.get("internal_admin"):
            return [
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
            ]

        folders = [
            "client/src/components",
            "client/src/pages",
            "client/src/hooks",
            "client/src/lib",
            "backend/routes",
            "backend/models",
            "backend/middleware"
        ]
        
        if dims.get("crm"):
            folders.extend(["backend/crm", "client/src/pages/CRM"])
        
        if dims.get("analytics"):
            folders.extend(["backend/analytics", "client/src/pages/Analytics"])
        
        if dims.get("integrations"):
            folders.append("backend/integrations")
        
        return folders
    
    def _synthesize_routes(self, dims: Dict) -> List[str]:
        """Synthesize required routes."""
        if dims.get("marketing_site"):
            return ["/", "/features", "/pricing", "/testimonials", "/404"]
        if dims.get("internal_admin"):
            return ["/", "/records", "/forms", "/approvals", "/settings", "/404"]

        routes = ["/", "/404"]
        
        if dims.get("auth"):
            routes.extend(["/login", "/register"])
        
        if dims.get("dashboard") or dims.get("analytics"):
            routes.append("/dashboard")
        
        if dims.get("crm"):
            routes.extend(["/crm", "/crm/accounts", "/crm/contacts", "/crm/deals"])
        
        if dims.get("settings") or dims.get("tenancy"):
            routes.append("/settings")
        
        if dims.get("billing") or dims.get("payment"):
            routes.append("/billing")
        
        return routes
    
    def _synthesize_pages(self, dims: Dict) -> List[str]:
        """Synthesize required page components."""
        if dims.get("marketing_site"):
            return ["Home", "Features", "Pricing", "Testimonials", "NotFound"]
        if dims.get("internal_admin"):
            return ["AdminDashboard", "Records", "Forms", "Approvals", "Settings", "NotFound"]

        pages = ["Home", "NotFound"]
        
        if dims.get("auth"):
            pages.extend(["Login", "Register"])
        
        if dims.get("dashboard"):
            pages.append("Dashboard")
        
        if dims.get("crm"):
            pages.extend(["CRM", "Accounts", "Contacts", "Deals"])
        
        if dims.get("analytics"):
            pages.append("Analytics")
        
        if dims.get("settings"):
            pages.append("Settings")
        
        if dims.get("billing"):
            pages.append("Billing")
        
        return pages
    
    def _synthesize_backend_modules(self, dims: Dict) -> List[str]:
        """Synthesize required backend modules."""
        if dims.get("marketing_site") and not (dims.get("backend") or dims.get("api")):
            return []
        if dims.get("internal_admin"):
            return ["health", "records", "forms", "approvals"]

        modules = ["auth", "health"]
        if dims.get("marketing_site"):
            modules = ["health", "lead_capture"]
        
        if dims.get("tenancy"):
            modules.append("tenancy")
        
        if dims.get("crm"):
            modules.append("crm")
        
        if dims.get("analytics"):
            modules.append("analytics")
        
        if dims.get("compliance"):
            modules.extend(["audit", "compliance"])
        
        if dims.get("workers"):
            modules.append("jobs")
        
        if dims.get("integrations"):
            modules.append("integrations")
        
        if dims.get("billing"):
            modules.append("billing")
        
        return modules
    
    def _synthesize_api_endpoints(self, dims: Dict) -> List[str]:
        """Synthesize required API endpoints."""
        if dims.get("marketing_site") and not (dims.get("backend") or dims.get("api")):
            return []
        if dims.get("internal_admin"):
            return [
                "/api/health",
                "/api/records",
                "/api/forms",
                "/api/approvals",
                "/api/audit-events",
            ]

        endpoints = ["/api/health"]
        
        if dims.get("auth"):
            endpoints.extend([
                "/api/auth/login",
                "/api/auth/register",
                "/api/auth/logout",
                "/api/auth/me"
            ])
        
        if dims.get("crm"):
            endpoints.extend([
                "/api/accounts",
                "/api/contacts",
                "/api/deals",
                "/api/activities"
            ])
        
        if dims.get("analytics"):
            endpoints.extend([
                "/api/analytics/dashboard",
                "/api/analytics/reports"
            ])
        
        return endpoints
    
    def _synthesize_database_tables(self, dims: Dict) -> List[str]:
        """Synthesize required database tables."""
        if dims.get("marketing_site") and not dims.get("database"):
            return []
        if dims.get("internal_admin"):
            return [
                "users",
                "records",
                "form_submissions",
                "approval_workflows",
                "approval_requests",
                "audit_events",
            ]
        if not (
            dims.get("database") or dims.get("auth") or dims.get("tenancy") or dims.get("crm") or dims.get("compliance")
        ):
            return []

        tables = ["form_submissions", "subscribers"] if dims.get("marketing_site") else ["users"]
        
        if dims.get("tenancy"):
            tables.extend(["organizations", "workspaces", "projects"])
        
        if dims.get("crm"):
            tables.extend(["accounts", "contacts", "deals", "activities", "tasks"])
        
        if dims.get("compliance"):
            tables.extend(["audit_events", "consent_logs"])
        
        if dims.get("workers"):
            tables.extend(["jobs", "job_logs"])
        
        if dims.get("integrations"):
            tables.extend(["integrations", "webhooks"])
        
        return tables
    
    def _synthesize_migrations(self, dims: Dict) -> List[str]:
        """Synthesize required migration files."""
        if not self._synthesize_database_tables(dims):
            return []

        # One per major table group
        migrations = ["001_initial.sql", "002_users.sql"]
        
        if dims.get("tenancy"):
            migrations.append("003_tenancy.sql")
        
        if dims.get("crm"):
            migrations.append("004_crm.sql")
        
        if dims.get("compliance"):
            migrations.append("005_audit.sql")
        
        return migrations
    
    def _synthesize_workers(self, dims: Dict) -> List[str]:
        """Synthesize required background workers."""
        if not dims.get("workers"):
            return []
        
        return [
            "email_digest",
            "report_generation",
            "webhook_retry",
            "data_sync"
        ]
    
    def _synthesize_integrations(self, dims: Dict) -> List[str]:
        """Synthesize required integrations."""
        if not dims.get("integrations"):
            return []
        
        return [
            "rest_connector",
            "webhook_handler"
        ]
    
    def _synthesize_tests(self, dims: Dict) -> List[str]:
        """Synthesize required tests."""
        if dims.get("marketing_site"):
            return ["test_build", "test_routes", "test_visual_sections"]
        if dims.get("internal_admin"):
            return ["test_build", "test_admin_routes", "test_api_contract", "test_database_schema"]

        tests = ["test_health"]
        
        if dims.get("auth"):
            tests.append("test_auth")
        
        if dims.get("tenancy"):
            tests.append("test_tenant_isolation")
        
        if dims.get("api"):
            tests.append("test_api_contracts")
        
        return tests
    
    def _synthesize_docs(self, dims: Dict) -> List[str]:
        """Synthesize required documentation."""
        if dims.get("marketing_site"):
            return ["README.md", "ideas.md"]
        if dims.get("internal_admin"):
            return ["README.md", "ARCHITECTURE.md", "DATA_MODEL.md"]

        return ["README.md", "ARCHITECTURE.md", ".env.example"]
    
    def _synthesize_preview_routes(self, dims: Dict) -> List[str]:
        """Synthesize routes that need screenshot/preview."""
        if dims.get("api") and not dims.get("frontend"):
            return []
        if dims.get("cli"):
            return []
        if dims.get("marketing_site"):
            return ["/", "/features", "/pricing", "/testimonials", "/404"]
        if dims.get("internal_admin"):
            return ["/", "/records", "/forms", "/approvals", "/settings"]

        routes = ["/"]
        
        if dims.get("auth"):
            routes.append("/login")
        
        if dims.get("dashboard"):
            routes.append("/dashboard")
        
        if dims.get("crm"):
            routes.append("/crm")
        
        return routes
    
    def _synthesize_visual_checks(self, dims: Dict) -> List[str]:
        """Synthesize visual QA checks."""
        if dims.get("api") and not dims.get("frontend"):
            return []
        if dims.get("cli"):
            return []
        if dims.get("marketing_site"):
            return [
                "no_blank_screen",
                "nav_visible",
                "hero_visible",
                "features_visible",
                "pricing_visible",
                "testimonials_visible",
                "footer_visible",
                "monochrome_tokens_only",
                "mobile_viewport_ok",
            ]
        if dims.get("internal_admin"):
            return [
                "no_blank_screen",
                "admin_nav_visible",
                "data_table_visible",
                "form_visible",
                "approval_queue_visible",
                "monochrome_tokens_only",
            ]

        return [
            "no_blank_screen",
            "nav_visible",
            "content_rendered"
        ]
    
    def _synthesize_mobile_viewports(self, dims: Dict) -> List[str]:
        """Synthesize mobile viewport requirements."""
        if dims.get("mobile") or dims.get("frontend"):
            return ["375x667", "768x1024", "1920x1080"]
        return []
    
    def _synthesize_screenshots(self, dims: Dict) -> List[str]:
        """Synthesize required screenshots."""
        return self._synthesize_preview_routes(dims)
    
    def _synthesize_deploy_artifacts(self, dims: Dict) -> List[str]:
        """Synthesize deployment requirements."""
        artifacts = []
        
        if dims.get("docker") or dims.get("deployment"):
            artifacts.extend(["Dockerfile", "docker-compose.yml"])
        
        return artifacts
    
    def _synthesize_proof_types(self, dims: Dict) -> List[str]:
        """Synthesize required proof types."""
        if dims.get("marketing_site"):
            return [
                "build_pass",
                "preview_pass",
                "routes_proven",
                "screenshot_valid",
                "goal_satisfied",
            ]
        if dims.get("internal_admin"):
            return [
                "build_pass",
                "preview_pass",
                "routes_proven",
                "database_schema_present",
                "admin_sections_present",
                "goal_satisfied",
            ]

        proofs = ["build_pass", "syntax_ok"]
        
        if dims.get("frontend"):
            proofs.extend(["preview_pass", "routes_proven"])
        
        if dims.get("database"):
            proofs.append("database_proven")
        
        if dims.get("api"):
            proofs.append("api_contract_valid")
        
        return proofs
    
    def _synthesize_forbidden_patterns(self, dims: Dict) -> List[str]:
        """Synthesize forbidden patterns."""
        return [
            "Markdown inside .tsx",
            "placeholder deploy command",
            "hardcoded secrets",
            "client-supplied price"
        ]
    
    def _synthesize_forbidden_providers(self, dims: Dict) -> List[str]:
        """Synthesize forbidden providers."""
        if dims.get("billing"):
            return ["Stripe", "Braintree"]
        return []
    
    def _synthesize_verifiers(self, dims: Dict) -> List[str]:
        """Synthesize required verifiers."""
        verifiers = ["syntax_check", "import_check"]
        
        if dims.get("frontend"):
            verifiers.extend(["build_check", "preview_check", "route_check"])
        
        if dims.get("database"):
            verifiers.append("database_check")
        
        if dims.get("api"):
            verifiers.append("api_contract_check")
        
        return verifiers
    
    def _synthesize_blocking_verifiers(self, dims: Dict) -> List[str]:
        """Synthesize verifiers that block export if failed."""
        return ["build_check", "security_check", "export_gate"]
    
    def _synthesize_repair_routes(self, dims: Dict) -> Dict[str, List[str]]:
        """Synthesize error-to-repair-agent routing."""
        return {
            "syntax_error": ["SyntaxRepairAgent"],
            "import_error": ["ImportRepairAgent", "IntegrationAgent"],
            "build_error": ["BuildRepairAgent"],
            "missing_component": ["ComponentGeneratorAgent"],
            "contract_violation": ["ContractRepairAgent"]
        }
    
    def _default_scoring_weights(self) -> Dict[str, float]:
        """Default scoring weights."""
        return {
            "generic_agent_log": 0.0,
            "file_exists": 1.0,
            "syntax_ok": 2.0,
            "import_resolves": 2.0,
            "build_pass": 15.0,
            "preview_pass": 15.0,
            "route_proven": 10.0,
            "database_proven": 10.0,
            "test_pass": 10.0,
            "screenshot_valid": 10.0,
            "visual_check_pass": 10.0,
            "goal_satisfied": 20.0
        }
    
    def _default_hard_cap_rules(self) -> List[Dict]:
        """Default hard-cap scoring rules."""
        return [
            {"condition": "build_failed", "max_score": 35},
            {"condition": "preview_failed", "max_score": 40},
            {"condition": "routes_empty", "max_score": 50},
            {"condition": "database_empty_when_required", "max_score": 50},
            {"condition": "blocking_verifier_failed", "success": False},
            {"condition": "export_gate_failed", "success": False}
        ]
    
    def _synthesize_export_policy(self, dims: Dict) -> Dict[str, Any]:
        """Synthesize export policy."""
        return {
            "allow_export_if_failed": False,
            "minimum_score": 85,
            "required_green_gates": [
                "build_pass",
                "preview_pass" if dims.get("frontend") else None,
                "required_routes_present" if dims.get("frontend") else None,
                "required_database_present" if dims.get("database") else None
            ]
        }
    
    def _synthesize_goal_criteria(self, dims: Dict, prompt: str) -> List[Dict]:
        """Synthesize goal success criteria from dimensions."""
        criteria = []

        if dims.get("marketing_site"):
            sections = dims.get("marketing_sections") or ["hero", "features", "pricing", "testimonials", "footer"]
            return [
                {
                    "criterion": f"section_{section}",
                    "test": f"{section} content is present, visible, and styled with shared tokens",
                    "priority": "high",
                }
                for section in sections
            ]
        if dims.get("internal_admin"):
            return [
                {
                    "criterion": "records_table",
                    "test": "Records/data table is mounted and visible from a browser route",
                    "priority": "high",
                },
                {
                    "criterion": "admin_form",
                    "test": "A working data-entry form surface is mounted and visible",
                    "priority": "high",
                },
                {
                    "criterion": "approval_workflow",
                    "test": "Approval queue/workflow surface is mounted and visible",
                    "priority": "high",
                },
                {
                    "criterion": "database_contract",
                    "test": "Database tables/migration exist for records, submissions, approvals, and audit events",
                    "priority": "high",
                },
            ]
        
        if dims.get("tenancy"):
            criteria.append({
                "criterion": "tenant_isolation",
                "test": "Create two tenants, verify data isolation",
                "priority": "critical"
            })
        
        if dims.get("crm"):
            criteria.append({
                "criterion": "crm_functionality",
                "test": "CRUD operations on accounts, contacts, deals",
                "priority": "high"
            })
        
        if dims.get("auth"):
            criteria.append({
                "criterion": "auth_system",
                "test": "Register, login, access protected route, logout",
                "priority": "critical"
            })
        
        return criteria
    
    def _init_contract_progress(self, dims: Dict) -> Dict:
        """Initialize contract progress tracking."""
        progress = {
            "required_files": {"done": [], "missing": [], "percent": 0},
            "required_routes": {"done": [], "missing": [], "percent": 0},
            "required_backend_modules": {"done": [], "missing": [], "percent": 0},
            "required_database_tables": {"done": [], "missing": [], "percent": 0},
            "required_workers": {"done": [], "missing": [], "percent": 0},
            "required_integrations": {"done": [], "missing": [], "percent": 0},
            "required_tests": {"done": [], "missing": [], "percent": 0},
            "required_preview_routes": {"done": [], "missing": [], "percent": 0}
        }
        
        # Pre-populate "missing" with all required items
        for file in self._synthesize_files(dims):
            progress["required_files"]["missing"].append(file)
        
        for route in self._synthesize_routes(dims):
            progress["required_routes"]["missing"].append(route)
        
        for table in self._synthesize_database_tables(dims):
            progress["required_database_tables"]["missing"].append(table)

        for route in self._synthesize_preview_routes(dims):
            progress["required_preview_routes"]["missing"].append(route)

        for module in self._synthesize_backend_modules(dims):
            progress["required_backend_modules"]["missing"].append(module)

        for worker in self._synthesize_workers(dims):
            progress["required_workers"]["missing"].append(worker)

        for integration in self._synthesize_integrations(dims):
            progress["required_integrations"]["missing"].append(integration)

        for test in self._synthesize_tests(dims):
            progress["required_tests"]["missing"].append(test)
        
        return progress
