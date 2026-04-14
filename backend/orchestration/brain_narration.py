"""
Structured coaching copy for job events and UI (brain "talks", not only logs).

Template-first for latency and cost; optional LLM hook can be added later.

NOW: Manus-style action chips, task progress cards, and conversational narration.
"""

from __future__ import annotations

from typing import Any, Dict, List

# job_id -> last phase_label we emitted progress_narrative for (avoid duplicate SSE noise)
_last_progress_phase: Dict[str, str] = {}

# Map agent names to human-readable descriptions for user-facing narration
AGENT_TO_DESCRIPTION = {
    # Core planning
    "planner_agent": "Creating detailed build plan",
    "requirements_clarifier": "Understanding your requirements",
    "clarification_agent": "Clarifying project scope",
    "stack_selector_agent": "Selecting optimal technology stack",
    "stack_selector": "Selecting optimal technology stack",
    
    # Code generation
    "frontend_agent": "Generating React components",
    "frontend_generation": "Generating React components",
    "backend_agent": "Setting up backend services",
    "backend_generation": "Setting up backend services",
    "builder_agent": "Building application structure",
    
    # Database & Infrastructure
    "database_agent": "Designing database schema",
    "database_architect_agent": "Architecting database structure",
    "deployment_agent": "Setting up deployment pipeline",
    "infrastructure_agent": "Configuring infrastructure",
    
    # Design & UI
    "design_agent": "Applying design system",
    "design_system_agent": "Building design system",
    "brand_agent": "Finalizing branding",
    "dark_mode_agent": "Adding dark mode support",
    "animation_agent": "Creating animations",
    "responsive_breakpoints_agent": "Optimizing for all devices",
    "typography_system_agent": "Setting up typography",
    
    # Quality & Testing
    "ux_auditor": "Auditing UX quality",
    "preview_validator_agent": "Validating preview output",
    "code_analysis_agent": "Analyzing code quality",
    "code_repair_agent": "Fixing code issues",
    "security_agent": "Implementing security measures",
    
    # Content & Documentation
    "documentation_agent": "Generating documentation",
    "legal_compliance": "Ensuring legal compliance",
    "image_generator": "Generating images and assets",
    
    # Fallback
    "default": "Processing step",
}

def get_agent_description(agent_key: str) -> str:
    """Get human-readable description for an agent, with fallback."""
    # Direct lookup
    if agent_key in AGENT_TO_DESCRIPTION:
        return AGENT_TO_DESCRIPTION[agent_key]
    
    # Try removing common suffixes
    for suffix in ["_agent", "Agent"]:
        clean_key = agent_key.replace(suffix, "")
        if clean_key in AGENT_TO_DESCRIPTION:
            return AGENT_TO_DESCRIPTION[clean_key]
    
    # Fallback: convert snake_case to title case
    readable = agent_key.replace("_", " ").title()
    return readable if readable else AGENT_TO_DESCRIPTION["default"]


def build_execution_think_payload(
    job: Dict[str, Any], steps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Pre-execution THINK: user-facing intent + plan, no chain-of-thought, no agent names.
    Emitted once before the runner begins stepping the DAG.
    """
    phase = (job.get("current_phase") or "").strip().lower()
    total = len(steps or [])
    if total == 0:
        return {
            "kind": "execution_think",
            "headline": "Getting organized",
            "summary": "I'm lining up this run before work starts; if steps are missing, we'll surface that next.",
            "next_steps": [],
        }

    completed = sum(1 for s in steps if s.get("status") == "completed")
    pending = sum(1 for s in steps if s.get("status") == "pending")

    if phase == "resuming_after_failure":
        headline = "Continuing your run"
        summary = (
            "I'm picking up from where things stopped: addressing what blocked checks first, "
            "then moving the rest of your plan forward on this same run."
        )
    elif completed == 0 and pending == total:
        headline = "Starting your build"
        summary = (
            "I've reviewed your approved plan and I'm beginning execution: foundation and dependencies first, "
            "then features and quality checks in order."
        )
    elif completed > 0:
        headline = "Continuing your build"
        summary = (
            "I'm resuming this run, building on what's already done and finishing what's left in the plan."
        )
    else:
        headline = "Starting your build"
        summary = (
            "I'm moving this plan forward step by step, keeping progress visible in Preview and Proof."
        )

    return {
        "kind": "execution_think",
        "headline": headline[:400],
        "summary": summary[:900],
        "next_steps": [
            "You'll see updates here first; Preview and Proof fill in as outputs land.",
        ],
    }


async def emit_execution_think_guidance(
    job_id: str,
    job: Dict[str, Any],
    steps: List[Dict[str, Any]],
) -> None:
    payload = build_execution_think_payload(job, steps)
    from .event_bus import publish
    from .runtime_state import append_job_event

    await append_job_event(job_id, "brain_guidance", payload)
    await publish(job_id, "brain_guidance", payload)


def build_failure_guidance(
    step_key: str,
    issues: List[str],
    *,
    failure_reason: str = "",
) -> Dict[str, Any]:
    """Return summary + next_steps for brain_guidance SSE / job_events."""
    clean_issues = [str(i).strip() for i in (issues or []) if str(i).strip()]
    blob = " ".join(clean_issues).lower()
    fr = (failure_reason or "").lower()

    summary_parts: List[str] = []
    if step_key:
        summary_parts.append(f"Step `{step_key}` did not pass verification.")
    if clean_issues:
        summary_parts.append(clean_issues[0][:280])
    elif fr:
        summary_parts.append(f"Reason: {failure_reason}.")
    else:
        summary_parts.append("Verification reported a problem; see issues for detail.")

    next_steps: List[str] = []

    if "prose" in blob or "preamble" in blob:
        next_steps.append(
            "Remove conversational text at the top of the affected file so the file starts with valid code."
        )
    if "esbuild" in blob or "syntax" in blob or "unexpected" in blob:
        next_steps.append(
            "Open the file named in the error, fix the syntax at the indicated location, then retry the step or resume the job."
        )
    if "npx" in blob or "esbuild unavailable" in blob:
        next_steps.append(
            "Confirm Node.js and npx are available on the host running the API (Docker image should include them)."
        )
    if "timeout" in blob:
        next_steps.append(
            "A file may be very large or the host is slow — simplify the file or raise verifier timeouts if appropriate."
        )
    if "python" in blob or "py_compile" in blob:
        next_steps.append(
            "Fix the Python syntax in the listed module, or remove invalid characters copied from prose."
        )
    if "tenant" in blob or "set_config" in blob or "app.tenant_id" in blob:
        next_steps.append(
            "Align generated backend with RLS / tenant GUC expectations, or adjust the security verification gate."
        )

    if not next_steps:
        next_steps.append(
            "Use the Failure tab for raw errors, open the referenced file in the code pane, fix, then Resume build or Retry step."
        )
        next_steps.append(
            "Optionally add a short note in chat and choose Resume — your message is stored for steering context."
        )

    headline = summary_parts[0] if summary_parts else "Build needs attention."

    return {
        "headline": headline[:400],
        "summary": " ".join(summary_parts)[:900],
        "next_steps": next_steps[:8],
        "step_key": step_key,
        "issue_count": len(clean_issues),
    }


def build_resume_coach_message(user_message: str) -> Dict[str, Any]:
    """Light narration when user steers a failed job."""
    msg = (user_message or "").strip()
    return {
        "headline": "Continuing your build",
        "summary": (
            f"Recorded your note ({len(msg)} chars). Failed and blocked steps were re-queued; "
            "the runner will try again with the current workspace."
        ),
        "next_steps": [
            "Watch the timeline for the retried verification or agent steps.",
            "If the same step fails, open the file from the error and edit locally, then Resume again.",
        ],
    }


def build_steering_guidance(
    user_message: str,
    *,
    resume: bool,
    job_status: str,
) -> Dict[str, Any]:
    """
    Coach copy for POST /jobs/{id}/steer.
    When resume=True, use the post-failure resume coach.
    When resume=False, avoid implying a retry was scheduled (job may still be running).
    """
    msg = (user_message or "").strip()
    if resume:
        return build_resume_coach_message(msg)
    st = (job_status or "").strip().lower()
    if st in ("running", "queued"):
        return {
            "headline": "Message recorded",
            "summary": (
                "Your note is saved on this job while the current run continues. "
                "Agents can use it as extra context."
            ),
            "next_steps": [
                "Watch the timeline and Preview for live progress.",
                "If a step fails, open Failure for details, fix if needed, then Resume.",
            ],
        }
    if st == "failed":
        return {
            "headline": "Note recorded",
            "summary": (
                "Your steering message is saved. Resume the build when you want the runner to retry with this context."
            ),
            "next_steps": [
                "Review the Failure tab, edit files if needed, then tap Resume.",
                "Or send another note and use Steer with resume when ready.",
            ],
        }
    return {
        "headline": "Note recorded",
        "summary": f"Saved your note ({len(msg)} characters) on this job.",
        "next_steps": ["Use workspace controls to continue when you are ready."],
    }


def clear_progress_narrative_cache(job_id: str) -> None:
    """Drop throttle state when a job ends so IDs can be reused safely in tests."""
    _last_progress_phase.pop(job_id, None)


def build_phase_progress_narrative(
    steps: List[Dict[str, Any]],
    *,
    phase_label: str,
    job_goal: str = "",
) -> Dict[str, Any]:
    """
    Plain-language pulse for the middle pane while a build runs (grounded in step counts).
    """
    _ = job_goal  # reserved for future context-aware narration
    total = len(steps or [])
    completed = sum(1 for s in steps or [] if s.get("status") == "completed")
    running = [
        s
        for s in (steps or [])
        if s.get("status") in ("running", "verifying", "in_progress")
    ]
    failed = [s for s in (steps or []) if s.get("status") == "failed"]
    blocked = [s for s in (steps or []) if s.get("status") == "blocked"]

    def _human_step(sk: str) -> str:
        s = (sk or "").strip()
        if s.startswith("agents."):
            tail = s.split(".", 1)[-1].replace("_", " ").strip()
            return (tail[:1].upper() + tail[1:]) if tail else "Agent work"
        if s.startswith("verification."):
            return f"Verifying {s.split('.', 1)[-1].replace('_', ' ')}"
        return s.replace("_", " ").replace(".", " — ")[:120] or "In progress"

    cur = ""
    if running:
        cur = _human_step(str(running[0].get("step_key") or ""))
    elif phase_label and phase_label not in ("running", ""):
        if phase_label.startswith("parallel:"):
            n = phase_label.replace("parallel:", "").strip() or "?"
            cur = f"Running {n} parallel tracks"
        else:
            cur = phase_label

    summary_parts = [f"Progress: {completed}/{max(total, 1)} steps completed."]
    if cur:
        summary_parts.append(f"Current focus: {cur}.")
    headline = "Build in progress"
    if failed or blocked:
        headline = "Build needs attention"
        summary_parts.append(
            "Some steps failed or are blocked — see Timeline (detail) and Failure for raw errors."
        )

    next_steps = [
        "Preview updates when the bundle verifies; Code shows files as they land.",
    ]
    if failed or blocked:
        next_steps.insert(
            0,
            "Use the composer to steer, then Resume — completed work stays in the workspace.",
        )

    return {
        "kind": "progress_narrative",
        "headline": headline[:400],
        "summary": " ".join(summary_parts)[:900],
        "next_steps": next_steps[:6],
        "phase_label": phase_label,
        "completed": completed,
        "total": total,
    }


def build_task_progress_card(steps: List[Dict[str, Any]], current_idx: int = 0) -> Dict[str, Any]:
    """
    Generate Manus-style task progress card: "1/11" format with all tasks.
    Each task is a human-readable description, not an agent name.
    """
    if not steps:
        return {"kind": "task_progress", "total": 0, "current": 0, "tasks": []}
    
    tasks = []
    for i, step in enumerate(steps):
        # Get human-readable description from agent name
        agent_key = step.get("agent_key", "").replace("agents.", "")
        description = get_agent_description(agent_key)
        
        tasks.append({
            "index": i,
            "description": description[:100],
            "status": step.get("status", "pending"),  # "pending", "running", "completed", "failed"
        })
    
    return {
        "kind": "task_progress",
        "total": len(steps),
        "current": current_idx + 1,
        "tasks": tasks,
    }


def build_action_chips(steps: List[Dict[str, Any]], current_idx: int = -1) -> List[Dict[str, Any]]:
    """
    Generate Manus-style action chips for the current step and next few steps.
    Shows what's running and what's queued.
    """
    if not steps or current_idx < 0:
        return []
    
    chips = []
    # Show current + next 2-3 steps
    for i in range(max(0, current_idx), min(len(steps), current_idx + 4)):
        step = steps[i]
        agent_key = step.get("agent_key", "").replace("agents.", "")
        description = get_agent_description(agent_key)
        
        chips.append({
            "action": description[:80],
            "status": step.get("status", "pending"),
            "icon": "file" if "create" in description.lower() else "arrow",
        })
    
    return chips


def build_current_step_indicator(step: Dict[str, Any], elapsed_seconds: int = 0, current_idx: int = 0, total: int = 1) -> Dict[str, Any]:
    """
    Generate Manus-style current step indicator with blue dot.
    Shows: step name, elapsed time, position (1/11), and thinking status.
    """
    agent_key = step.get("agent_key", "").replace("agents.", "")
    description = get_agent_description(agent_key)
    
    minutes, seconds = divmod(elapsed_seconds, 60)
    elapsed_str = f"{minutes}:{seconds:02d}" if minutes > 0 else f"0:{seconds:02d}"
    
    return {
        "kind": "current_step",
        "name": description[:80],
        "elapsed": elapsed_str,
        "position": f"{current_idx + 1}/{total}",
        "status": step.get("status", "running"),  # "thinking", "running", "completed", "failed"
    }


async def maybe_emit_progress_narrative(
    job_id: str,
    phase_label: str,
    steps: List[Dict[str, Any]],
    *,
    job_goal: str = "",
) -> None:
    """Emit at most one progress brain_guidance per distinct phase_label while the job runs."""
    pl = (phase_label or "running").strip() or "running"
    if _last_progress_phase.get(job_id) == pl:
        return
    _last_progress_phase[job_id] = pl

    payload = build_phase_progress_narrative(steps, phase_label=pl, job_goal=job_goal)

    from .event_bus import publish
    from .runtime_state import append_job_event

    await append_job_event(job_id, "brain_guidance", payload)
    await publish(job_id, "brain_guidance", payload)
