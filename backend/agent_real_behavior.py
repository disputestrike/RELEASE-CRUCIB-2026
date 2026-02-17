"""
Maps all 120 DAG agents to real behavior: state write, artifact (file) write, or tool run.
Called after each agent run so every agent has a verifiable effect (state, file, or tool result).
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from project_state import load_state, update_state
from tool_executor import execute_tool

logger = logging.getLogger(__name__)

# --- Behavior types ---
# state: write LLM output (or parsed) to state[state_key]
# artifact: write content to workspace file at artifact_path
# tool_run: run allowlisted command, write output to state[state_key]
# (tool agents File/Browser/API/DB/Deployment are already real; we only append tool_log optionally)

STATE_WRITERS: Dict[str, str] = {
    "Planner": "plan",
    "Requirements Clarifier": "requirements",
    "Stack Selector": "stack",
    "Design Agent": "design_spec",
    "Brand Agent": "brand_spec",
    "Memory Agent": "memory_summary",
    "Deployment Agent": "deploy_result",
    "Vibe Analyzer Agent": "vibe_spec",
    "Voice Context Agent": "voice_requirements",
    "Aesthetic Reasoner Agent": "aesthetic_report",
    "Collaborative Memory Agent": "team_preferences",
    "Real-time Feedback Agent": "feedback_log",
    "Mood Detection Agent": "mood",
    "Accessibility Vibe Agent": "accessibility_vibe",
    "Performance Vibe Agent": "performance_vibe",
    "Creativity Catalyst Agent": "creative_ideas",
    "Design Iteration Agent": "design_iterations",
}

# Agent -> default workspace-relative path for artifact write
ARTIFACT_PATHS: Dict[str, str] = {
    "Frontend Generation": "src/App.jsx",
    "Backend Generation": "server.py",
    "Database Agent": "schema.sql",
    "API Integration": "api/client.js",
    "Test Generation": "tests/test_basic.py",
    "Documentation Agent": "README.md",
    "Error Recovery": "docs/runbook.md",
    "PDF Export": "docs/summary.pdf",
    "Excel Export": "docs/tracking.csv",
    "Markdown Export": "docs/summary.md",
    "Layout Agent": "src/App.jsx",
    "SEO Agent": "public/robots.txt",
    "Content Agent": "content/copy.json",
    "Validation Agent": "validation/schema.json",
    "Auth Setup Agent": "auth/config.json",
    "Payment Setup Agent": "payments/config.json",
    "Monitoring Agent": "monitoring/sentry.yaml",
    "DevOps Agent": ".github/workflows/ci.yml",
    "Webhook Agent": "webhooks/handler.js",
    "Email Agent": "email/config.json",
    "Legal Compliance Agent": "docs/compliance.md",
    "Automation Agent": "cron/tasks.json",
    "GraphQL Agent": "schema.graphql",
    "WebSocket Agent": "ws/handler.js",
    "i18n Agent": "locales/en.json",
    "Caching Agent": "cache/redis.json",
    "Rate Limit Agent": "middleware/rate_limit.js",
    "Search Agent": "search/config.json",
    "Analytics Agent": "analytics/events.json",
    "API Documentation Agent": "openapi.yaml",
    "Mobile Responsive Agent": "styles/responsive.json",
    "Migration Agent": "migrations/001_init.sql",
    "Backup Agent": "scripts/backup.sh",
    "Notification Agent": "notifications/config.json",
    "Staging Agent": "staging.env",
    "A/B Test Agent": "experiments/ab.json",
    "Feature Flag Agent": "flags.json",
    "Error Boundary Agent": "components/ErrorBoundary.jsx",
    "Logging Agent": "logging/config.json",
    "Metrics Agent": "metrics/prometheus.yaml",
    "Audit Trail Agent": "audit/middleware.js",
    "Session Agent": "session/config.json",
    "OAuth Provider Agent": "auth/oauth.json",
    "2FA Agent": "auth/2fa.json",
    "Stripe Subscription Agent": "payments/stripe.json",
    "Invoice Agent": "templates/invoice.html",
    "CDN Agent": "cdn/config.json",
    "SSR Agent": "next.config.js",
    "Schema Validation Agent": "schemas/api.json",
    "Mock API Agent": "mocks/handlers.js",
    "E2E Agent": "e2e/spec.js",
    "Load Test Agent": "load/k6.js",
    "License Agent": "LICENSE",
    "Terms Agent": "docs/terms.md",
    "Privacy Policy Agent": "docs/privacy.md",
    "Cookie Consent Agent": "consent/cookies.json",
    "Multi-tenant Agent": "tenant/schema.sql",
    "RBAC Agent": "auth/roles.json",
    "SSO Agent": "auth/sso.json",
    "Audit Export Agent": "scripts/export_audit.sh",
    "Data Residency Agent": "compliance/residency.json",
    "HIPAA Agent": "docs/hipaa.md",
    "SOC2 Agent": "docs/soc2.md",
    "Penetration Test Agent": "security/pentest.md",
    "Incident Response Agent": "docs/incident_runbook.md",
    "SLA Agent": "docs/sla.md",
    "Cost Optimizer Agent": "docs/cost.md",
    "Accessibility WCAG Agent": "docs/wcag.md",
    "RTL Agent": "styles/rtl.css",
    "Dark Mode Agent": "themes/dark.json",
    "Keyboard Nav Agent": "a11y/keyboard.md",
    "Screen Reader Agent": "a11y/screenreader.md",
    "Component Library Agent": "components/manifest.json",
    "Design System Agent": "design/tokens.json",
    "Animation Agent": "animations/config.json",
    "Chart Agent": "charts/config.json",
    "Table Agent": "components/table.json",
    "Form Builder Agent": "forms/schema.json",
    "Workflow Agent": "workflows/main.json",
    "Queue Agent": "queue/config.json",
    "Video Tutorial Agent": "docs/tutorial_script.md",
    "IDE Integration Coordinator Agent": ".vscode/settings.json",
    "Multi-language Code Agent": "api_go/main.go",
    "Team Collaboration Agent": "docs/collab.md",
    "User Onboarding Agent": "onboarding/flow.json",
    "Customization Engine Agent": "customization/config.json",
    "Accessibility Agent": "docs/a11y.md",
}

# Tool runners: agent -> (state_key to write result, optional command override)
# If no command, we use result from run_real_post_step (Security Checker, UX Auditor, Performance Analyzer, Test Executor)
TOOL_RUNNER_STATE_KEYS: Dict[str, str] = {
    "Test Executor": "test_results",
    "Security Checker": "security_report",
    "UX Auditor": "ux_report",
    "Performance Analyzer": "performance_report",
    "Code Review Agent": "code_review_report",
    "Bundle Analyzer Agent": "bundle_report",
    "Lighthouse Agent": "lighthouse_report",
    "Dependency Audit Agent": "dependency_audit",
}

# Agents that already run real tools in run_real_post_step (we only write their result to state)
POST_STEP_AGENTS = frozenset({"Test Executor", "Security Checker", "UX Auditor", "Performance Analyzer"})

# Real tool agents (File, Browser, API, Database, Deployment) - we only append to tool_log
REAL_TOOL_AGENTS = frozenset({
    "Browser Tool Agent", "File Tool Agent", "API Tool Agent", "Database Tool Agent", "Deployment Tool Agent",
})


def _extract_code_or_text(content: Any) -> str:
    if content is None:
        return ""
    s = (content if isinstance(content, str) else str(content)).strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return s


def _parse_json_safe(text: str) -> Optional[Dict]:
    try:
        # Strip markdown code block if present
        t = text.strip()
        if t.startswith("```"):
            t = re.sub(r"^```\w*\n?", "", t)
            t = re.sub(r"\n?```\s*$", "", t)
        return json.loads(t)
    except Exception:
        return None


def run_agent_real_behavior(
    agent_name: str,
    project_id: str,
    result: Dict[str, Any],
    previous_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    """
    Run the real behavior for this agent: state write, artifact write, or tool run result to state.
    Call after each agent run (after run_real_post_step for LLM agents, after run_real_agent for tool agents).
    """
    previous_outputs = previous_outputs or {}
    out = result.get("output") or result.get("result") or result.get("code") or ""
    if isinstance(out, dict):
        out = json.dumps(out)
    out_str = (out if isinstance(out, str) else str(out)).strip()

    # 1) State writers: parse if JSON-ish, else store as text/list
    if agent_name in STATE_WRITERS:
        key = STATE_WRITERS[agent_name]
        value = out_str
        if key in ("plan", "feedback_log", "design_iterations"):
            value = [line.strip() for line in out_str.split("\n") if line.strip()] if out_str else []
        elif key in ("requirements", "stack", "design_spec", "brand_spec", "vibe_spec", "voice_requirements",
                     "aesthetic_report", "team_preferences", "mood", "accessibility_vibe", "performance_vibe", "creative_ideas"):
            parsed = _parse_json_safe(out_str)
            value = parsed if parsed is not None else {"raw": out_str[:10000]}
        elif key == "memory_summary":
            value = out_str[:5000]
        try:
            update_state(project_id, {key: value})
        except Exception as e:
            logger.warning("state write %s: %s", agent_name, e)
        return

    # 2) Tool runners that already ran in run_real_post_step: write result to state
    if agent_name in TOOL_RUNNER_STATE_KEYS and agent_name in POST_STEP_AGENTS:
        state_key = TOOL_RUNNER_STATE_KEYS[agent_name]
        try:
            if state_key == "test_results":
                update_state(project_id, {"test_results": {"output": out_str[:15000], "raw": result}})
            else:
                update_state(project_id, {state_key: out_str[:15000]})
        except Exception as e:
            logger.warning("tool state write %s: %s", agent_name, e)
        return

    # 3) Tool runners that need execute_tool run (Code Review, Bundle Analyzer, Lighthouse, Dependency Audit)
    if agent_name in TOOL_RUNNER_STATE_KEYS and agent_name not in POST_STEP_AGENTS:
        state_key = TOOL_RUNNER_STATE_KEYS[agent_name]
        cmd = None
        if agent_name == "Code Review Agent":
            cmd = ["python", "-m", "bandit", "-r", ".", "-f", "txt", "-ll"]
        elif agent_name == "Bundle Analyzer Agent":
            cmd = ["npx", "source-map-explorer", "dist/*.js"]
        elif agent_name == "Lighthouse Agent":
            cmd = ["npx", "lighthouse", "http://localhost:3000", "--output=json", "--chrome-flags=--headless"]
        elif agent_name == "Dependency Audit Agent":
            cmd = ["npm", "audit"]
        if cmd:
            tr = execute_tool(project_id, "run", {"command": cmd, "timeout": 90})
            report = (tr.get("output") or tr.get("error") or "")[:15000]
            try:
                update_state(project_id, {state_key: report})
            except Exception as e:
                logger.warning("tool run state %s: %s", agent_name, e)
        return

    # 4) Artifact writers: write content to workspace file
    if agent_name in ARTIFACT_PATHS:
        path = ARTIFACT_PATHS[agent_name]
        content = _extract_code_or_text(out_str)
        if not content and agent_name in ("PDF Export", "Excel Export"):
            content = out_str
        if content:
            try:
                execute_tool(project_id, "file", {"action": "write", "path": path, "content": content})
            except Exception as e:
                logger.warning("artifact write %s: %s", agent_name, e)
        return

    # 5) Image/Video/Scraping: write to state for downstream use
    if agent_name == "Image Generation":
        try:
            parsed = _parse_json_safe(out_str)
            if parsed:
                update_state(project_id, {"images": parsed})
        except Exception as e:
            logger.warning("image state: %s", e)
        return
    if agent_name == "Video Generation":
        try:
            parsed = _parse_json_safe(out_str)
            if parsed:
                update_state(project_id, {"videos": parsed})
        except Exception as e:
            logger.warning("video state: %s", e)
        return
    if agent_name == "Scraping Agent":
        urls = []
        for line in out_str.split("\n"):
            line = line.strip()
            if line and (line.startswith("http://") or line.startswith("https://")):
                urls.append(line)
        if urls:
            try:
                state = load_state(project_id)
                state["scrape_urls"] = state.get("scrape_urls", []) + urls
                update_state(project_id, {"scrape_urls": state["scrape_urls"]})
            except Exception as e:
                logger.warning("scrape_urls state: %s", e)
        return

    # 6) Real tool agents: append to tool_log
    if agent_name in REAL_TOOL_AGENTS:
        try:
            state = load_state(project_id)
            log = state.get("tool_log", [])
            log.append({"agent": agent_name, "output_preview": out_str[:500]})
            update_state(project_id, {"tool_log": log[-100:]})
        except Exception as e:
            logger.warning("tool_log: %s", e)
