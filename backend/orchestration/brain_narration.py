"""
Structured coaching copy for job events and UI (brain "talks", not only logs).

Template-first for latency and cost; optional LLM hook can be added later.
"""

from __future__ import annotations

from typing import Any, Dict, List


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
