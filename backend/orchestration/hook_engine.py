"""
Hook Engine — event-driven automations that fire at lifecycle points.

Hooks fire at:
  - on_prompt_submit     : before a job is planned
  - before_tool_call     : before any agent executes
  - after_tool_call      : after any agent completes
  - on_failure           : when a step fails
  - before_compaction    : before context is trimmed
  - on_run_complete      : when job finishes (success or fail)

Each hook can:
  - enrich the context
  - enforce guardrails
  - trigger automations
  - capture patterns for skill memory
  - update project brain
"""
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Hook registry ──────────────────────────────────────────────────────────────
_hooks: Dict[str, List[Callable]] = {
    "on_prompt_submit": [],
    "before_tool_call": [],
    "after_tool_call": [],
    "on_failure": [],
    "before_compaction": [],
    "on_run_complete": [],
}


def register_hook(event: str, fn: Callable) -> None:
    if event in _hooks:
        _hooks[event].append(fn)


async def fire(event: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Fire all hooks for an event. Each hook can mutate and return context."""
    for fn in _hooks.get(event, []):
        try:
            result = await fn(context) if callable(fn) else None
            if isinstance(result, dict):
                context.update(result)
        except Exception as e:
            logger.warning("hook_engine: hook %s on %s failed: %s", fn.__name__ if hasattr(fn, '__name__') else fn, event, e)
    return context


# ── Built-in hooks ─────────────────────────────────────────────────────────────

async def _hook_load_project_brain(context: Dict) -> Dict:
    """on_prompt_submit: inject project brain memory into goal."""
    job_id = context.get("job_id")
    user_id = context.get("user_id")
    if not user_id:
        return context
    try:
        from services.project_brain_service import load_project_brain
        brain = await load_project_brain(user_id, context.get("project_id"))
        if brain:
            context["brain_context"] = brain
            existing_goal = context.get("goal", "")
            if brain.get("summary") and "LEARNED SKILLS" not in existing_goal:
                context["goal"] = f"{existing_goal}\n\nPROJECT MEMORY:\n{brain['summary']}"
    except Exception as e:
        logger.debug("hook: load_project_brain skipped: %s", e)
    return context


async def _hook_security_preflight(context: Dict) -> Dict:
    """before_tool_call: run lightweight security check on agent output."""
    output = context.get("output", "")
    if not output or len(output) < 50:
        return context
    # Quick secret scan
    import re
    secret_patterns = [
        r'sk-[a-zA-Z0-9]{32,}',           # OpenAI keys
        r'ghp_[a-zA-Z0-9]{36}',            # GitHub tokens
        r'AIza[0-9A-Za-z\-_]{35}',         # Google API keys
        r'(?i)password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
        r'(?i)secret\s*=\s*["\'][^"\']{8,}["\']', # Hardcoded secrets
    ]
    for pattern in secret_patterns:
        if re.search(pattern, output):
            context["security_warning"] = f"Potential secret detected in output. Pattern: {pattern[:40]}"
            logger.warning("hook: secret pattern detected in agent output for job %s", context.get("job_id"))
            break
    return context


async def _hook_capture_pattern(context: Dict) -> Dict:
    """after_tool_call: capture successful patterns for skill memory."""
    if context.get("status") != "completed":
        return context
    agent_name = context.get("agent_name", "")
    output = context.get("output", "")
    if not output or len(output) < 100:
        return context
    # Store in context for Skill Extractor to pick up later
    patterns = context.get("_captured_patterns", [])
    patterns.append({
        "agent": agent_name,
        "output_length": len(output),
        "phase": context.get("phase", ""),
    })
    context["_captured_patterns"] = patterns
    return context


async def _hook_auto_recovery(context: Dict) -> Dict:
    """on_failure: log failure for brain repair to pick up."""
    step_key = context.get("step_key", "")
    error = context.get("error_message", "")
    job_id = context.get("job_id", "")
    if step_key and error and job_id:
        logger.info("hook: auto_recovery triggered for step %s: %s", step_key, error[:100])
        context["recovery_attempted"] = True
    return context


async def _hook_update_project_brain(context: Dict) -> Dict:
    """on_run_complete: save build outcome to project brain."""
    if context.get("status") != "completed":
        return context
    try:
        from services.project_brain_service import update_project_brain
        await update_project_brain(
            user_id=context.get("user_id", ""),
            project_id=context.get("project_id"),
            job_id=context.get("job_id", ""),
            goal=context.get("goal", ""),
            stack=context.get("stack", ""),
            quality_score=context.get("quality_score", 0),
        )
    except Exception as e:
        logger.debug("hook: update_project_brain skipped: %s", e)
    return context


# ── Register built-in hooks ────────────────────────────────────────────────────
register_hook("on_prompt_submit", _hook_load_project_brain)
register_hook("before_tool_call", _hook_security_preflight)
register_hook("after_tool_call", _hook_capture_pattern)
register_hook("on_failure", _hook_auto_recovery)
register_hook("on_run_complete", _hook_update_project_brain)
