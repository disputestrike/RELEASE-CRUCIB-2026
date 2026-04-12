import io
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_dag import AGENT_DAG, get_system_prompt_for_agent
from agent_real_behavior import run_agent_real_behavior
from automation.constants import (
    CREDITS_PER_AGENT_RUN,
    INTERNAL_USER_ID,
    MAX_CONCURRENT_RUNS_PER_USER,
    MAX_RUNS_PER_HOUR_PER_USER,
    WEBHOOK_IDEMPOTENCY_SECONDS,
    WEBHOOK_RATE_LIMIT_PER_MINUTE,
)
from automation.executor import run_actions
from automation.models import ActionConfig, AgentCreate, AgentUpdate, TriggerConfig
from automation.schedule import is_one_time, next_run_at
from deps import get_current_user, get_db, get_optional_user
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pricing_plans import CREDITS_PER_TOKEN
from pydantic import BaseModel
from services.llm_service import (
    _call_llm_with_fallback,
    _effective_api_keys,
    _get_model_chain,
    get_authenticated_or_api_user,
    get_workspace_api_keys,
)

logger = logging.getLogger(__name__)

agents_router = APIRouter(prefix="/api", tags=["agents"])

MIN_CREDITS_FOR_LLM = 5


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AgentPromptBody(BaseModel):
    """Generic body for agent runs that take a prompt."""

    prompt: str
    context: Optional[str] = None
    language: Optional[str] = "javascript"


class AgentCodeBody(BaseModel):
    code: str
    language: Optional[str] = "javascript"


class AgentScrapeBody(BaseModel):
    url: str


class AgentExportPdfBody(BaseModel):
    title: str
    content: str


class AgentExportMarkdownBody(BaseModel):
    title: str
    content: str


class AgentExportExcelBody(BaseModel):
    title: str
    rows: List[Dict[str, Any]] = []


class AgentMemoryBody(BaseModel):
    name: str
    content: str


class AgentGenericRunBody(BaseModel):
    agent_name: str
    prompt: str


class AgentAutomationBody(BaseModel):
    name: str
    prompt: str
    run_at: Optional[str] = None


class RunInternalBody(BaseModel):
    """Body for run-internal (worker calling back to run an agent)."""

    agent_name: str
    prompt: str
    user_id: str


class FromTemplateBody(BaseModel):
    template_slug: str
    overrides: Optional[Dict[str, Any]] = None


class FromDescriptionBody(BaseModel):
    """Prompt-to-automation: natural language description of the automation."""

    description: str


AGENT_DEFINITIONS = [
    {
        "name": "Planner",
        "layer": "planning",
        "description": "Decomposes user requests into executable tasks",
        "avg_tokens": 50000,
    },
    {
        "name": "Requirements Clarifier",
        "layer": "planning",
        "description": "Asks clarifying questions and validates requirements",
        "avg_tokens": 30000,
    },
    {
        "name": "Stack Selector",
        "layer": "planning",
        "description": "Chooses optimal technology stack",
        "avg_tokens": 20000,
    },
    {
        "name": "Frontend Generation",
        "layer": "execution",
        "description": "Generates React/Next.js UI components",
        "avg_tokens": 150000,
    },
    {
        "name": "Backend Generation",
        "layer": "execution",
        "description": "Creates APIs, auth, business logic",
        "avg_tokens": 120000,
    },
    {
        "name": "Database Agent",
        "layer": "execution",
        "description": "Designs schema and migrations",
        "avg_tokens": 80000,
    },
    {
        "name": "API Integration",
        "layer": "execution",
        "description": "Integrates third-party APIs",
        "avg_tokens": 60000,
    },
    {
        "name": "Test Generation",
        "layer": "execution",
        "description": "Writes comprehensive test suites",
        "avg_tokens": 100000,
    },
    {
        "name": "Image Generation",
        "layer": "execution",
        "description": "Creates AI-generated visuals",
        "avg_tokens": 40000,
    },
    {
        "name": "Security Checker",
        "layer": "validation",
        "description": "Audits for vulnerabilities",
        "avg_tokens": 40000,
    },
    {
        "name": "Test Executor",
        "layer": "validation",
        "description": "Runs all tests and reports",
        "avg_tokens": 50000,
    },
    {
        "name": "UX Auditor",
        "layer": "validation",
        "description": "Reviews design and accessibility",
        "avg_tokens": 35000,
    },
    {
        "name": "Performance Analyzer",
        "layer": "validation",
        "description": "Optimizes speed and efficiency",
        "avg_tokens": 40000,
    },
    {
        "name": "Deployment Agent",
        "layer": "deployment",
        "description": "Deploys to cloud platforms",
        "avg_tokens": 60000,
    },
    {
        "name": "Error Recovery",
        "layer": "deployment",
        "description": "Auto-fixes failures",
        "avg_tokens": 45000,
    },
    {
        "name": "Memory Agent",
        "layer": "deployment",
        "description": "Stores patterns for reuse",
        "avg_tokens": 25000,
    },
    {
        "name": "PDF Export",
        "layer": "export",
        "description": "Generates formatted PDF reports",
        "avg_tokens": 30000,
    },
    {
        "name": "Excel Export",
        "layer": "export",
        "description": "Creates spreadsheets with formulas",
        "avg_tokens": 25000,
    },
    {
        "name": "Markdown Export",
        "layer": "export",
        "description": "Outputs project summary in Markdown",
        "avg_tokens": 20000,
    },
    {
        "name": "Scraping Agent",
        "layer": "automation",
        "description": "Extracts data from websites",
        "avg_tokens": 35000,
    },
    {
        "name": "Automation Agent",
        "layer": "automation",
        "description": "Schedules tasks and workflows",
        "avg_tokens": 30000,
    },
    {
        "name": "Video Generation",
        "layer": "execution",
        "description": "Stock video search queries",
        "avg_tokens": 20000,
    },
    {
        "name": "Design Agent",
        "layer": "execution",
        "description": "Image placement spec (hero, feature_1, feature_2)",
        "avg_tokens": 30000,
    },
    {
        "name": "Layout Agent",
        "layer": "execution",
        "description": "Injects image placeholders into frontend",
        "avg_tokens": 40000,
    },
    {
        "name": "SEO Agent",
        "layer": "execution",
        "description": "Meta, OG, schema, sitemap, robots.txt",
        "avg_tokens": 35000,
    },
    {
        "name": "Content Agent",
        "layer": "planning",
        "description": "Landing copy: hero, features, CTA",
        "avg_tokens": 30000,
    },
    {
        "name": "Brand Agent",
        "layer": "execution",
        "description": "Colors, fonts, tone spec",
        "avg_tokens": 25000,
    },
    {
        "name": "Documentation Agent",
        "layer": "deployment",
        "description": "README: setup, env, run, deploy",
        "avg_tokens": 40000,
    },
    {
        "name": "Validation Agent",
        "layer": "validation",
        "description": "Form/API validation rules, Zod/Yup",
        "avg_tokens": 35000,
    },
    {
        "name": "Auth Setup Agent",
        "layer": "execution",
        "description": "JWT/OAuth flow, protected routes",
        "avg_tokens": 50000,
    },
    {
        "name": "Payment Setup Agent",
        "layer": "execution",
        "description": "Stripe checkout, webhooks",
        "avg_tokens": 50000,
    },
    {
        "name": "Monitoring Agent",
        "layer": "deployment",
        "description": "Sentry, analytics setup",
        "avg_tokens": 35000,
    },
    {
        "name": "Accessibility Agent",
        "layer": "validation",
        "description": "a11y improvements: ARIA, contrast",
        "avg_tokens": 30000,
    },
    {
        "name": "DevOps Agent",
        "layer": "deployment",
        "description": "CI/CD, Dockerfile",
        "avg_tokens": 40000,
    },
    {
        "name": "Webhook Agent",
        "layer": "execution",
        "description": "Webhook endpoint design",
        "avg_tokens": 35000,
    },
    {
        "name": "Email Agent",
        "layer": "execution",
        "description": "Transactional email setup",
        "avg_tokens": 35000,
    },
    {
        "name": "Legal Compliance Agent",
        "layer": "planning",
        "description": "GDPR/CCPA hints",
        "avg_tokens": 30000,
    },
    {
        "name": "GraphQL Agent",
        "layer": "execution",
        "description": "GraphQL schema and resolvers",
        "avg_tokens": 40000,
    },
    {
        "name": "WebSocket Agent",
        "layer": "execution",
        "description": "Real-time subscriptions",
        "avg_tokens": 35000,
    },
    {
        "name": "i18n Agent",
        "layer": "execution",
        "description": "Localization, translation keys",
        "avg_tokens": 30000,
    },
    {
        "name": "Caching Agent",
        "layer": "execution",
        "description": "Redis/edge caching strategy",
        "avg_tokens": 30000,
    },
    {
        "name": "Rate Limit Agent",
        "layer": "execution",
        "description": "API rate limiting, quotas",
        "avg_tokens": 30000,
    },
    {
        "name": "Search Agent",
        "layer": "execution",
        "description": "Full-text search (Algolia/Meilisearch)",
        "avg_tokens": 35000,
    },
    {
        "name": "Analytics Agent",
        "layer": "deployment",
        "description": "GA4, Mixpanel, event schema",
        "avg_tokens": 30000,
    },
    {
        "name": "API Documentation Agent",
        "layer": "execution",
        "description": "OpenAPI/Swagger from routes",
        "avg_tokens": 40000,
    },
    {
        "name": "Mobile Responsive Agent",
        "layer": "validation",
        "description": "Breakpoints, touch, PWA hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Migration Agent",
        "layer": "execution",
        "description": "DB migration scripts",
        "avg_tokens": 35000,
    },
    {
        "name": "Backup Agent",
        "layer": "deployment",
        "description": "Backup strategy, restore steps",
        "avg_tokens": 30000,
    },
    {
        "name": "Notification Agent",
        "layer": "execution",
        "description": "Push, in-app, email notifications",
        "avg_tokens": 35000,
    },
    {
        "name": "Design Iteration Agent",
        "layer": "planning",
        "description": "Feedback → spec → rebuild flow",
        "avg_tokens": 35000,
    },
    {
        "name": "Code Review Agent",
        "layer": "validation",
        "description": "Security, style, best-practice review",
        "avg_tokens": 45000,
    },
    {
        "name": "Staging Agent",
        "layer": "deployment",
        "description": "Staging env, preview URLs",
        "avg_tokens": 25000,
    },
    {
        "name": "A/B Test Agent",
        "layer": "execution",
        "description": "Experiment setup, variant routing",
        "avg_tokens": 30000,
    },
    {
        "name": "Feature Flag Agent",
        "layer": "execution",
        "description": "LaunchDarkly/Flagsmith wiring",
        "avg_tokens": 30000,
    },
    {
        "name": "Error Boundary Agent",
        "layer": "execution",
        "description": "React error boundaries, fallback UI",
        "avg_tokens": 30000,
    },
    {
        "name": "Logging Agent",
        "layer": "execution",
        "description": "Structured logs, log levels",
        "avg_tokens": 30000,
    },
    {
        "name": "Metrics Agent",
        "layer": "deployment",
        "description": "Prometheus/Datadog metrics",
        "avg_tokens": 30000,
    },
    {
        "name": "Audit Trail Agent",
        "layer": "execution",
        "description": "User action logging, audit log",
        "avg_tokens": 35000,
    },
    {
        "name": "Session Agent",
        "layer": "execution",
        "description": "Session storage, expiry, refresh",
        "avg_tokens": 30000,
    },
    {
        "name": "OAuth Provider Agent",
        "layer": "execution",
        "description": "Google/GitHub OAuth wiring",
        "avg_tokens": 40000,
    },
    {
        "name": "2FA Agent",
        "layer": "execution",
        "description": "TOTP, backup codes",
        "avg_tokens": 30000,
    },
    {
        "name": "Stripe Subscription Agent",
        "layer": "execution",
        "description": "Plans, metering, downgrade",
        "avg_tokens": 40000,
    },
    {
        "name": "Invoice Agent",
        "layer": "execution",
        "description": "Invoice generation, PDF",
        "avg_tokens": 35000,
    },
    {
        "name": "CDN Agent",
        "layer": "deployment",
        "description": "Static assets, cache headers",
        "avg_tokens": 30000,
    },
    {
        "name": "SSR Agent",
        "layer": "execution",
        "description": "Next.js SSR/SSG hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Bundle Analyzer Agent",
        "layer": "validation",
        "description": "Code splitting, chunk hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Lighthouse Agent",
        "layer": "validation",
        "description": "Performance, a11y, SEO scores",
        "avg_tokens": 35000,
    },
    {
        "name": "Schema Validation Agent",
        "layer": "execution",
        "description": "Request/response validation",
        "avg_tokens": 30000,
    },
    {
        "name": "Mock API Agent",
        "layer": "execution",
        "description": "MSW, Mirage, mock server",
        "avg_tokens": 35000,
    },
    {
        "name": "E2E Agent",
        "layer": "execution",
        "description": "Playwright/Cypress scaffolding",
        "avg_tokens": 45000,
    },
    {
        "name": "Load Test Agent",
        "layer": "execution",
        "description": "k6, Artillery scripts",
        "avg_tokens": 35000,
    },
    {
        "name": "Dependency Audit Agent",
        "layer": "validation",
        "description": "npm audit, Snyk hints",
        "avg_tokens": 30000,
    },
    {
        "name": "License Agent",
        "layer": "planning",
        "description": "OSS license compliance",
        "avg_tokens": 25000,
    },
    {
        "name": "Terms Agent",
        "layer": "planning",
        "description": "Terms of service draft",
        "avg_tokens": 30000,
    },
    {
        "name": "Privacy Policy Agent",
        "layer": "planning",
        "description": "Privacy policy draft",
        "avg_tokens": 30000,
    },
    {
        "name": "Cookie Consent Agent",
        "layer": "execution",
        "description": "Cookie banner, preferences",
        "avg_tokens": 30000,
    },
    {
        "name": "Multi-tenant Agent",
        "layer": "execution",
        "description": "Tenant isolation, schema",
        "avg_tokens": 40000,
    },
    {
        "name": "RBAC Agent",
        "layer": "execution",
        "description": "Roles, permissions matrix",
        "avg_tokens": 40000,
    },
    {
        "name": "SSO Agent",
        "layer": "execution",
        "description": "SAML, enterprise SSO",
        "avg_tokens": 40000,
    },
    {
        "name": "Audit Export Agent",
        "layer": "deployment",
        "description": "Export audit logs",
        "avg_tokens": 30000,
    },
    {
        "name": "Data Residency Agent",
        "layer": "planning",
        "description": "Region, GDPR data location",
        "avg_tokens": 30000,
    },
    {
        "name": "HIPAA Agent",
        "layer": "planning",
        "description": "Healthcare compliance hints",
        "avg_tokens": 35000,
    },
    {
        "name": "SOC2 Agent",
        "layer": "planning",
        "description": "SOC2 control hints",
        "avg_tokens": 35000,
    },
    {
        "name": "Penetration Test Agent",
        "layer": "validation",
        "description": "Pentest checklist",
        "avg_tokens": 35000,
    },
    {
        "name": "Incident Response Agent",
        "layer": "deployment",
        "description": "Runbook, escalation",
        "avg_tokens": 35000,
    },
    {
        "name": "SLA Agent",
        "layer": "deployment",
        "description": "Uptime, latency targets",
        "avg_tokens": 30000,
    },
    {
        "name": "Cost Optimizer Agent",
        "layer": "deployment",
        "description": "Cloud cost hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Accessibility WCAG Agent",
        "layer": "validation",
        "description": "WCAG 2.1 AA checklist",
        "avg_tokens": 35000,
    },
    {
        "name": "RTL Agent",
        "layer": "execution",
        "description": "Right-to-left layout",
        "avg_tokens": 25000,
    },
    {
        "name": "Dark Mode Agent",
        "layer": "execution",
        "description": "Theme toggle, contrast",
        "avg_tokens": 30000,
    },
    {
        "name": "Keyboard Nav Agent",
        "layer": "validation",
        "description": "Full keyboard navigation",
        "avg_tokens": 30000,
    },
    {
        "name": "Screen Reader Agent",
        "layer": "validation",
        "description": "Screen-reader-specific hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Component Library Agent",
        "layer": "execution",
        "description": "Shadcn/Radix usage",
        "avg_tokens": 35000,
    },
    {
        "name": "Design System Agent",
        "layer": "execution",
        "description": "Tokens, spacing, typography",
        "avg_tokens": 35000,
    },
    {
        "name": "Animation Agent",
        "layer": "execution",
        "description": "Framer Motion, transitions",
        "avg_tokens": 30000,
    },
    {
        "name": "Chart Agent",
        "layer": "execution",
        "description": "Recharts, D3 usage",
        "avg_tokens": 35000,
    },
    {
        "name": "Table Agent",
        "layer": "execution",
        "description": "Data tables, sorting, pagination",
        "avg_tokens": 35000,
    },
    {
        "name": "Form Builder Agent",
        "layer": "execution",
        "description": "Dynamic form generation",
        "avg_tokens": 40000,
    },
    {
        "name": "Workflow Agent",
        "layer": "execution",
        "description": "State machine, workflows",
        "avg_tokens": 40000,
    },
    {
        "name": "Queue Agent",
        "layer": "execution",
        "description": "Job queues, Bull/Celery",
        "avg_tokens": 40000,
    },
    # DAG-only (23 more = 123 total) — in agent_dag.py, now exposed in /api/agents
    {
        "name": "Native Config Agent",
        "layer": "execution",
        "description": "Expo/app.json, eas.json for mobile",
        "avg_tokens": 25000,
    },
    {
        "name": "Store Prep Agent",
        "layer": "deployment",
        "description": "App store submission metadata and guides",
        "avg_tokens": 35000,
    },
    {
        "name": "Vibe Analyzer Agent",
        "layer": "planning",
        "description": "Analyze project vibe, mood, aesthetic",
        "avg_tokens": 30000,
    },
    {
        "name": "Voice Context Agent",
        "layer": "planning",
        "description": "Convert voice/speech to code context",
        "avg_tokens": 30000,
    },
    {
        "name": "Video Tutorial Agent",
        "layer": "deployment",
        "description": "Video tutorial scripts and storyboards",
        "avg_tokens": 35000,
    },
    {
        "name": "Aesthetic Reasoner Agent",
        "layer": "validation",
        "description": "Evaluate code for beauty and elegance",
        "avg_tokens": 30000,
    },
    {
        "name": "Team Preferences",
        "layer": "planning",
        "description": "Capture team style and conventions",
        "avg_tokens": 25000,
    },
    {
        "name": "Collaborative Memory Agent",
        "layer": "deployment",
        "description": "Team preferences and project patterns",
        "avg_tokens": 30000,
    },
    {
        "name": "Real-time Feedback Agent",
        "layer": "validation",
        "description": "Adapt to user reactions and feedback",
        "avg_tokens": 35000,
    },
    {
        "name": "Mood Detection Agent",
        "layer": "planning",
        "description": "Detect user mood and intent",
        "avg_tokens": 25000,
    },
    {
        "name": "Accessibility Vibe Agent",
        "layer": "validation",
        "description": "Accessible and inclusive vibe",
        "avg_tokens": 30000,
    },
    {
        "name": "Performance Vibe Agent",
        "layer": "validation",
        "description": "Code that feels fast and responsive",
        "avg_tokens": 30000,
    },
    {
        "name": "Creativity Catalyst Agent",
        "layer": "planning",
        "description": "Creative improvements and innovation",
        "avg_tokens": 35000,
    },
    {
        "name": "IDE Integration Coordinator Agent",
        "layer": "execution",
        "description": "IDE extensions and plugin hooks",
        "avg_tokens": 35000,
    },
    {
        "name": "Multi-language Code Agent",
        "layer": "execution",
        "description": "Code in multiple languages",
        "avg_tokens": 40000,
    },
    {
        "name": "Team Collaboration Agent",
        "layer": "deployment",
        "description": "Collaboration workflows and review",
        "avg_tokens": 35000,
    },
    {
        "name": "User Onboarding Agent",
        "layer": "deployment",
        "description": "Onboarding and tutorial experience",
        "avg_tokens": 35000,
    },
    {
        "name": "Customization Engine Agent",
        "layer": "execution",
        "description": "User customization and themes",
        "avg_tokens": 35000,
    },
    {
        "name": "Browser Tool Agent",
        "layer": "automation",
        "description": "Playwright browser automation",
        "avg_tokens": 40000,
    },
    {
        "name": "File Tool Agent",
        "layer": "execution",
        "description": "Writes files to project workspace",
        "avg_tokens": 50000,
    },
    {
        "name": "API Tool Agent",
        "layer": "automation",
        "description": "HTTP requests and API calls",
        "avg_tokens": 35000,
    },
    {
        "name": "Database Tool Agent",
        "layer": "execution",
        "description": "Applies schema to project DB",
        "avg_tokens": 40000,
    },
    {
        "name": "Deployment Tool Agent",
        "layer": "deployment",
        "description": "Deploy to Vercel/Railway/Netlify",
        "avg_tokens": 50000,
    },
]


AGENT_TEMPLATES = [
    {
        "slug": "daily-digest",
        "name": "Daily digest",
        "description": "Generate a short daily summary and optionally email it.",
        "trigger": {"type": "schedule", "cron_expression": "0 9 * * *"},
        "actions": [
            {
                "type": "run_agent",
                "config": {
                    "agent_name": "Content Agent",
                    "prompt": "Summarize the key updates for today in 3 bullet points.",
                },
            }
        ],
    },
    {
        "slug": "youtube-poster",
        "name": "YouTube poster",
        "description": "Post or schedule content (placeholder: use HTTP action to your API).",
        "trigger": {"type": "schedule", "cron_expression": "0 17 * * *"},
        "actions": [
            {
                "type": "http",
                "config": {
                    "method": "POST",
                    "url": "https://httpbin.org/post",
                    "body": {"message": "Scheduled post"},
                },
            }
        ],
    },
    {
        "slug": "lead-finder",
        "name": "Lead finder",
        "description": "Scrape and filter leads; notify via Slack.",
        "trigger": {"type": "webhook"},
        "actions": [
            {
                "type": "run_agent",
                "config": {
                    "agent_name": "Scraping Agent",
                    "prompt": "Suggest 2-3 data sources for B2B leads.",
                },
            },
            {
                "type": "slack",
                "config": {"text": "New lead run completed.", "webhook_url": ""},
            },
        ],
    },
    {
        "slug": "inbox-summarizer",
        "name": "Inbox summarizer",
        "description": "Webhook + Content Agent + email.",
        "trigger": {"type": "webhook"},
        "actions": [
            {
                "type": "run_agent",
                "config": {
                    "agent_name": "Content Agent",
                    "prompt": "Summarize the following in 3 bullets.",
                },
            },
            {
                "type": "email",
                "config": {
                    "to": "",
                    "subject": "Summary",
                    "body": "{{steps.0.output}}",
                },
            },
        ],
    },
    {
        "slug": "status-checker",
        "name": "Status page checker",
        "description": "Schedule HTTP check; Slack on failure.",
        "trigger": {"type": "schedule", "cron_expression": "0 */6 * * *"},
        "actions": [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://api.github.com/zen"},
            },
            {
                "type": "slack",
                "config": {"text": "Status check completed.", "webhook_url": ""},
            },
        ],
    },
]


# Internal token for worker callbacks
INTERNAL_RUN_TOKEN = os.environ.get("CRUCIBAI_INTERNAL_TOKEN", "")

_webhook_idempotency: Dict[str, str] = {}
_webhook_rate: Dict[str, List[float]] = {}  # agent_id -> list of timestamps


def _check_webhook_rate_limit(agent_id: str) -> bool:
    """True if under limit (WEBHOOK_RATE_LIMIT_PER_MINUTE/min)."""
    now = datetime.now(timezone.utc).timestamp()
    if agent_id not in _webhook_rate:
        _webhook_rate[agent_id] = []
    lst = _webhook_rate[agent_id]
    lst[:] = [t for t in lst if now - t < 60]
    if len(lst) >= WEBHOOK_RATE_LIMIT_PER_MINUTE:
        return False
    lst.append(now)
    return True


def _user_credits(user: Optional[dict]) -> int:
    if not user:
        return 0
    if user.get("credit_balance") is not None:
        return int(user["credit_balance"])
    return int((user.get("token_balance") or 0) // CREDITS_PER_TOKEN)


async def _ensure_credit_balance(user_id: str) -> None:
    db = get_db()
    doc = await db.users.find_one(
        {"id": user_id}, {"credit_balance": 1, "token_balance": 1}
    )
    if not doc or doc.get("credit_balance") is not None:
        return
    cred = (doc.get("token_balance") or 0) // CREDITS_PER_TOKEN
    await db.users.update_one({"id": user_id}, {"$set": {"credit_balance": cred}})


@agents_router.get("/agents")
async def get_agents():
    return {"agents": AGENT_DEFINITIONS}


@agents_router.get("/agents/status/{project_id}")
async def get_agent_status(project_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]}, {"id": 1}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statuses = await db.agent_status.find(
        {"project_id": project_id}, {"_id": 0}
    ).to_list(100)
    if not statuses:
        return {
            "statuses": [
                {
                    "agent_name": a["name"],
                    "status": "idle",
                    "progress": 0,
                    "tokens_used": 0,
                }
                for a in AGENT_DEFINITIONS
            ]
        }
    return {"statuses": statuses}


# ---------- Agent execution (real LLM/logic per agent) ----------


@agents_router.post("/agents/run/planner")
async def agent_planner(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Planner: decomposes user request into executable tasks."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Planner agent. Decompose the user's request into 3-7 clear, executable tasks. Output a numbered list only, no extra text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Planner", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/requirements-clarifier")
async def agent_requirements_clarifier(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Requirements Clarifier: asks clarifying questions."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Requirements Clarifier. Based on the request, ask 2-4 short clarifying questions to reduce ambiguity. One question per line."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Requirements Clarifier",
        "result": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/stack-selector")
async def agent_stack_selector(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Stack Selector: recommends technology stack."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Stack Selector. Recommend a concise tech stack (frontend, backend, DB, tools) for the request. Output as a short bullet list with brief rationale."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Stack Selector", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/backend-generate")
async def agent_backend_generate(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Backend Generation: creates API/auth/business logic code."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Backend Generation agent. Output only valid code (e.g. Python FastAPI or Node Express). No markdown fences or explanation. Include one clear endpoint and structure."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    if code.startswith("python"):
        code = code[6:].strip()
    return {"agent": "Backend Generation", "code": code, "model_used": model_used}


@agents_router.post("/agents/run/database-design")
async def agent_database_design(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Database Agent: designs schema and migrations."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Database Agent. Output a clear schema design: table/collection names, key fields, and 1-2 migration steps. Use plain text or SQL."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Database Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/api-integrate")
async def agent_api_integrate(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """API Integration: generates code to integrate a third-party API."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an API Integration agent. Given an API description or URL, output only code (e.g. JavaScript or Python) that fetches and uses the API. No markdown."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    return {"agent": "API Integration", "code": code, "model_used": model_used}


@agents_router.post("/agents/run/test-generate")
async def agent_test_generate(
    data: AgentCodeBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Test Generation: writes test suite for given code."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Test Generation agent. Output only test code (e.g. Jest, pytest) for the given code. No markdown fences or explanation."
    prompt = f"Generate tests for this {data.language} code:\n\n{data.code[:8000]}"
    response, model_used = await _call_llm_with_fallback(
        message=prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    return {"agent": "Test Generation", "code": code, "model_used": model_used}


@agents_router.post("/agents/run/image-generate")
async def agent_image_generate(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Image Generation: returns detailed image spec/prompt for visual creation (or calls DALL-E if available)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Image Generation agent. Given a request, output a detailed image generation prompt (style, composition, colors, size hint) suitable for DALL-E or similar. One paragraph."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Image Generation",
        "result": response,
        "prompt_spec": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/test-executor")
async def agent_test_executor(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Test Executor: returns how to run tests and validates test file presence."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Test Executor agent. Given a project type (e.g. React, Python), reply with exactly: 1) the command to run tests (e.g. npm test, pytest), 2) one line on what to check."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Test Executor",
        "result": response,
        "command_hint": "Run the command above in your project root.",
        "model_used": model_used,
    }


@agents_router.post("/agents/run/deploy")
async def agent_deploy(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Deployment Agent: returns deploy instructions or triggers deploy."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Deployment Agent. For the given project type, output concise step-by-step deploy instructions (e.g. Vercel, Netlify, or Docker). Number the steps."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Deployment Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/memory-store")
async def agent_memory_store(
    data: AgentMemoryBody, user: dict = Depends(get_current_user)
):
    """Memory Agent: store a pattern for reuse."""
    db = get_db()
    doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "content": data.content,
        "user_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_memory.insert_one(doc)
    return {"agent": "Memory Agent", "action": "stored", "id": doc["id"]}


@agents_router.get("/agents/run/memory-list")
async def agent_memory_list(user: dict = Depends(get_current_user)):
    """Memory Agent: list stored patterns."""
    db = get_db()
    cursor = (
        db.agent_memory.find({"user_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(50)
    )
    items = await cursor.to_list(length=50)
    return {"agent": "Memory Agent", "items": items}


@agents_router.post("/agents/run/export-pdf")
async def agent_export_pdf(
    data: AgentExportPdfBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """PDF Export: generates a PDF from title and content."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.setFont("Helvetica", 16)
        c.drawString(72, 750, (data.title or "Report")[:80])
        c.setFont("Helvetica", 10)
        y = 720
        for line in (data.content or "").replace("\r\n", "\n").split("\n")[:200]:
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = 750
            c.drawString(72, y, line[:100])
            y -= 14
        c.save()
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=report.pdf"},
        )
    except ImportError:
        raise HTTPException(
            status_code=501, detail="reportlab not installed. pip install reportlab"
        )


@agents_router.post("/agents/run/export-excel")
async def agent_export_excel(
    data: AgentExportExcelBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Excel Export: creates a spreadsheet from rows."""
    try:
        import openpyxl
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = (data.title or "Sheet")[:31]
        rows = data.rows or []
        if rows:
            headers = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            if headers:
                ws.append(headers)
                for r in rows[1:]:
                    ws.append([r.get(h, "") for h in headers])
        wb.save(buf := io.BytesIO())
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"},
        )
    except ImportError:
        raise HTTPException(
            status_code=501, detail="openpyxl not installed. pip install openpyxl"
        )


@agents_router.post("/agents/run/export-markdown")
async def agent_export_markdown(
    data: AgentExportMarkdownBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Markdown Export: returns a .md file from title and content (optional item 40)."""
    title = (data.title or "Export").strip()[:80]
    content = (data.content or "").strip()
    body = f"# {title}\n\n{content}\n"
    return Response(
        content=body,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{title.replace(" ", "-")[:60]}.md"'
        },
    )


@agents_router.post("/agents/run/scrape")
async def agent_scrape(
    data: AgentScrapeBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Scraping Agent: fetches URL and extracts main content with LLM. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.get(data.url, timeout=15)
        r.raise_for_status()
        html = r.text[:15000]
    system = "You are a Scraping Agent. Extract the main text content from this HTML. Return clean plain text only, no HTML tags. Summarize if very long."
    response, model_used = await _call_llm_with_fallback(
        message=f"URL: {data.url}\n\nHTML snippet:\n{html[:8000]}",
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", html, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Scraping Agent",
        "result": response,
        "url": data.url,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/automation")
async def agent_automation(
    data: AgentAutomationBody, user: dict = Depends(get_current_user)
):
    """Automation Agent: schedules a task (store and optional run_at)."""
    db = get_db()
    doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "prompt": data.prompt,
        "run_at": data.run_at or datetime.now(timezone.utc).isoformat(),
        "status": "scheduled",
        "user_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.automation_tasks.insert_one(doc)
    return {
        "agent": "Automation Agent",
        "action": "scheduled",
        "id": doc["id"],
        "run_at": doc["run_at"],
    }


@agents_router.get("/agents/run/automation-list")
async def agent_automation_list(user: dict = Depends(get_current_user)):
    """List scheduled automation tasks."""
    db = get_db()
    cursor = (
        db.automation_tasks.find({"user_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(50)
    )
    items = await cursor.to_list(length=50)
    return {"agent": "Automation Agent", "items": items}


# ---------- New agents (Design, SEO, Content, etc.) ----------


@agents_router.post("/agents/run/design")
async def agent_design(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Design Agent: image placement spec (hero, feature_1, feature_2)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = 'You are a Design Agent. Output ONLY a JSON object with keys: hero, feature_1, feature_2. Each value: { "position": "top-full|sidebar|grid", "aspect": "16:9|1:1|4:3", "role": "hero|feature|testimonial" }. No markdown.'
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Design Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/layout")
async def agent_layout(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Layout Agent: inject image placeholders into frontend."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Layout Agent. Given frontend code and image specs, output updated React/JSX with image placeholders (img tags with data-image-slot) in correct positions. No markdown."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Layout Agent",
        "result": response,
        "code": (response or "")
        .strip()
        .removeprefix("```")
        .removesuffix("```")
        .strip(),
        "model_used": model_used,
    }


@agents_router.post("/agents/run/seo")
async def agent_seo(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """SEO Agent: meta tags, OG, schema, sitemap, robots."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an SEO Agent. Output meta tags, Open Graph, Twitter Card, JSON-LD schema, sitemap hints, robots.txt rules. Plain text or JSON."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "SEO Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/content")
async def agent_content(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Content Agent: landing copy (hero, features, CTA)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Content Agent. Write landing page copy: hero headline, 3 feature blurbs (2 lines each), CTA text. Plain text, one section per line."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Content Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/brand")
async def agent_brand(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Brand Agent: colors, fonts, tone."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Brand Agent. Output a JSON with: primary_color, secondary_color, font_heading, font_body, tone (e.g. professional, playful). No markdown."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Brand Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/documentation")
async def agent_documentation(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Documentation Agent: README sections."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Documentation Agent. Output README sections: setup, env vars, run commands, deploy steps. Markdown."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Documentation Agent",
        "result": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/validation")
async def agent_validation(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Validation Agent: form/API validation rules, Zod/Yup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Validation Agent. List 3-5 form/API validation rules and suggest Zod/Yup schemas. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Validation Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/auth-setup")
async def agent_auth_setup(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Auth Setup Agent: JWT/OAuth2 flow."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Auth Setup Agent. Suggest JWT/OAuth2 flow: login, logout, token refresh, protected routes. Code or step list."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Auth Setup Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/payment-setup")
async def agent_payment_setup(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Payment Setup Agent: Stripe integration."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Payment Setup Agent. Suggest Stripe (or similar) integration: checkout, webhooks, subscription. Code or step list."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Payment Setup Agent",
        "result": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/monitoring")
async def agent_monitoring(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Monitoring Agent: Sentry/analytics setup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Monitoring Agent. Suggest Sentry/analytics setup: error tracking, performance, user events. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Monitoring Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/accessibility")
async def agent_accessibility(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Accessibility Agent: a11y improvements."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Accessibility Agent. List 3-5 a11y improvements: ARIA, focus, contrast, screen reader. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Accessibility Agent",
        "result": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/devops")
async def agent_devops(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """DevOps Agent: CI/CD, Dockerfile."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a DevOps Agent. Suggest CI/CD (GitHub Actions), Dockerfile, env config. Plain text or YAML."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "DevOps Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/webhook")
async def agent_webhook(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Webhook Agent: webhook endpoint design."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Webhook Agent. Suggest webhook endpoint design: payload, signature verification, retries. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Webhook Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/email")
async def agent_email(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Email Agent: transactional email setup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Email Agent. Suggest transactional email setup: provider (Resend/SendGrid), templates, verification. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Email Agent", "result": response, "model_used": model_used}


@agents_router.post("/agents/run/legal-compliance")
async def agent_legal_compliance(
    data: AgentPromptBody, user: dict = Depends(get_authenticated_or_api_user)
):
    """Legal Compliance Agent: GDPR/CCPA hints."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Legal Compliance Agent. Suggest GDPR/CCPA items: cookie banner, privacy link, data retention. Plain text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {
        "agent": "Legal Compliance Agent",
        "result": response,
        "model_used": model_used,
    }


@agents_router.post("/agents/run/generic")
async def agent_run_generic(
    data: AgentGenericRunBody, user: dict = Depends(get_current_user)
):
    """Run any agent by name (100-agent roster). Uses system prompt from agent DAG."""
    if data.agent_name not in AGENT_DAG:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {data.agent_name}")
    system = get_system_prompt_for_agent(data.agent_name)
    if not system:
        system = f"You are {data.agent_name}. Fulfill the user request. Output concise, actionable text or code as appropriate."
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": data.agent_name, "result": response, "model_used": model_used}


@agents_router.post("/agents/run-internal")
async def agents_run_internal(data: RunInternalBody, request: Request):
    """Internal: worker calls this to run an agent by name (validates X-Internal-Token). No user JWT."""
    db = get_db()
    token = (request.headers.get("X-Internal-Token") or "").strip()
    if not INTERNAL_RUN_TOKEN or token != INTERNAL_RUN_TOKEN:
        raise HTTPException(
            status_code=401, detail="Invalid or missing X-Internal-Token"
        )
    agent_name = data.agent_name
    if agent_name not in AGENT_DAG:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")
    if data.user_id == INTERNAL_USER_ID:
        user = None
        user_keys = {}
    else:
        user = await db.users.find_one({"id": data.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = (
        get_system_prompt_for_agent(agent_name)
        or f"You are {agent_name}. Fulfill the request."
    )
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"result": response, "model_used": model_used}


# Webhook idempotency: (agent_id, idempotency_key) -> last run_id (in-memory for single process; use Redis in multi-instance)
@agents_router.post("/agents/webhook/{agent_id}")
async def agents_webhook_trigger(
    agent_id: str, request: Request, secret: Optional[str] = Query(None)
):
    """Trigger agent run via webhook. Query param secret= or header X-Webhook-Secret. Returns 202 + run_id."""
    db = get_db()
    raw_secret = secret or request.headers.get("X-Webhook-Secret") or ""
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    agent = await db.user_agents.find_one({"id": agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.get("enabled"):
        raise HTTPException(status_code=400, detail="Agent is disabled")
    cfg = agent.get("trigger_config") or {}
    if cfg.get("type") != "webhook":
        raise HTTPException(status_code=400, detail="Agent is not webhook-triggered")
    if (cfg.get("webhook_secret") or "").strip() != raw_secret.strip():
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    if not _check_webhook_rate_limit(agent_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    now_iso = datetime.now(timezone.utc).isoformat()
    if idempotency_key:
        key = f"{agent_id}:{idempotency_key}"
        if key in _webhook_idempotency:
            run_id = _webhook_idempotency[key]
            return Response(
                status_code=202,
                content=json.dumps({"run_id": run_id}),
                media_type="application/json",
            )
    user_id = agent.get("user_id") or ""
    if user_id and user_id != INTERNAL_USER_ID:
        cred = _user_credits(await db.users.find_one({"id": user_id}) or {})
        if cred < CREDITS_PER_AGENT_RUN:
            raise HTTPException(
                status_code=402, detail="Insufficient credits for agent run"
            )
        running = await db.agent_runs.count_documents(
            {"user_id": user_id, "status": "running"}
        )
        if running >= MAX_CONCURRENT_RUNS_PER_USER:
            raise HTTPException(status_code=429, detail="Too many concurrent runs")
    run_id = str(uuid.uuid4())
    await db.agent_runs.insert_one(
        {
            "id": run_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "triggered_at": now_iso,
            "triggered_by": "webhook",
            "status": "running",
            "started_at": now_iso,
            "output_summary": {},
            "log_lines": [],
        }
    )
    if user_id and user_id != INTERNAL_USER_ID:
        await db.users.update_one(
            {"id": user_id}, {"$inc": {"credit_balance": -CREDITS_PER_AGENT_RUN}}
        )

    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(
            message=prompt,
            system_message=sys_p,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=eff),
            api_keys=eff,
        )
        return {"result": r}

    try:
        status, output_summary, log_lines, _ = await run_actions(
            agent,
            user_id,
            run_id,
            [],
            run_agent_callback=_run_agent_cb,
        )
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": status,
                "finished_at": finished,
                "output_summary": output_summary,
                "log_lines": log_lines[-1000:],
            }
        },
    )
    if idempotency_key:
        _webhook_idempotency[f"{agent_id}:{idempotency_key}"] = run_id
    return Response(
        status_code=202,
        content=json.dumps({"run_id": run_id}),
        media_type="application/json",
    )


@agents_router.post("/agents", response_model=None)
async def agents_create(
    data: AgentCreate, request: Request, user: dict = Depends(get_current_user)
):
    """Create a user agent (schedule or webhook + actions)."""
    db = get_db()
    await _ensure_credit_balance(user["id"])
    agent_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    trigger = data.trigger
    trigger_type = trigger.type
    trigger_config = {"type": trigger_type}
    if trigger_type == "schedule":
        trigger_config["cron_expression"] = trigger.cron_expression
        trigger_config["run_at"] = trigger.run_at
        next_ = next_run_at(
            cron_expression=trigger.cron_expression, run_at=trigger.run_at
        )
        trigger_config["next_run_at"] = next_.isoformat() if next_ else None
    else:
        webhook_secret = trigger.webhook_secret or secrets.token_urlsafe(24)
        trigger_config["webhook_secret"] = webhook_secret
    actions = [
        {"type": a.type, "config": a.config, "approval_required": a.approval_required}
        for a in data.actions
    ]
    doc = {
        "id": agent_id,
        "user_id": user["id"],
        "name": data.name,
        "description": data.description or "",
        "trigger_type": trigger_type,
        "trigger_config": trigger_config,
        "actions": actions,
        "enabled": data.enabled,
        "created_at": now,
        "updated_at": now,
        "next_run_at": trigger_config.get("next_run_at"),
    }
    await db.user_agents.insert_one(doc)
    _bu = os.environ.get("FRONTEND_URL") or str(request.base_url)
    base_url = _bu.rstrip("/")
    webhook_url = (
        f"{base_url}/api/agents/webhook/{agent_id}?secret={trigger_config.get('webhook_secret', '')}"
        if trigger_type == "webhook"
        else None
    )
    return {
        "id": agent_id,
        "user_id": user["id"],
        "name": doc["name"],
        "description": doc["description"],
        "trigger_type": trigger_type,
        "trigger_config": trigger_config,
        "actions": actions,
        "enabled": doc["enabled"],
        "created_at": now,
        "updated_at": now,
        "webhook_url": webhook_url,
    }


@agents_router.get("/agents/mine")
async def agents_list(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """List current user's automation agents (saved schedules/webhooks)."""
    db = get_db()
    cursor = (
        db.user_agents.find({"user_id": user["id"]})
        .sort("updated_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    out = []
    for a in items:
        last = await db.agent_runs.find_one(
            {"agent_id": a["id"]},
            sort=[("triggered_at", -1)],
            projection={"status": 1, "triggered_at": 1},
        )
        run_count = await db.agent_runs.count_documents({"agent_id": a["id"]})
        tc = dict(a.get("trigger_config") or {})
        tc.pop("webhook_secret", None)
        out.append(
            {
                "id": a["id"],
                "user_id": a["user_id"],
                "name": a["name"],
                "description": a.get("description"),
                "trigger_type": a["trigger_type"],
                "trigger_config": tc,
                "actions": a.get("actions", []),
                "enabled": a.get("enabled", True),
                "created_at": a["created_at"],
                "updated_at": a["updated_at"],
                "run_count": run_count,
                "last_run_at": last["triggered_at"] if last else None,
                "last_run_status": last.get("status") if last else None,
            }
        )
    return {
        "items": out,
        "total": await db.user_agents.count_documents({"user_id": user["id"]}),
    }


@agents_router.get("/agents/templates")
async def agents_templates_list():
    """List agent templates (no auth required for listing)."""
    return {
        "templates": [
            {"slug": t["slug"], "name": t["name"], "description": t["description"]}
            for t in AGENT_TEMPLATES
        ]
    }


@agents_router.get("/agents/templates/{slug}")
async def agents_template_get(slug: str):
    """Get one template by slug."""
    t = next((x for x in AGENT_TEMPLATES if x["slug"] == slug), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@agents_router.get("/agents/activity")
async def get_agents_activity(
    session_id: Optional[str] = None, user: dict = Depends(get_optional_user)
):
    """Return recent agent activity for the Agents panel (Cursor-style)."""
    db = get_db()
    if not user:
        return {"activities": []}
    cursor = (
        db.chat_history.find(
            {"user_id": user["id"]},
            {
                "session_id": 1,
                "message": 1,
                "model": 1,
                "tokens_used": 1,
                "created_at": 1,
            },
        )
        .sort("created_at", -1)
        .limit(30)
    )
    activities = []
    seen = set()
    async for row in cursor:
        sid = row.get("session_id") or "default"
        key = (sid, row.get("created_at", "")[:19])
        if key in seen:
            continue
        seen.add(key)
        activities.append(
            {
                "session_id": sid,
                "message": (row.get("message") or "")[:80],
                "model": row.get("model"),
                "tokens_used": row.get("tokens_used", 0),
                "created_at": row.get("created_at"),
            }
        )
    return {"activities": activities[:20]}


@agents_router.get("/agents/{agent_id}")
async def agents_get(agent_id: str, user: dict = Depends(get_current_user)):
    """Get one agent (own only)."""
    db = get_db()
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    last = await db.agent_runs.find_one(
        {"agent_id": agent_id},
        sort=[("triggered_at", -1)],
        projection={"status": 1, "triggered_at": 1},
    )
    run_count = await db.agent_runs.count_documents({"agent_id": agent_id})
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    webhook_url = (
        f"{base}/api/agents/webhook/{agent_id}?secret={agent.get('trigger_config', {}).get('webhook_secret', '')}"
        if agent.get("trigger_type") == "webhook"
        else None
    )
    return {
        "id": agent["id"],
        "user_id": agent["user_id"],
        "name": agent["name"],
        "description": agent.get("description"),
        "trigger_type": agent["trigger_type"],
        "trigger_config": agent.get("trigger_config", {}),
        "actions": agent.get("actions", []),
        "enabled": agent.get("enabled", True),
        "created_at": agent["created_at"],
        "updated_at": agent["updated_at"],
        "webhook_url": webhook_url,
        "run_count": run_count,
        "last_run_at": last["triggered_at"] if last else None,
        "last_run_status": last.get("status") if last else None,
    }


@agents_router.post("/agents/{agent_id}/webhook-rotate-secret")
async def agents_webhook_rotate_secret(
    agent_id: str, request: Request, user: dict = Depends(get_current_user)
):
    """Rotate webhook secret for a webhook-triggered agent. Returns new secret and URL once; update your caller."""
    db = get_db()
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.get("trigger_type") != "webhook":
        raise HTTPException(status_code=400, detail="Agent is not webhook-triggered")
    new_secret = secrets.token_urlsafe(24)
    base = os.environ.get("FRONTEND_URL", request.base_url.rstrip("/")).rstrip("/")
    webhook_url = f"{base}/api/agents/webhook/{agent_id}?secret={new_secret}"
    tc = dict(agent.get("trigger_config") or {})
    tc["webhook_secret"] = new_secret
    now = datetime.now(timezone.utc).isoformat()
    await db.user_agents.update_one(
        {"id": agent_id, "user_id": user["id"]},
        {"$set": {"trigger_config": tc, "updated_at": now}},
    )
    return {"webhook_secret": new_secret, "webhook_url": webhook_url}


@agents_router.patch("/agents/{agent_id}")
async def agents_update(
    agent_id: str, data: AgentUpdate, user: dict = Depends(get_current_user)
):
    """Update agent (partial)."""
    db = get_db()
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = datetime.now(timezone.utc).isoformat()
    updates = {"updated_at": now}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.enabled is not None:
        updates["enabled"] = data.enabled
    if data.trigger is not None:
        tc = {
            "type": data.trigger.type,
            "cron_expression": data.trigger.cron_expression,
            "run_at": data.trigger.run_at,
            "webhook_secret": data.trigger.webhook_secret
            or (agent.get("trigger_config") or {}).get("webhook_secret"),
        }
        if data.trigger.type == "schedule":
            next_ = next_run_at(
                cron_expression=data.trigger.cron_expression, run_at=data.trigger.run_at
            )
            tc["next_run_at"] = next_.isoformat() if next_ else None
        updates["trigger_config"] = tc
        updates["trigger_type"] = data.trigger.type
        updates["next_run_at"] = tc.get("next_run_at")
    if data.actions is not None:
        updates["actions"] = [
            {
                "type": a.type,
                "config": a.config,
                "approval_required": a.approval_required,
            }
            for a in data.actions
        ]
    await db.user_agents.update_one(
        {"id": agent_id, "user_id": user["id"]}, {"$set": updates}
    )
    return {"ok": True, "id": agent_id}


@agents_router.delete("/agents/{agent_id}")
async def agents_delete(agent_id: str, user: dict = Depends(get_current_user)):
    """Delete agent (own only)."""
    db = get_db()
    r = await db.user_agents.delete_one({"id": agent_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True, "id": agent_id}


@agents_router.get("/agents/{agent_id}/runs")
async def agents_runs_list(
    agent_id: str,
    user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """List runs for an agent (own only)."""
    db = get_db()
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    cursor = (
        db.agent_runs.find({"agent_id": agent_id})
        .sort("triggered_at", -1)
        .skip(offset)
        .limit(limit)
    )
    runs = await cursor.to_list(length=limit)
    out = []
    for r in runs:
        started = r.get("started_at")
        finished = r.get("finished_at")
        dur = None
        if started and finished:
            try:
                from dateutil import parser as date_parser

                d1 = date_parser.isoparse(started)
                d2 = date_parser.isoparse(finished)
                dur = (d2 - d1).total_seconds()
            except Exception:
                pass
        out.append(
            {
                "id": r["id"],
                "agent_id": r["agent_id"],
                "user_id": r["user_id"],
                "triggered_at": r["triggered_at"],
                "triggered_by": r.get("triggered_by", "schedule"),
                "status": r["status"],
                "started_at": started,
                "finished_at": finished,
                "duration_seconds": dur,
                "error_message": r.get("error_message"),
                "output_summary": r.get("output_summary"),
                "step_index": r.get("step_index"),
            }
        )
    return {
        "items": out,
        "total": await db.agent_runs.count_documents({"agent_id": agent_id}),
    }


@agents_router.get("/agents/runs/{run_id}")
async def agents_run_get(run_id: str, user: dict = Depends(get_current_user)):
    """Get single run (own only, via agent ownership)."""
    db = get_db()
    run = await db.agent_runs.find_one({"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = await db.user_agents.find_one(
        {"id": run["agent_id"], "user_id": user["id"]}
    )
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    started = run.get("started_at")
    finished = run.get("finished_at")
    dur = None
    if started and finished:
        try:
            from dateutil import parser as date_parser

            d1 = date_parser.isoparse(started)
            d2 = date_parser.isoparse(finished)
            dur = (d2 - d1).total_seconds()
        except Exception:
            pass
    return {
        "id": run["id"],
        "agent_id": run["agent_id"],
        "user_id": run["user_id"],
        "triggered_at": run["triggered_at"],
        "triggered_by": run.get("triggered_by"),
        "status": run["status"],
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": dur,
        "error_message": run.get("error_message"),
        "output_summary": run.get("output_summary"),
        "step_index": run.get("step_index"),
    }


@agents_router.get("/agents/runs/{run_id}/logs")
async def agents_run_logs(run_id: str, user: dict = Depends(get_current_user)):
    """Get log lines for a run (own only)."""
    db = get_db()
    run = await db.agent_runs.find_one({"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = await db.user_agents.find_one(
        {"id": run["agent_id"], "user_id": user["id"]}
    )
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"run_id": run_id, "log_lines": run.get("log_lines", [])}


@agents_router.post("/agents/{agent_id}/run")
async def agents_trigger_run(agent_id: str, user: dict = Depends(get_current_user)):
    """Trigger a run now (manual). Returns run_id."""
    db = get_db()
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    cred = _user_credits(user)
    if cred < CREDITS_PER_AGENT_RUN:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {CREDITS_PER_AGENT_RUN}, have {cred}.",
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    await db.agent_runs.insert_one(
        {
            "id": run_id,
            "agent_id": agent_id,
            "user_id": user["id"],
            "triggered_at": now_iso,
            "triggered_by": "manual",
            "status": "running",
            "started_at": now_iso,
            "output_summary": {},
            "log_lines": [],
        }
    )
    await db.users.update_one(
        {"id": user["id"]}, {"$inc": {"credit_balance": -CREDITS_PER_AGENT_RUN}}
    )

    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(
            message=prompt,
            system_message=sys_p,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=eff),
            api_keys=eff,
        )
        return {"result": r}

    try:
        status, output_summary, log_lines, _ = await run_actions(
            agent, user["id"], run_id, [], run_agent_callback=_run_agent_cb
        )
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": status,
                "finished_at": finished,
                "output_summary": output_summary,
                "log_lines": log_lines[-1000:],
            }
        },
    )
    return {"run_id": run_id, "status": status}


@agents_router.post("/agents/from-description")
async def agents_from_description(
    data: FromDescriptionBody, request: Request, user: dict = Depends(get_current_user)
):
    """Create an agent from a natural language description (prompt-to-automation). Uses LLM to produce trigger + actions, then creates the agent."""
    cred = _user_credits(user)
    if cred < MIN_CREDITS_FOR_LLM:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need at least {MIN_CREDITS_FOR_LLM} for prompt-to-automation. Buy more in Credit Center.",
        )
    await _ensure_credit_balance(user["id"])
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.description, effective_keys=effective)
    system = """You are an automation designer. Given the user's description of an automation, output ONLY a single valid JSON object (no markdown, no code fence, no explanation) with exactly these keys:
- "name": short title for the agent (e.g. "Daily summary")
- "description": one sentence describing what it does
- "trigger": object with "type" ("schedule" or "webhook"). If schedule, add "cron_expression": standard 5-field cron, e.g. "0 9 * * *" for 9am daily, "0 */6 * * *" for every 6 hours, "0 0 * * *" for midnight daily
- "actions": array of action objects. Each has "type" and "config".
  Action types: "http" (config: method, url, optional headers, optional body), "email" (to, subject, body; body can use {{steps.0.output}} for previous step output), "slack" (webhook_url, text), "run_agent" (agent_name: one of Content Agent, Scraping Agent, etc.; prompt: string, can use {{steps.0.output}}).
  For "every day at 9am" use cron_expression "0 9 * * *". For "every 6 hours" use "0 */6 * * *". For webhook use trigger type "webhook" and no cron.
Output only the JSON object, nothing else."""
    try:
        response, _ = await _call_llm_with_fallback(
            message=data.description,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
    except Exception as e:
        logger.exception("agents_from_description LLM failed")
        raise HTTPException(
            status_code=502, detail=f"Could not generate automation: {str(e)}"
        )
    raw = (response or "").strip()
    json_str = raw
    if "```" in raw:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            json_str = m.group(1).strip()
    try:
        spec = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("agents_from_description invalid JSON: %s", raw[:500])
        raise HTTPException(
            status_code=422,
            detail="Generated spec was not valid JSON. Try a clearer description.",
        )
    name = (spec.get("name") or "My automation").strip() or "My automation"
    description = (spec.get("description") or "").strip()
    trigger_spec = spec.get("trigger") or {}
    trigger_type = (trigger_spec.get("type") or "schedule").lower()
    if trigger_type not in ("schedule", "webhook"):
        trigger_type = "schedule"
    if trigger_type == "schedule":
        cron = (trigger_spec.get("cron_expression") or "0 9 * * *").strip()
        trigger_config = TriggerConfig(
            type="schedule",
            cron_expression=cron or "0 9 * * *",
            run_at=None,
            webhook_secret=None,
        )
    else:
        trigger_config = TriggerConfig(
            type="webhook", cron_expression=None, run_at=None, webhook_secret=None
        )
    actions_spec = spec.get("actions") or []
    if not actions_spec:
        actions_spec = [
            {
                "type": "http",
                "config": {"method": "GET", "url": "https://httpbin.org/get"},
            }
        ]
    action_configs = []
    for a in actions_spec[:20]:
        if not isinstance(a, dict):
            continue
        atype = (a.get("type") or "http").lower()
        aconfig = a.get("config") or a
        if not isinstance(aconfig, dict):
            aconfig = {}
        action_configs.append(
            ActionConfig(
                type=atype,
                config=aconfig,
                approval_required=a.get("approval_required", False),
            )
        )
    if not action_configs:
        action_configs = [
            ActionConfig(
                type="http",
                config={"method": "GET", "url": "https://httpbin.org/get"},
                approval_required=False,
            )
        ]
    create = AgentCreate(
        name=name,
        description=description or None,
        trigger=trigger_config,
        actions=action_configs,
        enabled=True,
    )
    deduct = 3
    db = get_db()
    if cred >= deduct:
        await db.users.update_one(
            {"id": user["id"]}, {"$inc": {"credit_balance": -deduct}}
        )
    return await agents_create(create, request, user)


@agents_router.post("/agents/from-template")
async def agents_from_template(
    data: FromTemplateBody, request: Request, user: dict = Depends(get_current_user)
):
    """Create an agent from a template (overrides: name, description, trigger, actions)."""
    t = next((x for x in AGENT_TEMPLATES if x["slug"] == data.template_slug), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    overrides = data.overrides or {}
    name = overrides.get("name") or t["name"]
    description = overrides.get("description") or t.get("description", "")
    trigger = overrides.get("trigger") or t["trigger"]
    actions = overrides.get("actions") or t["actions"]
    trigger_config = TriggerConfig(**trigger) if isinstance(trigger, dict) else trigger
    action_configs = [ActionConfig(**a) if isinstance(a, dict) else a for a in actions]
    create = AgentCreate(
        name=name,
        description=description,
        trigger=trigger_config,
        actions=action_configs,
        enabled=True,
    )
    return await agents_create(create, request, user)


@agents_router.post("/agents/runs/{run_id}/approve")
async def agents_run_approve(
    run_id: str,
    user: dict = Depends(get_current_user),
    comment: Optional[str] = Body(None),
):
    """Resume a run that is waiting_approval (owner only)."""
    db = get_db()
    run = await db.agent_runs.find_one({"id": run_id})
    if not run or run["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "waiting_approval":
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")
    agent = await db.user_agents.find_one(
        {"id": run["agent_id"], "user_id": user["id"]}
    )
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    step_index = (run.get("step_index") or 0) + 1
    steps_context = [
        s.get("output") for s in (run.get("output_summary") or {}).get("steps", [])
    ]
    steps_context = [{"output": x} for x in steps_context]

    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(
            message=prompt,
            system_message=sys_p,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=eff),
            api_keys=eff,
        )
        return {"result": r}

    try:
        status, output_summary, log_lines, _ = await run_actions(
            agent,
            user["id"],
            run_id,
            steps_context,
            run_agent_callback=_run_agent_cb,
            resume_from_step=step_index,
        )
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": status,
                "finished_at": finished,
                "output_summary": output_summary,
                "log_lines": run.get("log_lines", []) + log_lines,
                "step_index": None,
            }
        },
    )
    return {"ok": True, "run_id": run_id, "status": status}


@agents_router.post("/agents/runs/{run_id}/reject")
async def agents_run_reject(
    run_id: str,
    user: dict = Depends(get_current_user),
    comment: Optional[str] = Body(None),
):
    """Cancel a run that is waiting_approval."""
    db = get_db()
    run = await db.agent_runs.find_one({"id": run_id})
    if not run or run["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "waiting_approval":
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one(
        {"id": run_id}, {"$set": {"status": "cancelled", "finished_at": finished}}
    )
    return {"ok": True, "run_id": run_id, "status": "cancelled"}
