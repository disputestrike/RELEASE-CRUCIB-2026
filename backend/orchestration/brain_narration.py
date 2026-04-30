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


def _summarize_goal_for_intro(goal: str) -> str:
    """Trim and clean the user goal so it can be embedded inside an intro
    sentence. Returns '' if the goal isn't suitable (too short, generic)."""
    if not goal:
        return ""
    g = " ".join(str(goal).strip().split())
    if not g:
        return ""
    # Drop a leading imperative ("Build me a ...", "Create an ...") so the
    # intro reads naturally: "I'll build a ..." rather than "I'll Build me a ...".
    lowered = g.lower()
    for prefix in (
        "build me a ", "build me an ", "build me ",
        "build a ", "build an ", "build ",
        "create me a ", "create me an ", "create me ",
        "create a ", "create an ", "create ",
        "make me a ", "make me an ", "make ",
        "design a ", "design an ", "design ",
        "develop a ", "develop an ", "develop ",
        "generate a ", "generate an ", "generate ",
    ):
        if lowered.startswith(prefix):
            g = g[len(prefix):]
            break
    g = g.strip().rstrip(".!?")
    if len(g) < 6:
        return ""
    if len(g) > 240:
        g = g[:237].rstrip() + "..."
    return g


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
    goal_summary = _summarize_goal_for_intro(job.get("goal") or "")

    if phase == "resuming_after_failure":
        headline = "Continuing your workspace"
        summary = (
            "I'm picking up from where things stopped - addressing what blocked checks first, "
            "then moving the rest of your plan forward in this conversation."
        )
    elif completed == 0 and pending == total:
        # Manus-style: "I will build <X>. I'll start by initializing the project
        # and then proceed with the development." Falls back to a generic line
        # if the goal didn't yield a usable summary.
        if goal_summary:
            headline = f"I'll build {goal_summary}"
            summary = (
                "I'll start by initializing the project and setting up the foundation, "
                "then build the screens and features, and finish with verification and a live preview."
            )
        else:
            headline = "Starting your build"
            summary = (
                "I'll initialize the project and set up the foundation first, then build the screens and "
                "features, and finish with verification and a live preview."
            )
    elif completed > 0:
        headline = "Continuing your build"
        summary = (
            "I'm picking this run back up - finishing what's left in the plan and re-running checks "
            "as needed."
        )
    else:
        headline = "Starting your build"
        summary = "I'm moving this plan forward step by step. You'll see progress in Preview and Proof."

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

    summary_parts: List[str] = [
        "I found something in the generated workspace that needs another pass, so I am repairing it and keeping the run moving."
    ]
    if "default is not exported" in blob or "not exported" in blob or "import" in blob:
        summary_parts.append("I am reconnecting the app entry and mounted screens.")
    elif "route" in blob or "missing" in blob:
        summary_parts.append("I am filling the missing product surfaces and reconnecting the preview.")
    elif fr:
        summary_parts.append("I am using the current workspace state and latest diagnostic signal to continue.")

    next_steps: List[str] = []

    if "prose" in blob or "preamble" in blob:
        next_steps.append(
            "Cleaning generated source so it stays valid code."
        )
    if "esbuild" in blob or "syntax" in blob or "unexpected" in blob:
        next_steps.append(
            "Repairing the source file that interrupted the preview."
        )
    if "npx" in blob or "esbuild unavailable" in blob:
        next_steps.append(
            "Checking the host runtime needed to render the preview."
        )
    if "timeout" in blob:
        next_steps.append(
            "I am simplifying the next check so the preview can keep moving."
        )
    if "python" in blob or "py_compile" in blob:
        next_steps.append(
            "Repairing backend source before continuing."
        )
    if "tenant" in blob or "set_config" in blob or "app.tenant_id" in blob:
        next_steps.append(
            "Rechecking data isolation and backend policy wiring."
        )

    if not next_steps:
        next_steps.append(
            "I will keep the current workspace and run the next repair pass."
        )
        next_steps.append(
            "Add a note in this chat any time; I will keep it attached to the same workspace."
        )

    headline = "Making a repair pass"

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
            f"Recorded your note ({len(msg)} chars). I am continuing from the current workspace "
            "with your latest direction included."
        ),
        "next_steps": [
            "The preview and files will update as the next pass lands.",
            "Keep steering in this chat; completed work stays attached to the conversation.",
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
                "Your note is saved on this conversation while the current work continues. "
                "I will use it as extra context."
            ),
            "next_steps": [
                "Preview and files will update as the current pass continues.",
                "You can keep steering in this same chat.",
            ],
        }
    if st == "failed":
        return {
            "headline": "Note recorded",
            "summary": (
                "Your steering message is saved on this conversation. I can continue from the current workspace with this context."
            ),
            "next_steps": [
                "Preview and files stay available while the next pass runs.",
                "Send another note any time to refine the same build.",
            ],
        }
    return {
        "headline": "Note recorded",
        "summary": f"Saved your note ({len(msg)} characters) on this conversation.",
        "next_steps": ["Keep steering here; the workspace stays attached to this chat."],
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
            return "Checking the workspace"
        return s.replace("_", " ").replace(".", " - ")[:120] or "In progress"

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
        headline = "Repairing the workspace"
        summary_parts.append(
            "I found a part of the workspace that needs another pass, so I am continuing from the saved files."
        )

    next_steps = [
        "Preview updates when the bundle verifies; Code shows files as they land.",
    ]
    if failed or blocked:
        next_steps.insert(
            0,
            "Use the composer to steer; completed work stays in this conversation.",
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
