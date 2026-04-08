"""
10/10 Roadmap: Agent DAG, output chaining, error recovery, timeouts.
Run agents in parallel phases with context from previous agents; retry and fallback on failure.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid

from agents.code_repair_agent import coerce_text_output

logger = logging.getLogger(__name__)

# --- DAG: phases run in order; within each phase agents run in parallel ---
# Each tuple: (display_name, system_prompt_suffix for context)
ORCHESTRATION_AGENTS_CONFIG = {
    "Planner": ("Planner", "Decompose the request into 3-7 executable tasks. Numbered list only."),
    "Requirements Clarifier": ("Requirements Clarifier", "Ask 2-4 clarifying questions. One per line."),
    "Stack Selector": ("Stack Selector", "Recommend tech stack (frontend, backend, DB). Short bullets."),
    "Frontend Generation": ("Frontend Generation", "Output only complete React/JSX code. No markdown."),
    "Backend Generation": ("Backend Generation", "Output only backend code (e.g. FastAPI/Express). No markdown."),
    "Database Agent": ("Database Agent", "Output schema and migration steps. Plain text or SQL."),
    "API Integration": ("API Integration", "Output only code that calls an API. No markdown."),
    "Test Generation": ("Test Generation", "Output only test code. No markdown."),
    "Image Generation": ("Image Generation", "Output a detailed image prompt (style, composition, colors) for the request."),
    "Security Checker": ("Security Checker", "List 3-5 security checklist items with PASS/FAIL."),
    "Test Executor": ("Test Executor", "Give the test command and one line of what to check."),
    "UX Auditor": ("UX Auditor", "List 2-4 accessibility/UX checklist items with PASS/FAIL."),
    "Performance Analyzer": ("Performance Analyzer", "List 2-4 performance tips for the project."),
    "Deployment Agent": ("Deployment Agent", "Give step-by-step deploy instructions."),
    "Error Recovery": ("Error Recovery", "List 2-3 common failure points and how to recover."),
    "Memory Agent": ("Memory Agent", "Summarize the project in 2-3 lines for reuse."),
    "PDF Export": ("PDF Export", "Describe what a one-page project summary PDF would include."),
    "Excel Export": ("Excel Export", "Suggest 3-5 columns for a project tracking spreadsheet."),
    "Markdown Export": ("Markdown Export", "Output a short project summary in Markdown (headings, bullets)."),
    "Scraping Agent": ("Scraping Agent", "Suggest 2-3 data sources or URLs to scrape for this project."),
    "Automation Agent": ("Automation Agent", "Suggest 2-3 automated tasks or cron jobs for this project."),
    "Design Agent": ("Design Agent", "Output JSON: hero, feature_1, feature_2 with position, aspect, role. No markdown."),
    "Layout Agent": ("Layout Agent", "Inject image placeholders into frontend. Output updated React/JSX."),
    "SEO Agent": ("SEO Agent", "Meta tags, OG, schema, sitemap, robots.txt."),
    "Content Agent": ("Content Agent", "Landing copy: hero, features, CTA."),
    "Brand Agent": ("Brand Agent", "Colors, fonts, tone. JSON."),
    "Documentation Agent": ("Documentation Agent", "README: setup, env, run, deploy."),
    "Validation Agent": ("Validation Agent", "3-5 validation rules, Zod/Yup schemas."),
    "Auth Setup Agent": ("Auth Setup Agent", "JWT/OAuth flow, protected routes."),
    "Payment Setup Agent": ("Payment Setup Agent", "Stripe checkout, webhooks."),
    "Monitoring Agent": ("Monitoring Agent", "Sentry, analytics setup."),
    "Accessibility Agent": ("Accessibility Agent", "3-5 a11y improvements."),
    "DevOps Agent": ("DevOps Agent", "CI/CD, Dockerfile."),
    "Webhook Agent": ("Webhook Agent", "Webhook endpoint design."),
    "Email Agent": ("Email Agent", "Transactional email setup."),
    "Legal Compliance Agent": ("Legal Compliance Agent", "GDPR/CCPA hints."),
}

# Parallel phases (agents in same list run in parallel; order respects DAG deps)
PARALLEL_PHASES: List[List[str]] = [
    ["Planner"],
    ["Requirements Clarifier", "Stack Selector", "Content Agent", "Legal Compliance Agent"],
    ["Frontend Generation", "Backend Generation", "Database Agent", "Design Agent", "SEO Agent", "Brand Agent", "Auth Setup Agent", "Payment Setup Agent", "Email Agent"],
    ["API Integration", "Test Generation", "Image Generation", "Scraping Agent", "Automation Agent"],
    ["Security Checker", "Test Executor", "UX Auditor", "Performance Analyzer", "Layout Agent", "Validation Agent", "Accessibility Agent", "Webhook Agent"],
    ["Deployment Agent", "Error Recovery", "Memory Agent"],
    ["PDF Export", "Excel Export", "Markdown Export", "Documentation Agent", "Monitoring Agent", "DevOps Agent"],
]

# Criticality: critical = stop build on failure; high = use fallback; low/medium = skip
AGENT_CRITICALITY: Dict[str, str] = {
    "Planner": "critical",
    "Requirements Clarifier": "high",
    "Stack Selector": "critical",
    "Frontend Generation": "high",
    "Backend Generation": "high",
    "Database Agent": "high",
    "API Integration": "medium",
    "Test Generation": "medium",
    "Image Generation": "low",
    "Security Checker": "medium",
    "Test Executor": "medium",
    "UX Auditor": "low",
    "Performance Analyzer": "low",
    "Deployment Agent": "medium",
    "Error Recovery": "low",
    "Memory Agent": "low",
    "PDF Export": "low",
    "Excel Export": "low",
    "Scraping Agent": "low",
    "Automation Agent": "low",
    "Design Agent": "low",
    "Layout Agent": "low",
    "SEO Agent": "low",
    "Content Agent": "low",
    "Brand Agent": "low",
    "Documentation Agent": "low",
    "Validation Agent": "low",
    "Auth Setup Agent": "medium",
    "Payment Setup Agent": "medium",
    "Monitoring Agent": "low",
    "Accessibility Agent": "low",
    "DevOps Agent": "low",
    "Webhook Agent": "low",
    "Email Agent": "low",
    "Legal Compliance Agent": "low",
}

AGENT_TIMEOUTS: Dict[str, int] = {
    "Planner": 120,
    "Frontend Generation": 180,
    "Backend Generation": 180,
    "Security Checker": 90,
    "Test Generation": 120,
    "Performance Analyzer": 60,
}
DEFAULT_TIMEOUT = 120

MAX_CONTEXT_CHARS = 2000  # truncate previous outputs to avoid token blow-up


class AgentError(Exception):
    def __init__(self, agent_name: str, reason: str, severity: str = "high"):
        self.agent_name = agent_name
        self.reason = reason
        self.severity = severity


def _generate_fallback(agent_name: str) -> str:
    fallbacks = {
        "Frontend Generation": "// Generated frontend (fallback)\nconst App = () => <div>Generated app</div>;\nexport default App;",
        "Backend Generation": "# Generated backend (fallback)\nfrom fastapi import FastAPI\napp = FastAPI()",
        "Test Generation": "# Test generation failed, skipped",
        "Performance Analyzer": "// No optimization performed",
    }
    return fallbacks.get(agent_name, f"// {agent_name} generated no output (fallback)")


def _build_context_additions(agent_name: str, previous_outputs: Dict[str, Any], project_prompt: str) -> str:
    """Build context string from previous agent outputs for prompt enhancement."""
    parts = []
    if "Planner" in previous_outputs and previous_outputs["Planner"].get("output"):
        out = coerce_text_output(previous_outputs["Planner"]["output"] or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Previous step (Planning):\n{out}\n\nUse this plan to inform your decisions.")
    if "Stack Selector" in previous_outputs and previous_outputs["Stack Selector"].get("output"):
        out = coerce_text_output(previous_outputs["Stack Selector"]["output"] or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Selected Tech Stack:\n{out}\n\nGenerate code using this stack.")
    if "Frontend Generation" in previous_outputs and agent_name in ("Security Checker", "UX Auditor", "Performance Analyzer", "Layout Agent", "Validation Agent", "Accessibility Agent"):
        out = coerce_text_output(previous_outputs["Frontend Generation"].get("output") or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Generated Frontend (excerpt):\n{out}")
    if "Backend Generation" in previous_outputs and agent_name in ("Security Checker", "Test Generation", "Validation Agent", "Webhook Agent"):
        out = coerce_text_output(previous_outputs["Backend Generation"].get("output") or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Generated Backend (excerpt):\n{out}")
    if "Design Agent" in previous_outputs and agent_name in ("Image Generation", "Layout Agent"):
        out = coerce_text_output(previous_outputs["Design Agent"].get("output") or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Design placement spec:\n{out}")
    if "Image Generation" in previous_outputs and agent_name == "Layout Agent":
        out = coerce_text_output(previous_outputs["Image Generation"].get("output") or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Image prompts:\n{out}")
    if "Deployment Agent" in previous_outputs and agent_name in ("Documentation Agent", "Monitoring Agent", "DevOps Agent"):
        out = coerce_text_output(previous_outputs["Deployment Agent"].get("output") or "", limit=MAX_CONTEXT_CHARS)
        parts.append(f"Deployment plan:\n{out}")
    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)


async def run_orchestration_with_dag(project_id: str, user_id: str) -> Dict[str, Any]:
    """
    Run all agents in parallel phases with output chaining, retries, and timeouts.
    Uses server's db, get_workspace_api_keys, _effective_api_keys, _get_model_chain, _call_llm_with_fallback (late import).
    """
    from server import (
        db,
        get_workspace_api_keys,
        _effective_api_keys,
        _get_model_chain,
        _call_llm_with_fallback,
    )

    project = await db.projects.find_one({"id": project_id})
    if not project:
        return {}
    req = project.get("requirements") or {}
    prompt = req.get("prompt") or req.get("description") or project.get("description") or "Build a web application"
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)

    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)

    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"status": "running", "current_phase": 0, "progress_percent": 0}},
    )
    results: Dict[str, Any] = {}
    total_used = 0
    phase_timings: Dict[str, Any] = {}
    build_failed = False

    for phase_num, agents_in_phase in enumerate(PARALLEL_PHASES):
        if build_failed:
            break
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"current_phase": phase_num, "current_agent": ",".join(agents_in_phase)}},
        )
        start = asyncio.get_event_loop().time()
        context = _build_context_additions("", results, prompt)  # we pass results below per-agent
        tasks = [
            _run_single_agent_with_timeout(
                project_id,
                user_id,
                agent_name,
                prompt,
                results,
                db,
                _call_llm_with_fallback,
                model_chain,
                effective,
            )
            for agent_name in agents_in_phase
        ]
        phase_results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = asyncio.get_event_loop().time() - start
        phase_timings[f"phase_{phase_num}"] = {"agents": agents_in_phase, "elapsed_seconds": round(elapsed, 2)}

        for agent_name, r in zip(agents_in_phase, phase_results):
            if isinstance(r, Exception):
                out = await _handle_agent_failure(
                    project_id,
                    agent_name,
                    AgentError(agent_name, str(r), "high"),
                    AGENT_CRITICALITY.get(agent_name, "medium"),
                    db,
                )
                results[agent_name] = out
                if out.get("recoverable") is False:
                    build_failed = True
                continue
            results[agent_name] = r
            total_used += r.get("tokens_used", 0)
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {"$set": {"status": "completed", "progress": 100, "tokens_used": r.get("tokens_used", 0)}},
                upsert=True,
            )
            await db.project_logs.insert_one({
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "agent": agent_name,
                "message": f"{agent_name} completed. Used {r.get('tokens_used', 0):,} tokens.",
                "level": "success",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        progress_pct = int((phase_num + 1) / len(PARALLEL_PHASES) * 100)
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"progress_percent": progress_pct, "tokens_used": total_used, "execution_metrics": {"phase_timings": phase_timings}}},
        )

    status = "failed" if build_failed else "completed"
    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "status": status,
                "tokens_used": total_used,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "live_url": None,
                "execution_metrics": {
                    "phase_timings": phase_timings,
                    "total_seconds": sum(t.get("elapsed_seconds", 0) for t in phase_timings.values()),
                },
            }
        },
    )
    project = await db.projects.find_one({"id": project_id})
    if project and not build_failed:
        refund = project.get("tokens_allocated", 0) - total_used
        if refund > 0:
            await db.users.update_one({"id": user_id}, {"$inc": {"token_balance": refund}})
            await db.token_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tokens": refund,
                "type": "refund",
                "description": f"Unused tokens from project {project_id[:8]}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    return results


async def _run_single_agent_with_timeout(
    project_id: str,
    user_id: str,
    agent_name: str,
    prompt: str,
    previous_outputs: Dict[str, Any],
    db,
    call_llm,
    model_chain: list,
    effective: dict,
) -> Dict[str, Any]:
    timeout_s = AGENT_TIMEOUTS.get(agent_name, DEFAULT_TIMEOUT)
    try:
        return await asyncio.wait_for(
            _run_single_agent_with_retry(
                project_id,
                user_id,
                agent_name,
                prompt,
                previous_outputs,
                db,
                call_llm,
                model_chain,
                effective,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        return await _handle_agent_failure(
            project_id,
            agent_name,
            AgentError(agent_name, f"Timeout after {timeout_s}s", "high"),
            AGENT_CRITICALITY.get(agent_name, "medium"),
            db,
        )


async def _run_single_agent_with_retry(
    project_id: str,
    user_id: str,
    agent_name: str,
    prompt: str,
    previous_outputs: Dict[str, Any],
    db,
    call_llm,
    model_chain: list,
    effective: dict,
    max_retries: int = 3,
) -> Dict[str, Any]:
    last_error = None
    for attempt in range(max_retries):
        try:
            result = await _run_single_agent_with_context(
                project_id,
                agent_name,
                prompt,
                previous_outputs,
                db,
                call_llm,
                model_chain,
                effective,
            )
            if not result.get("output") and not result.get("code"):
                raise AgentError(agent_name, "Empty output", "medium")
            return result
        except AgentError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return await _handle_agent_failure(project_id, agent_name, e, AGENT_CRITICALITY.get(agent_name, "medium"), db)
        except Exception as e:
            last_error = AgentError(agent_name, str(e), "high")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return await _handle_agent_failure(
                project_id,
                agent_name,
                last_error,
                AGENT_CRITICALITY.get(agent_name, "medium"),
                db,
            )
    return await _handle_agent_failure(
        project_id,
        agent_name,
        last_error or AgentError(agent_name, "Unknown", "high"),
        AGENT_CRITICALITY.get(agent_name, "medium"),
        db,
    )


async def _run_single_agent_with_context(
    project_id: str,
    agent_name: str,
    prompt: str,
    previous_outputs: Dict[str, Any],
    db,
    call_llm,
    model_chain: list,
    effective: dict,
) -> Dict[str, Any]:
    if agent_name not in ORCHESTRATION_AGENTS_CONFIG:
        return {"agent": agent_name, "status": "skipped", "output": "", "tokens_used": 0}
    _, system_suffix = ORCHESTRATION_AGENTS_CONFIG[agent_name]
    system_msg = f"You are {system_suffix}"
    context_add = _build_context_additions(agent_name, previous_outputs, prompt)
    if context_add:
        system_msg = system_msg + "\n\n" + context_add
    user_msg = prompt

    await db.agent_status.update_one(
        {"project_id": project_id, "agent_name": agent_name},
        {"$set": {"project_id": project_id, "agent_name": agent_name, "status": "running", "progress": 0, "tokens_used": 0}},
        upsert=True,
    )
    await db.project_logs.insert_one({
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "agent": agent_name,
        "message": f"Starting {agent_name}...",
        "level": "info",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    if not effective.get("openai") and not effective.get("anthropic"):
        return {
            "agent": agent_name,
            "status": "completed",
            "output": _generate_fallback(agent_name),
            "tokens_used": 0,
        }

    response, _ = await call_llm(
        message=user_msg,
        system_message=system_msg,
        session_id=f"orch_{project_id}",
        model_chain=model_chain,
        api_keys=effective,
    )
    tokens_used = max(100, min(200000, (len(prompt) + len(response or "")) * 2))
    output = (response or "").strip()
    code = output.removeprefix("```").removesuffix("```").strip() if output else ""
    if code.startswith("python"):
        code = code[6:].strip()
    return {
        "agent": agent_name,
        "status": "completed",
        "output": output,
        "code": code if agent_name in ("Frontend Generation", "Backend Generation", "API Integration", "Test Generation") else None,
        "tokens_used": tokens_used,
    }


async def _handle_agent_failure(
    project_id: str,
    agent_name: str,
    error: AgentError,
    criticality: str,
    db,
) -> Dict[str, Any]:
    await db.project_logs.insert_one({
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "agent": agent_name,
        "message": f"{agent_name} failed: {error.reason}",
        "level": "error",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    if criticality == "critical":
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {
            "agent": agent_name,
            "status": "failed",
            "output": "",
            "reason": error.reason,
            "recoverable": False,
            "tokens_used": 0,
        }
    if criticality == "high":
        fallback = _generate_fallback(agent_name)
        return {
            "agent": agent_name,
            "status": "failed_with_fallback",
            "output": fallback,
            "fallback_output": fallback,
            "reason": error.reason,
            "recoverable": True,
            "tokens_used": 0,
        }
    return {
        "agent": agent_name,
        "status": "skipped",
        "output": "",
        "reason": error.reason,
        "recoverable": True,
        "tokens_used": 0,
    }


def get_execution_phases() -> List[List[str]]:
    """Return phases for UI (parallel groups)."""
    return PARALLEL_PHASES
