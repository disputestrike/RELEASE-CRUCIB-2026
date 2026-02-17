"""
Agent DAG: dependency graph and parallel execution phases.
Used by run_orchestration_v2 for output chaining and parallel runs.
Token optimization: set USE_TOKEN_OPTIMIZED_PROMPTS=1 for shorter prompts and smaller context.
"""
import os
from collections import deque
from typing import Dict, List, Any

# Agent names must match _ORCHESTRATION_AGENTS in server.py
# depends_on = list of agent names that must complete before this one
AGENT_DAG: Dict[str, Dict[str, Any]] = {
    "Planner": {"depends_on": [], "system_prompt": "You are a Planner. Decompose the request into 3-7 executable tasks. Numbered list only."},
    "Requirements Clarifier": {"depends_on": ["Planner"], "system_prompt": "You are a Requirements Clarifier. Ask 2-4 clarifying questions. One per line."},
    "Stack Selector": {"depends_on": ["Requirements Clarifier"], "system_prompt": "You are a Stack Selector. Recommend tech stack (frontend, backend, DB). Short bullets."},
    "Frontend Generation": {"depends_on": ["Stack Selector"], "system_prompt": "You are Frontend Generation. Output only complete React/JSX code. No markdown."},
    "Backend Generation": {"depends_on": ["Stack Selector"], "system_prompt": "You are Backend Generation. Output only backend code (e.g. FastAPI/Express). No markdown."},
    "Database Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Database Agent. Output schema and migration steps. Plain text or SQL."},
    "API Integration": {"depends_on": ["Stack Selector"], "system_prompt": "You are API Integration. Output only code that calls an API. No markdown."},
    "Test Generation": {"depends_on": ["Backend Generation"], "system_prompt": "You are Test Generation. Output only test code. No markdown."},
    "Image Generation": {"depends_on": ["Design Agent"], "system_prompt": "You are Image Generation. Use the Design Agent's placement spec. Output ONLY a JSON object with exactly these keys: hero, feature_1, feature_2. Each value is a detailed image generation prompt (style, composition, colors) for that section. No markdown, no explanation, only valid JSON."},
    "Video Generation": {"depends_on": ["Image Generation"], "system_prompt": "You are Video Generation. Based on the app request, output ONLY a JSON object with keys: hero, feature. Each value is a short search query (2-5 words) for finding a stock video for that section. No markdown, no explanation, only valid JSON."},
    "Security Checker": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a Security Checker. List 3-5 security checklist items with PASS/FAIL."},
    "Test Executor": {"depends_on": ["Test Generation"], "system_prompt": "You are a Test Executor. Give the test command and one line of what to check."},
    "UX Auditor": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a UX Auditor. List 2-4 accessibility/UX checklist items with PASS/FAIL."},
    "Performance Analyzer": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a Performance Analyzer. List 2-4 performance tips for the project."},
    "Deployment Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Deployment Agent. Give step-by-step deploy instructions."},
    "Error Recovery": {"depends_on": ["Backend Generation"], "system_prompt": "You are Error Recovery. List 2-3 common failure points and how to recover."},
    "Memory Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Memory Agent. Summarize the project in 2-3 lines for reuse."},
    "PDF Export": {"depends_on": ["Deployment Agent"], "system_prompt": "You are PDF Export. Describe what a one-page project summary PDF would include."},
    "Excel Export": {"depends_on": ["Deployment Agent"], "system_prompt": "You are Excel Export. Suggest 3-5 columns for a project tracking spreadsheet."},
    "Markdown Export": {"depends_on": ["Deployment Agent"], "system_prompt": "You are Markdown Export. Output a short project summary in Markdown (headings, bullets)."},
    "Scraping Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Scraping Agent. Suggest 2-3 data sources or URLs to scrape for this project."},
    "Automation Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are an Automation Agent. Suggest 2-3 automated tasks or cron jobs for this project."},
    # Design & layout
    "Design Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Design Agent. Output ONLY a JSON object with keys: hero, feature_1, feature_2. Each value: { \"position\": \"top-full|sidebar|grid\", \"aspect\": \"16:9|1:1|4:3\", \"role\": \"hero|feature|testimonial\" }. No markdown."},
    "Layout Agent": {"depends_on": ["Frontend Generation", "Image Generation", "Design Agent"], "system_prompt": "You are a Layout Agent. Given frontend code and image specs, output updated React/JSX with image placeholders (img tags with data-image-slot) in correct positions. No markdown."},
    "SEO Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are an SEO Agent. Output meta tags, Open Graph, Twitter Card, JSON-LD schema, sitemap hints, robots.txt rules. Plain text or JSON."},
    "Content Agent": {"depends_on": ["Planner"], "system_prompt": "You are a Content Agent. Write landing page copy: hero headline, 3 feature blurbs (2 lines each), CTA text. Plain text, one section per line."},
    "Brand Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Brand Agent. Output a JSON with: primary_color, secondary_color, font_heading, font_body, tone (e.g. professional, playful). No markdown."},
    # Setup & integration
    "Documentation Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Documentation Agent. Output README sections: setup, env vars, run commands, deploy steps. Markdown."},
    "Validation Agent": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a Validation Agent. List 3-5 form/API validation rules and suggest Zod/Yup schemas. Plain text."},
    "Auth Setup Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are an Auth Setup Agent. Suggest JWT/OAuth2 flow: login, logout, token refresh, protected routes. Code or step list."},
    "Payment Setup Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Payment Setup Agent. Suggest Stripe (or similar) integration: checkout, webhooks, subscription. Code or step list."},
    "Monitoring Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Monitoring Agent. Suggest Sentry/analytics setup: error tracking, performance, user events. Plain text."},
    "Accessibility Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an Accessibility Agent. List 3-5 a11y improvements: ARIA, focus, contrast, screen reader. Plain text."},
    "DevOps Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a DevOps Agent. Suggest CI/CD (GitHub Actions), Dockerfile, env config. Plain text or YAML."},
    "Webhook Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Webhook Agent. Suggest webhook endpoint design: payload, signature verification, retries. Plain text."},
    "Email Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are an Email Agent. Suggest transactional email setup: provider (Resend/SendGrid), templates, verification. Plain text."},
    "Legal Compliance Agent": {"depends_on": ["Planner"], "system_prompt": "You are a Legal Compliance Agent. Suggest GDPR/CCPA items: cookie banner, privacy link, data retention. Plain text."},
    # Phase 2: 50 agents (14 new)
    "GraphQL Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a GraphQL Agent. Output GraphQL schema and resolvers for the app. Plain text or code."},
    "WebSocket Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a WebSocket Agent. Suggest real-time subscription design and sample code. Plain text or code."},
    "i18n Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an i18n Agent. Suggest locales, translation keys, and react-i18next (or similar) setup. Plain text."},
    "Caching Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Caching Agent. Suggest Redis or edge caching strategy for the app. Plain text."},
    "Rate Limit Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Rate Limit Agent. Suggest API rate limiting, quotas, and throttling. Plain text or code."},
    "Search Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Search Agent. Suggest full-text search (Algolia/Meilisearch/Elastic) integration. Plain text."},
    "Analytics Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are an Analytics Agent. Suggest GA4, Mixpanel, or event schema for the app. Plain text."},
    "API Documentation Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are an API Documentation Agent. Output OpenAPI/Swagger spec or doc from routes. Plain text or YAML."},
    "Mobile Responsive Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Mobile Responsive Agent. Suggest breakpoints, touch targets, PWA hints. Plain text."},
    "Migration Agent": {"depends_on": ["Database Agent"], "system_prompt": "You are a Migration Agent. Output DB migration scripts (e.g. Alembic, knex). Plain text or code."},
    "Backup Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Backup Agent. Suggest backup strategy and restore steps. Plain text."},
    "Notification Agent": {"depends_on": ["Email Agent"], "system_prompt": "You are a Notification Agent. Suggest push, in-app, and email notification flow. Plain text."},
    "Design Iteration Agent": {"depends_on": ["Planner", "Design Agent"], "system_prompt": "You are a Design Iteration Agent. Suggest feedback → spec → rebuild flow. Plain text."},
    "Code Review Agent": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a Code Review Agent. List 3-5 security, style, and best-practice review items. Plain text."},
    # Phase 3: 75 agents (+25)
    "Staging Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Staging Agent. Suggest staging env and preview URLs. Plain text."},
    "A/B Test Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an A/B Test Agent. Suggest experiment setup and variant routing. Plain text."},
    "Feature Flag Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Feature Flag Agent. Suggest LaunchDarkly/Flagsmith wiring. Plain text."},
    "Error Boundary Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an Error Boundary Agent. Suggest React error boundaries and fallback UI. Code or plain text."},
    "Logging Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Logging Agent. Suggest structured logs and log levels. Plain text."},
    "Metrics Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Metrics Agent. Suggest Prometheus/Datadog metrics. Plain text."},
    "Audit Trail Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are an Audit Trail Agent. Suggest user action logging and audit log. Plain text."},
    "Session Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Session Agent. Suggest session storage, expiry, refresh. Plain text or code."},
    "OAuth Provider Agent": {"depends_on": ["Auth Setup Agent"], "system_prompt": "You are an OAuth Provider Agent. Suggest Google/GitHub OAuth wiring. Plain text or code."},
    "2FA Agent": {"depends_on": ["Auth Setup Agent"], "system_prompt": "You are a 2FA Agent. Suggest TOTP and backup codes. Plain text."},
    "Stripe Subscription Agent": {"depends_on": ["Payment Setup Agent"], "system_prompt": "You are a Stripe Subscription Agent. Suggest plans, metering, downgrade. Plain text."},
    "Invoice Agent": {"depends_on": ["Payment Setup Agent"], "system_prompt": "You are an Invoice Agent. Suggest invoice generation and PDF. Plain text."},
    "CDN Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a CDN Agent. Suggest static assets and cache headers. Plain text."},
    "SSR Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an SSR Agent. Suggest Next.js SSR/SSG hints. Plain text."},
    "Bundle Analyzer Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Bundle Analyzer Agent. Suggest code splitting and chunk hints. Plain text."},
    "Lighthouse Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Lighthouse Agent. Suggest performance, a11y, SEO audit. Plain text."},
    "Schema Validation Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Schema Validation Agent. Suggest request/response validation. Plain text."},
    "Mock API Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Mock API Agent. Suggest MSW, Mirage, or mock server. Plain text."},
    "E2E Agent": {"depends_on": ["Test Generation"], "system_prompt": "You are an E2E Agent. Suggest Playwright/Cypress scaffolding. Plain text or code."},
    "Load Test Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Load Test Agent. Suggest k6 or Artillery scripts. Plain text."},
    "Dependency Audit Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Dependency Audit Agent. Suggest npm audit, Snyk. Plain text."},
    "License Agent": {"depends_on": ["Planner"], "system_prompt": "You are a License Agent. Suggest OSS license compliance. Plain text."},
    "Terms Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a Terms Agent. Draft terms of service outline. Plain text."},
    "Privacy Policy Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a Privacy Policy Agent. Draft privacy policy outline. Plain text."},
    "Cookie Consent Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a Cookie Consent Agent. Suggest cookie banner and preferences. Plain text."},
    # Phase 4: 100 agents (+25)
    "Multi-tenant Agent": {"depends_on": ["Database Agent"], "system_prompt": "You are a Multi-tenant Agent. Suggest tenant isolation and schema. Plain text."},
    "RBAC Agent": {"depends_on": ["Auth Setup Agent"], "system_prompt": "You are an RBAC Agent. Suggest roles and permissions matrix. Plain text."},
    "SSO Agent": {"depends_on": ["Auth Setup Agent"], "system_prompt": "You are an SSO Agent. Suggest SAML, enterprise SSO. Plain text."},
    "Audit Export Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are an Audit Export Agent. Suggest export of audit logs. Plain text."},
    "Data Residency Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a Data Residency Agent. Suggest region and GDPR data location. Plain text."},
    "HIPAA Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a HIPAA Agent. Suggest healthcare compliance hints. Plain text."},
    "SOC2 Agent": {"depends_on": ["Legal Compliance Agent"], "system_prompt": "You are a SOC2 Agent. Suggest SOC2 control hints. Plain text."},
    "Penetration Test Agent": {"depends_on": ["Security Checker"], "system_prompt": "You are a Penetration Test Agent. Suggest pentest checklist. Plain text."},
    "Incident Response Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are an Incident Response Agent. Suggest runbook and escalation. Plain text."},
    "SLA Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are an SLA Agent. Suggest uptime and latency targets. Plain text."},
    "Cost Optimizer Agent": {"depends_on": ["Deployment Agent"], "system_prompt": "You are a Cost Optimizer Agent. Suggest cloud cost hints. Plain text."},
    "Accessibility WCAG Agent": {"depends_on": ["Accessibility Agent"], "system_prompt": "You are an Accessibility WCAG Agent. WCAG 2.1 AA checklist. Plain text."},
    "RTL Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an RTL Agent. Suggest right-to-left layout. Plain text."},
    "Dark Mode Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Dark Mode Agent. Suggest theme toggle and contrast. Code or plain text."},
    "Keyboard Nav Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Keyboard Nav Agent. Suggest full keyboard navigation. Plain text."},
    "Screen Reader Agent": {"depends_on": ["Accessibility Agent"], "system_prompt": "You are a Screen Reader Agent. Suggest screen-reader-specific hints. Plain text."},
    "Component Library Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Component Library Agent. Suggest Shadcn/Radix usage. Plain text."},
    "Design System Agent": {"depends_on": ["Brand Agent"], "system_prompt": "You are a Design System Agent. Suggest tokens, spacing, typography. Plain text."},
    "Animation Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are an Animation Agent. Suggest Framer Motion or transitions. Plain text."},
    "Chart Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Chart Agent. Suggest Recharts or D3 usage. Plain text."},
    "Table Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Table Agent. Suggest data tables, sorting, pagination. Plain text."},
    "Form Builder Agent": {"depends_on": ["Frontend Generation"], "system_prompt": "You are a Form Builder Agent. Suggest dynamic form generation. Plain text."},
    "Workflow Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Workflow Agent. Suggest state machine or workflows. Plain text."},
    "Queue Agent": {"depends_on": ["Backend Generation"], "system_prompt": "You are a Queue Agent. Suggest job queues (Bull/Celery). Plain text."},
    # Phase 5: Vibe & Accessibility Agents (110-115 agents) - NEW
    "Vibe Analyzer Agent": {"depends_on": ["Design Agent", "Brand Agent"], "system_prompt": "You are a Vibe Analyzer. Analyze the overall 'vibe' of the project: mood, aesthetic, energy level. Output: vibe_name, emotional_tone, visual_energy, code_style. JSON format."},
    "Voice Context Agent": {"depends_on": ["Planner", "Requirements Clarifier"], "system_prompt": "You are a Voice Context Agent. Convert voice/speech input to code context. Extract intent, emotion, urgency, and technical requirements from natural language. Output structured requirements."},
    "Video Tutorial Agent": {"depends_on": ["Documentation Agent", "Frontend Generation"], "system_prompt": "You are a Video Tutorial Agent. Generate video tutorial scripts and storyboards. Output: scene descriptions, narration, code highlights, timing. Markdown format."},
    "Aesthetic Reasoner Agent": {"depends_on": ["Design Agent", "Frontend Generation"], "system_prompt": "You are an Aesthetic Reasoner. Evaluate code and design for beauty, elegance, and visual harmony. Suggest improvements for aesthetic quality. Output: beauty_score (1-10), improvements, reasoning."},
    "Collaborative Memory Agent": {"depends_on": ["Memory Agent", "Team Preferences"], "system_prompt": "You are a Collaborative Memory Agent. Remember team preferences, past decisions, and project patterns. Output: team_style, preferred_patterns, past_decisions, recommendations."},
    "Real-time Feedback Agent": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a Real-time Feedback Agent. Adapt to user reactions and feedback instantly. Suggest quick improvements based on user sentiment. Output: feedback_analysis, quick_fixes, priority_improvements."},
    "Mood Detection Agent": {"depends_on": ["Planner"], "system_prompt": "You are a Mood Detection Agent. Detect user mood and intent from interactions. Output: user_mood, confidence_level, recommended_approach, tone_adjustment."},
    "Accessibility Vibe Agent": {"depends_on": ["Accessibility Agent", "Vibe Analyzer Agent"], "system_prompt": "You are an Accessibility Vibe Agent. Ensure design and code 'feel' accessible and inclusive. Check WCAG compliance while maintaining aesthetic vibe. Output: accessibility_score, vibe_preservation, recommendations."},
    "Performance Vibe Agent": {"depends_on": ["Performance Analyzer", "Frontend Generation"], "system_prompt": "You are a Performance Vibe Agent. Optimize code to 'feel' fast and responsive. Suggest micro-interactions and loading states. Output: performance_feel_score, micro_interactions, loading_strategies."},
    "Creativity Catalyst Agent": {"depends_on": ["Design Agent", "Content Agent"], "system_prompt": "You are a Creativity Catalyst Agent. Suggest creative improvements and innovative features. Output: creative_ideas (top 5), implementation_difficulty, innovation_score, wow_factor."},
    "IDE Integration Coordinator Agent": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are an IDE Integration Coordinator. Prepare code for IDE extensions. Output: IDE-compatible code, extension hooks, plugin metadata, quick-action suggestions."},
    "Multi-language Code Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Multi-language Code Agent. Generate code in multiple languages (Python, JavaScript, Go, Rust, etc.). Maintain consistency across languages. Output: language_variants, compatibility_notes."},
    "Team Collaboration Agent": {"depends_on": ["Collaborative Memory Agent"], "system_prompt": "You are a Team Collaboration Agent. Suggest collaboration workflows, code review processes, and team communication patterns. Output: workflow_suggestions, review_checklist, communication_guidelines."},
    "User Onboarding Agent": {"depends_on": ["Documentation Agent", "Video Tutorial Agent"], "system_prompt": "You are a User Onboarding Agent. Create comprehensive onboarding experience. Output: quickstart_guide, tutorial_sequence, learning_path, support_resources."},
    "Customization Engine Agent": {"depends_on": ["Brand Agent", "Vibe Analyzer Agent"], "system_prompt": "You are a Customization Engine Agent. Enable users to customize code/design to their preferences. Output: customization_options, theme_variables, plugin_architecture, extension_points."},
    # Phase 3: Tool Integration Agents (REAL execution: wired in real_agent_runner.py)
    "Browser Tool Agent": {"depends_on": ["Stack Selector"], "system_prompt": "You are a Browser Tool Agent. Automate browser actions using Playwright: navigate, screenshot, scrape, fill forms, click elements. Output: action plan or results."},
    "File Tool Agent": {"depends_on": ["Frontend Generation", "Backend Generation"], "system_prompt": "You are a File Tool Agent. Writes generated frontend/backend/schema/tests to project workspace. (Real agent executes this.)"},
    "API Tool Agent": {"depends_on": ["API Integration"], "system_prompt": "You are an API Tool Agent. Make HTTP requests (GET, POST, PUT, DELETE). Handle authentication and parse responses. Output: API response data."},
    "Database Tool Agent": {"depends_on": ["Database Agent"], "system_prompt": "You are a Database Tool Agent. Applies schema to project SQLite. (Real agent executes this.)"},
    "Deployment Tool Agent": {"depends_on": ["Deployment Agent", "File Tool Agent"], "system_prompt": "You are a Deployment Tool Agent. Deploys from project workspace to Vercel/Railway/Netlify. (Real agent executes this.)"},
}


# Max chars of previous output to inject (avoid token overflow)
CONTEXT_MAX_CHARS = 2000
CONTEXT_MAX_CHARS_OPTIMIZED = 1200

# Shorter system prompts when USE_TOKEN_OPTIMIZED_PROMPTS=1 (~10–12K vs ~20K tokens per build)
OPTIMIZED_SYSTEM_PROMPTS: Dict[str, str] = {
    "Planner": "Planner. 3–7 tasks. Numbered list only.",
    "Requirements Clarifier": "Requirements. 2–4 clarifying questions. One per line.",
    "Stack Selector": "Stack. Recommend frontend, backend, DB. Short bullets.",
    "Frontend Generation": "Frontend. React/JSX code only. No markdown.",
    "Backend Generation": "Backend. FastAPI/Express code only. No markdown.",
    "Database Agent": "Database. Schema and migrations. Plain text or SQL.",
    "API Integration": "API. Code that calls an API. No markdown.",
    "Test Generation": "Tests. Test code only. No markdown.",
    "Image Generation": "Image. Output JSON only: { \"hero\": \"prompt\", \"feature_1\": \"prompt\", \"feature_2\": \"prompt\" }.",
    "Video Generation": "Video. Output JSON only: { \"hero\": \"search query\", \"feature\": \"search query\" }.",
    "Security Checker": "Security. 3–5 items PASS/FAIL.",
    "Test Executor": "Test run. Command + one line to check.",
    "UX Auditor": "UX. 2–4 accessibility items PASS/FAIL.",
    "Performance Analyzer": "Performance. 2–4 tips.",
    "Deployment Agent": "Deploy. Step-by-step instructions.",
    "Error Recovery": "Errors. 2–3 failure points + recovery.",
    "Memory Agent": "Memory. 2–3 line project summary.",
    "PDF Export": "PDF. One-page summary description.",
    "Excel Export": "Excel. 3–5 columns for tracking.",
    "Markdown Export": "Markdown. Short project summary (headings, bullets).",
    "Scraping Agent": "Scraping. 2–3 data sources or URLs.",
    "Automation Agent": "Automation. 2–3 cron/automated tasks.",
    "Design Agent": "Design. JSON: hero, feature_1, feature_2 with position, aspect, role.",
    "Layout Agent": "Layout. Inject image placeholders into frontend. React/JSX.",
    "SEO Agent": "SEO. Meta, OG, schema, sitemap, robots.txt.",
    "Content Agent": "Content. Hero, 3 feature blurbs, CTA.",
    "Brand Agent": "Brand. JSON: colors, fonts, tone.",
    "Documentation Agent": "Documentation. README: setup, env, run, deploy.",
    "Validation Agent": "Validation. 3–5 rules + Zod/Yup.",
    "Auth Setup Agent": "Auth. JWT/OAuth flow, protected routes.",
    "Payment Setup Agent": "Payment. Stripe checkout, webhooks.",
    "Monitoring Agent": "Monitoring. Sentry, analytics setup.",
    "Accessibility Agent": "Accessibility. 3–5 a11y improvements.",
    "DevOps Agent": "DevOps. CI/CD, Dockerfile.",
    "Webhook Agent": "Webhook. Endpoint design, signature verification.",
    "Email Agent": "Email. Transactional email setup.",
    "Legal Compliance Agent": "Legal. GDPR/CCPA hints.",
    "GraphQL Agent": "GraphQL. Schema + resolvers.",
    "WebSocket Agent": "WebSocket. Real-time subscriptions.",
    "i18n Agent": "i18n. Locales, translation keys.",
    "Caching Agent": "Caching. Redis/edge strategy.",
    "Rate Limit Agent": "Rate limit. API quotas.",
    "Search Agent": "Search. Algolia/Meilisearch.",
    "Analytics Agent": "Analytics. GA4, events.",
    "API Documentation Agent": "API docs. OpenAPI/Swagger.",
    "Mobile Responsive Agent": "Mobile. Breakpoints, PWA.",
    "Migration Agent": "Migrations. DB scripts.",
    "Backup Agent": "Backup. Strategy, restore.",
    "Notification Agent": "Notifications. Push, in-app.",
    "Design Iteration Agent": "Design iteration. Feedback flow.",
    "Code Review Agent": "Code review. Security, style.",
    "Staging Agent": "Staging. Preview URLs.",
    "A/B Test Agent": "A/B tests. Variant routing.",
    "Feature Flag Agent": "Feature flags. LaunchDarkly.",
    "Error Boundary Agent": "Error boundaries. Fallback UI.",
    "Logging Agent": "Logging. Structured logs.",
    "Metrics Agent": "Metrics. Prometheus/Datadog.",
    "Audit Trail Agent": "Audit trail. User actions.",
    "Session Agent": "Session. Storage, expiry.",
    "OAuth Provider Agent": "OAuth. Google/GitHub.",
    "2FA Agent": "2FA. TOTP, backup codes.",
    "Stripe Subscription Agent": "Stripe. Plans, metering.",
    "Invoice Agent": "Invoice. PDF generation.",
    "CDN Agent": "CDN. Static, cache headers.",
    "SSR Agent": "SSR. Next.js hints.",
    "Bundle Analyzer Agent": "Bundle. Code splitting.",
    "Lighthouse Agent": "Lighthouse. Perf, a11y.",
    "Schema Validation Agent": "Schema. Request/response.",
    "Mock API Agent": "Mock API. MSW, Mirage.",
    "E2E Agent": "E2E. Playwright/Cypress.",
    "Load Test Agent": "Load test. k6, Artillery.",
    "Dependency Audit Agent": "Deps. npm audit, Snyk.",
    "License Agent": "License. OSS compliance.",
    "Terms Agent": "Terms. ToS draft.",
    "Privacy Policy Agent": "Privacy. Policy draft.",
    "Cookie Consent Agent": "Cookie. Banner, prefs.",
    "Multi-tenant Agent": "Multi-tenant. Isolation.",
    "RBAC Agent": "RBAC. Roles, permissions.",
    "SSO Agent": "SSO. SAML, enterprise.",
    "Audit Export Agent": "Audit export. Logs.",
    "Data Residency Agent": "Data residency. Region.",
    "HIPAA Agent": "HIPAA. Healthcare.",
    "SOC2 Agent": "SOC2. Controls.",
    "Penetration Test Agent": "Pentest. Checklist.",
    "Incident Response Agent": "Incident. Runbook.",
    "SLA Agent": "SLA. Uptime, latency.",
    "Cost Optimizer Agent": "Cost. Cloud hints.",
    "Accessibility WCAG Agent": "WCAG 2.1 AA.",
    "RTL Agent": "RTL. Right-to-left.",
    "Dark Mode Agent": "Dark mode. Theme toggle.",
    "Keyboard Nav Agent": "Keyboard. Full nav.",
    "Screen Reader Agent": "Screen reader. Hints.",
    "Component Library Agent": "Components. Shadcn/Radix.",
    "Design System Agent": "Design system. Tokens.",
    "Animation Agent": "Animation. Framer Motion.",
    "Chart Agent": "Charts. Recharts, D3.",
    "Table Agent": "Tables. Sort, pagination.",
    "Form Builder Agent": "Forms. Dynamic.",
    "Workflow Agent": "Workflow. State machine.",
    "Queue Agent": "Queue. Bull/Celery.",
    "Vibe Analyzer Agent": "Vibe. Mood, aesthetic, energy. JSON: vibe_name, emotional_tone, visual_energy, code_style.",
    "Voice Context Agent": "Voice. Convert speech to code context. Extract intent, emotion, urgency, requirements.",
    "Video Tutorial Agent": "Video tutorials. Scripts, storyboards, narration, code highlights, timing.",
    "Aesthetic Reasoner Agent": "Aesthetics. Beauty, elegance, harmony. Score 1-10, improvements, reasoning.",
    "Collaborative Memory Agent": "Team memory. Preferences, patterns, decisions, recommendations.",
    "Real-time Feedback Agent": "Real-time feedback. Adapt to user reactions. Quick fixes, priority improvements.",
    "Mood Detection Agent": "Mood. User mood, confidence, approach, tone adjustment.",
    "Accessibility Vibe Agent": "Accessible vibe. WCAG + aesthetic. Score, vibe preservation, recommendations.",
    "Performance Vibe Agent": "Performance feel. Fast, responsive. Micro-interactions, loading states.",
    "Creativity Catalyst Agent": "Creativity. Top 5 ideas, difficulty, innovation score, wow factor.",
    "IDE Integration Coordinator Agent": "IDE coordinator. IDE-compatible code, hooks, metadata, quick actions.",
    "Multi-language Code Agent": "Multi-language. Python, JS, Go, Rust. Variants, compatibility.",
    "Team Collaboration Agent": "Team collab. Workflows, code review, communication patterns.",
    "User Onboarding Agent": "Onboarding. Quickstart, tutorials, learning path, support.",
    "Customization Engine Agent": "Customization. Options, themes, plugins, extensions.",
}



def _use_token_optimized() -> bool:
    return os.environ.get("USE_TOKEN_OPTIMIZED_PROMPTS", "").strip().lower() in ("1", "true", "yes")


def get_context_max_chars() -> int:
    """Max chars per previous output; smaller when token-optimized."""
    return CONTEXT_MAX_CHARS_OPTIMIZED if _use_token_optimized() else CONTEXT_MAX_CHARS


def get_system_prompt_for_agent(agent_name: str) -> str:
    """System prompt for agent; uses short version when USE_TOKEN_OPTIMIZED_PROMPTS=1."""
    if agent_name not in AGENT_DAG:
        return ""
    if _use_token_optimized() and agent_name in OPTIMIZED_SYSTEM_PROMPTS:
        return OPTIMIZED_SYSTEM_PROMPTS[agent_name]
    return AGENT_DAG[agent_name].get("system_prompt", "")


def topological_sort(dag: Dict[str, Dict[str, Any]]) -> List[str]:
    """Kahn's algorithm: return execution order respecting dependencies. Raises if cycle."""
    # Only count deps that exist in dag (missing refs like "Team Preferences" would otherwise block)
    in_degree = {
        n: len([d for d in cfg.get("depends_on", []) if d in dag])
        for n, cfg in dag.items()
    }
    q = deque([n for n, d in in_degree.items() if d == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for node, cfg in dag.items():
            if u in cfg.get("depends_on", []):
                in_degree[node] -= 1
                if in_degree[node] == 0:
                    q.append(node)
    if len(order) != len(dag):
        raise ValueError("Cycle in agent DAG")
    return order


def get_execution_phases(dag: Dict[str, Dict[str, Any]]) -> List[List[str]]:
    """Group agents into phases: each phase can run in parallel (no dep within phase)."""
    order = topological_sort(dag)
    dag_nodes = set(dag.keys())
    phases: List[List[str]] = []
    completed = set()
    while len(completed) < len(order):
        ready = []
        for node in order:
            if node in completed:
                continue
            deps = set(dag[node].get("depends_on", []))
            # Only require deps that exist in the DAG to be completed
            if (deps & dag_nodes) <= completed:
                ready.append(node)
        if not ready:
            raise ValueError("DAG cycle or missing nodes")
        phases.append(ready)
        completed.update(ready)
    return phases


def build_context_from_previous_agents(
    current_agent: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    project_prompt: str,
) -> str:
    """Build enhanced prompt with previous agents' outputs. Truncates to get_context_max_chars() per output."""
    max_chars = get_context_max_chars()
    parts = [project_prompt]
    for agent_name, data in previous_outputs.items():
        out = data.get("output") or data.get("result") or data.get("code") or ""
        if isinstance(out, str) and out.strip():
            snippet = out.strip()[:max_chars]
            if len(out.strip()) > max_chars:
                snippet += "\n... (truncated)"
            parts.append(f"--- Output from {agent_name} ---\n{snippet}")
    return "\n\n".join(parts)
