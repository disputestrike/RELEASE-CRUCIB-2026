"""
CrucibAI Workflows — 40+ named, one-click build sequences.
Each workflow maps a user intent to a specific agent subset + goal template.
Inspired by Everything Claude Code but running on 244 DAG agents instead of 14.
"""

from typing import Any, Dict, List, Optional

# ── Workflow registry ──────────────────────────────────────────────────────────
# Each workflow defines:
#   - name: display name
#   - description: what it does
#   - category: grouping for UI
#   - goal_template: injected into planner as the build goal
#   - agents: specific agents to prioritize (empty = use full DAG)
#   - requires_existing_code: whether it modifies existing workspace
#   - icon: emoji for UI

WORKFLOWS: Dict[str, Dict[str, Any]] = {

    # ── AUTH & IDENTITY ────────────────────────────────────────────────────────
    "add-auth": {
        "name": "Add Authentication",
        "description": "Add Google + GitHub OAuth, magic link email, JWT sessions, and RBAC",
        "category": "Auth & Identity",
        "icon": "🔐",
        "goal_template": "Add complete authentication to this application: Google OAuth, GitHub OAuth, magic link email login, JWT session management with refresh tokens, role-based access control (Owner/Admin/Member/Viewer), and account suspension logic. Wire to existing frontend and backend.",
        "agents": ["Auth Setup Agent", "OAuth Provider Agent", "RBAC Agent", "Session Agent", "2FA Agent", "Security Checker"],
        "requires_existing_code": True,
    },
    "add-2fa": {
        "name": "Add 2FA / MFA",
        "description": "Add TOTP two-factor authentication with QR code setup",
        "category": "Auth & Identity",
        "icon": "🔑",
        "goal_template": "Add TOTP two-factor authentication: QR code setup flow, authenticator app support, backup codes, enforce MFA for admin roles. Wire to existing auth system.",
        "agents": ["2FA Agent", "Auth Setup Agent", "Security Checker"],
        "requires_existing_code": True,
    },
    "add-sso": {
        "name": "Add SSO",
        "description": "Add SAML/OIDC single sign-on for enterprise customers",
        "category": "Auth & Identity",
        "icon": "🏢",
        "goal_template": "Add enterprise SSO: SAML 2.0 and OIDC support, IdP metadata upload, attribute mapping, JIT provisioning, per-tenant SSO configuration.",
        "agents": ["SSO Agent", "Auth Setup Agent", "Multi-tenant Agent"],
        "requires_existing_code": True,
    },

    # ── PAYMENTS & BILLING ─────────────────────────────────────────────────────
    "add-stripe": {
        "name": "Add Stripe Billing",
        "description": "Add Stripe subscriptions, usage-based billing, and dunning logic",
        "category": "Payments",
        "icon": "💳",
        "goal_template": "Add complete Stripe billing: subscription plans (free/pro/enterprise), usage-based metering, Stripe Checkout, customer portal, webhook handlers for payment events, dunning logic for failed payments, automatic account suspension after 3 failed charges.",
        "agents": ["Payment Setup Agent", "Stripe Integration Agent", "Stripe Subscription Agent", "Invoice Agent", "Webhook Agent"],
        "requires_existing_code": True,
    },
    "add-stripe-connect": {
        "name": "Add Stripe Connect",
        "description": "Let your users bill their own customers via Stripe Connect",
        "category": "Payments",
        "icon": "🏦",
        "goal_template": "Add Stripe Connect so platform users can bill their own customers: Connect account creation, OAuth flow, split payments, platform fee collection, payout management.",
        "agents": ["Payment Setup Agent", "Stripe Integration Agent", "OAuth Provider Agent"],
        "requires_existing_code": True,
    },

    # ── DATABASE ───────────────────────────────────────────────────────────────
    "add-database": {
        "name": "Add Database",
        "description": "Add PostgreSQL with Drizzle ORM, migrations, and seed data",
        "category": "Database",
        "icon": "🗄️",
        "goal_template": "Add PostgreSQL database with Drizzle ORM: complete schema based on app requirements, migrations, indexes, seed data, connection pooling, and database health checks.",
        "agents": ["Database Agent", "ORM Setup Agent", "Migration Agent", "Database Optimization Agent"],
        "requires_existing_code": False,
    },
    "add-realtime": {
        "name": "Add Real-time",
        "description": "Add WebSocket real-time updates, live cursors, and collaboration",
        "category": "Database",
        "icon": "⚡",
        "goal_template": "Add real-time functionality: WebSocket connections, live data updates, presence indicators, optimistic UI updates, conflict resolution for concurrent edits.",
        "agents": ["WebSocket Agent", "Real-Time Collaboration Agent", "Queue Agent"],
        "requires_existing_code": True,
    },

    # ── AI FEATURES ────────────────────────────────────────────────────────────
    "add-ai-chat": {
        "name": "Add AI Chat",
        "description": "Add a GPT-powered chat assistant to your app",
        "category": "AI Features",
        "icon": "🤖",
        "goal_template": "Add an AI chat assistant: streaming chat UI, conversation history, system prompt configuration, model selection (GPT-4/Claude/Llama), token usage tracking, rate limiting per user.",
        "agents": ["RAG Agent", "Memory Agent", "Embeddings/Vectorization Agent"],
        "requires_existing_code": True,
    },
    "add-rag": {
        "name": "Add RAG / Document Q&A",
        "description": "Add document upload, chunking, embedding, and Q&A",
        "category": "AI Features",
        "icon": "📚",
        "goal_template": "Add RAG pipeline: document upload (PDF/DOCX/TXT), chunking, embedding via OpenAI/Anthropic, pgvector storage, semantic search, Q&A with source citations, document management UI.",
        "agents": ["RAG Agent", "Embeddings/Vectorization Agent", "File Storage Agent", "Search Agent"],
        "requires_existing_code": True,
    },
    "add-recommendations": {
        "name": "Add Recommendations",
        "description": "Add ML-powered recommendation engine",
        "category": "AI Features",
        "icon": "✨",
        "goal_template": "Add recommendation engine: collaborative filtering, content-based filtering, hybrid model, A/B testing framework, recommendation API, and UI components.",
        "agents": ["Recommendation Engine Agent", "ML Framework Selector Agent", "A/B Test Agent"],
        "requires_existing_code": True,
    },

    # ── ADMIN & ANALYTICS ──────────────────────────────────────────────────────
    "add-admin-dashboard": {
        "name": "Add Admin Dashboard",
        "description": "Add full admin panel with user management and analytics",
        "category": "Admin",
        "icon": "🎛️",
        "goal_template": "Add admin superportal: user management (list/search/ban/impersonate), tenant management for multi-tenant apps, MRR/churn/DAU metrics dashboard, audit log viewer, feature flag controls, system health monitoring.",
        "agents": ["Analytics Agent", "Data Visualization Agent", "RBAC Agent", "Audit Trail Agent", "Feature Flag Agent"],
        "requires_existing_code": True,
    },
    "add-analytics": {
        "name": "Add Analytics",
        "description": "Add usage analytics, funnel analysis, and retention charts",
        "category": "Admin",
        "icon": "📊",
        "goal_template": "Add analytics dashboard: event tracking, funnel analysis, cohort retention charts, revenue analytics, user journey visualization, custom report builder, CSV export.",
        "agents": ["Analytics Agent", "Analytics Events Schema Agent", "Data Visualization Agent", "Report Generation Agent"],
        "requires_existing_code": True,
    },

    # ── SECURITY ───────────────────────────────────────────────────────────────
    "security-audit": {
        "name": "Security Audit",
        "description": "Full security scan: OWASP, secrets, injection, XSS",
        "category": "Security",
        "icon": "🛡️",
        "goal_template": "Perform a complete security audit of this codebase: OWASP Top 10 check, secret scanning, SQL injection analysis, XSS vulnerability scan, authentication weaknesses, CORS misconfiguration, rate limiting gaps. Produce a security report with fixes.",
        "agents": ["AgentShield", "Security Checker", "Security Scanning Agent", "Penetration Test Agent", "Network Security Agent", "Secret Management Agent"],
        "requires_existing_code": True,
    },
    "add-rate-limiting": {
        "name": "Add Rate Limiting",
        "description": "Add IP and user-based rate limiting to all API endpoints",
        "category": "Security",
        "icon": "🚦",
        "goal_template": "Add rate limiting: per-IP limits, per-user limits, per-endpoint configuration, Redis-backed sliding window, rate limit headers, 429 responses with retry-after.",
        "agents": ["Rate Limiting Agent", "Rate Limit Agent", "Security Checker"],
        "requires_existing_code": True,
    },
    "add-compliance": {
        "name": "Add GDPR/HIPAA Compliance",
        "description": "Add data privacy, consent management, and compliance controls",
        "category": "Security",
        "icon": "📋",
        "goal_template": "Add compliance controls: GDPR data export and deletion, consent management, cookie consent banner, data retention policies, HIPAA audit logging if healthcare, privacy policy generator, DPA templates.",
        "agents": ["HIPAA Agent", "SOC2 Agent", "Legal Compliance Agent", "Privacy Policy Agent", "Cookie Consent Agent", "Audit & Compliance Engine Agent"],
        "requires_existing_code": True,
    },

    # ── TESTING ────────────────────────────────────────────────────────────────
    "add-tests": {
        "name": "Add Test Suite",
        "description": "Add unit tests, integration tests, and E2E tests",
        "category": "Testing",
        "icon": "🧪",
        "goal_template": "Add comprehensive test suite: unit tests for all utility functions, integration tests for all API endpoints, E2E tests for critical user journeys (signup, core feature, payment). Target 80%+ coverage.",
        "agents": ["Test Generation", "Unit Test Agent", "Integration Test Agent", "E2E Test Agent", "E2E Agent"],
        "requires_existing_code": True,
    },
    "fix-build": {
        "name": "Fix Build Errors",
        "description": "Automatically detect and fix all build/compile errors",
        "category": "Testing",
        "icon": "🔧",
        "goal_template": "Analyze all build errors, TypeScript errors, lint errors, and test failures in this codebase. Fix every error systematically. Verify the build passes completely.",
        "agents": ["Error Recovery", "Build Validator Agent", "Compilation Dry-Run Agent", "Import Path Validator Agent", "Dependency Conflict Resolver Agent"],
        "requires_existing_code": True,
    },
    "add-ci-cd": {
        "name": "Add CI/CD",
        "description": "Add GitHub Actions CI/CD pipeline with tests and deploy",
        "category": "Testing",
        "icon": "🔄",
        "goal_template": "Add GitHub Actions CI/CD: run tests on PR, type check, lint, build verification, auto-deploy to Railway on main branch merge, environment-specific configs.",
        "agents": ["GitHub Actions CI Agent", "Docker Setup Agent", "Deployment Agent", "Staging Agent"],
        "requires_existing_code": True,
    },

    # ── PERFORMANCE ────────────────────────────────────────────────────────────
    "optimize-performance": {
        "name": "Optimize Performance",
        "description": "Profile and fix all performance bottlenecks",
        "category": "Performance",
        "icon": "⚡",
        "goal_template": "Analyze and fix all performance issues: frontend bundle splitting, React render optimization, image optimization, database query optimization (N+1 fixes, missing indexes), caching strategy, CDN configuration. Target Lighthouse score 90+.",
        "agents": ["Performance Profiler", "Performance Analyzer", "Lighthouse Agent", "Lighthouse Performance Agent", "Bundle Analyzer Agent", "Caching Agent", "Database Optimization Agent", "CDN Agent"],
        "requires_existing_code": True,
    },
    "add-caching": {
        "name": "Add Caching",
        "description": "Add Redis caching for API responses and database queries",
        "category": "Performance",
        "icon": "🚀",
        "goal_template": "Add Redis caching: cache expensive database queries, API response caching with TTL, cache invalidation strategy, cache warming, cache hit rate monitoring.",
        "agents": ["Caching Agent", "Database Optimization Agent", "Monitoring Agent"],
        "requires_existing_code": True,
    },

    # ── UI & DESIGN ────────────────────────────────────────────────────────────
    "add-dark-mode": {
        "name": "Add Dark Mode",
        "description": "Add system-aware dark mode with smooth transitions",
        "category": "UI & Design",
        "icon": "🌙",
        "goal_template": "Add complete dark mode: CSS variables for all colors, system preference detection, manual toggle with localStorage persistence, smooth transition animations, all components support both modes.",
        "agents": ["Dark Mode Agent", "Dark Mode Theme Agent", "CSS Modern Standards Agent"],
        "requires_existing_code": True,
    },
    "add-i18n": {
        "name": "Add Internationalization",
        "description": "Add multi-language support with RTL and locale switching",
        "category": "UI & Design",
        "icon": "🌍",
        "goal_template": "Add full i18n: translation files for English + 3 other languages, locale switching, RTL layout support, date/number/currency formatting per locale, pluralization rules.",
        "agents": ["i18n Agent", "RTL Agent"],
        "requires_existing_code": True,
    },
    "add-accessibility": {
        "name": "Fix Accessibility",
        "description": "Make app WCAG 2.1 AA compliant",
        "category": "UI & Design",
        "icon": "♿",
        "goal_template": "Fix all accessibility issues: ARIA labels, keyboard navigation, focus management, color contrast ratios, screen reader announcements, skip links. Pass WCAG 2.1 AA audit.",
        "agents": ["Accessibility Agent", "Accessibility Audit Agent", "Accessibility WCAG Agent", "Keyboard Nav Agent", "Screen Reader Agent"],
        "requires_existing_code": True,
    },
    "add-email-templates": {
        "name": "Add Email Templates",
        "description": "Add transactional email templates with Resend/SendGrid",
        "category": "UI & Design",
        "icon": "📧",
        "goal_template": "Add transactional email system: welcome email, password reset, payment receipt, subscription renewal warning, account suspension notice. Use React Email for templates, integrate with Resend or SendGrid.",
        "agents": ["Email Agent", "Email Template Agent", "Notification Agent"],
        "requires_existing_code": True,
    },

    # ── INFRASTRUCTURE ─────────────────────────────────────────────────────────
    "add-monitoring": {
        "name": "Add Monitoring",
        "description": "Add error tracking, uptime monitoring, and alerting",
        "category": "Infrastructure",
        "icon": "📡",
        "goal_template": "Add full monitoring stack: error tracking (Sentry integration), uptime monitoring, performance metrics, custom dashboards, alerting on error spikes or downtime, structured logging.",
        "agents": ["Monitoring Agent", "Monitoring & Logging Agent", "Logging Agent", "Metrics Agent", "Incident Response Agent", "Synthetic Monitoring Agent"],
        "requires_existing_code": True,
    },
    "add-feature-flags": {
        "name": "Add Feature Flags",
        "description": "Add feature flagging for controlled rollouts and A/B tests",
        "category": "Infrastructure",
        "icon": "🚩",
        "goal_template": "Add feature flag system: flag creation and management UI, per-user and per-tenant targeting, percentage rollouts, A/B test integration, flag analytics.",
        "agents": ["Feature Flag Agent", "A/B Test Agent"],
        "requires_existing_code": True,
    },
    "add-notifications": {
        "name": "Add Push Notifications",
        "description": "Add web push, SMS, and in-app notifications",
        "category": "Infrastructure",
        "icon": "🔔",
        "goal_template": "Add notification system: in-app notification center, web push notifications, SMS via Twilio, notification preferences per user, notification rules engine (trigger conditions), read/unread state.",
        "agents": ["Notification Agent", "SMS & Push Agent", "Notification Rules Agent", "WebSocket Agent"],
        "requires_existing_code": True,
    },
    "dockerize": {
        "name": "Dockerize App",
        "description": "Add Docker, docker-compose, and container optimization",
        "category": "Infrastructure",
        "icon": "🐳",
        "goal_template": "Dockerize the application: multi-stage Dockerfile for frontend and backend, docker-compose for local dev, .dockerignore, container health checks, environment variable handling, volume mounts for data persistence.",
        "agents": ["Docker Setup Agent", "Environment Configuration Agent", "DevOps Agent"],
        "requires_existing_code": True,
    },
    "add-search": {
        "name": "Add Search",
        "description": "Add full-text search with filters and ranking",
        "category": "Infrastructure",
        "icon": "🔍",
        "goal_template": "Add full-text search: search index for main content, relevance ranking, filters, faceted search, search suggestions/autocomplete, search analytics.",
        "agents": ["Search Agent", "Search Engine Agent", "Search Relevance Agent"],
        "requires_existing_code": True,
    },

    # ── EXPORTS & INTEGRATIONS ─────────────────────────────────────────────────
    "add-exports": {
        "name": "Add Data Export",
        "description": "Add PDF, Excel, CSV, and Markdown export",
        "category": "Exports",
        "icon": "📥",
        "goal_template": "Add data export functionality: PDF export with custom templates, Excel/XLSX export with formatting, CSV export for all data tables, Markdown export for documents. All exports run server-side.",
        "agents": ["PDF Export", "Excel Export", "Markdown Export", "Report Generation Agent"],
        "requires_existing_code": True,
    },
    "add-webhooks": {
        "name": "Add Webhooks",
        "description": "Add outbound webhook system for integrations",
        "category": "Exports",
        "icon": "🔗",
        "goal_template": "Add webhook system: webhook endpoint management UI, event subscription, HMAC signature verification, retry logic with exponential backoff, webhook delivery logs, test webhook tool.",
        "agents": ["Webhook Agent", "Webhook Management Agent"],
        "requires_existing_code": True,
    },
    "add-api-docs": {
        "name": "Add API Documentation",
        "description": "Generate OpenAPI/Swagger docs for all endpoints",
        "category": "Exports",
        "icon": "📖",
        "goal_template": "Generate complete API documentation: OpenAPI 3.0 spec for all endpoints, Swagger UI, request/response examples, authentication documentation, SDKs for JavaScript and Python.",
        "agents": ["API Documentation Agent", "API Documentation Generation Agent", "API Contract Validator Agent"],
        "requires_existing_code": True,
    },

    # ── MULTI-TENANT ───────────────────────────────────────────────────────────
    "add-multitenancy": {
        "name": "Add Multi-tenancy",
        "description": "Add tenant isolation, custom domains, and per-tenant config",
        "category": "Multi-tenant",
        "icon": "🏗️",
        "goal_template": "Add multi-tenant architecture: row-level security per tenant, tenant provisioning on signup, custom subdomain routing with SSL, per-tenant configuration, data isolation verification, tenant admin portal.",
        "agents": ["Multi-tenant Agent", "Data Residency Agent", "SSO Agent", "Audit Trail Agent"],
        "requires_existing_code": True,
    },

    # ── MOBILE ─────────────────────────────────────────────────────────────────
    "make-mobile-ready": {
        "name": "Make Mobile Ready",
        "description": "Add responsive design, PWA, and mobile-optimized UX",
        "category": "Mobile",
        "icon": "📱",
        "goal_template": "Make app fully mobile-ready: responsive breakpoints for all screens, PWA manifest and service worker, mobile-optimized touch interactions, bottom navigation for mobile, app store submission prep.",
        "agents": ["Mobile Responsive Agent", "Store Prep Agent", "Native Config Agent", "Responsive Breakpoints Agent"],
        "requires_existing_code": True,
    },

    # ── FROM SCRATCH — Full apps ───────────────────────────────────────────────
    "saas-mvp": {
        "name": "Build SaaS MVP",
        "description": "Complete SaaS with auth, billing, dashboard, and deploy",
        "category": "Full Apps",
        "icon": "🚀",
        "goal_template": "Build a production-ready SaaS MVP with: user authentication (Google/GitHub OAuth + email), Stripe subscription billing (free/pro tiers), user dashboard, admin panel, PostgreSQL database, RESTful API, responsive React frontend, and Railway deployment config.",
        "agents": [],  # Use full DAG
        "requires_existing_code": False,
    },
    "landing-page": {
        "name": "Build Landing Page",
        "description": "Marketing landing page with hero, features, pricing, and CTA",
        "category": "Full Apps",
        "icon": "🎯",
        "goal_template": "Build a stunning marketing landing page: hero section with headline and CTA, features grid, social proof/testimonials, pricing table, FAQ, and footer. Fast, SEO-optimized, mobile-first design.",
        "agents": ["Frontend Generation", "SEO Agent", "Design Agent", "Performance Vibe Agent"],
        "requires_existing_code": False,
    },
    "api-backend": {
        "name": "Build REST API",
        "description": "Production REST API with auth, docs, and tests",
        "category": "Full Apps",
        "icon": "⚙️",
        "goal_template": "Build a production REST API: FastAPI or Express backend, JWT authentication, PostgreSQL with ORM, full CRUD endpoints, input validation, rate limiting, OpenAPI documentation, comprehensive test suite, Docker deployment.",
        "agents": ["Backend Generation", "Auth Setup Agent", "Database Agent", "API Documentation Agent", "Test Generation"],
        "requires_existing_code": False,
    },
}


# ── Workflow categories for UI grouping ────────────────────────────────────────
WORKFLOW_CATEGORIES = [
    "Auth & Identity",
    "Payments",
    "Database",
    "AI Features",
    "Admin",
    "Security",
    "Testing",
    "Performance",
    "UI & Design",
    "Infrastructure",
    "Exports",
    "Multi-tenant",
    "Mobile",
    "Full Apps",
]


def get_workflows_by_category() -> Dict[str, List[Dict]]:
    """Return workflows grouped by category for the UI sidebar."""
    result = {cat: [] for cat in WORKFLOW_CATEGORIES}
    for key, wf in WORKFLOWS.items():
        cat = wf.get("category", "Full Apps")
        if cat in result:
            result[cat].append({"key": key, **wf})
    return {k: v for k, v in result.items() if v}


def get_workflow(key: str) -> Optional[Dict]:
    """Get a workflow by key."""
    return WORKFLOWS.get(key)


def workflow_to_plan_goal(key: str, context: str = "") -> Optional[str]:
    """Convert a workflow key to a plan goal, optionally with context."""
    wf = WORKFLOWS.get(key)
    if not wf:
        return None
    goal = wf["goal_template"]
    if context:
        goal = f"{goal}\n\nEXISTING CONTEXT:\n{context}"
    return goal
