"""
Event Bridge — translates CrucibAI internal events → frontend-compatible event types.

Internal (our SSE): brain_guidance, file_written, step_completed, step_failed, job_completed
Frontend expects:   phase.started, phase.complete, artifact.created, issue.detected,
                    issue.fixed, subagent.started, subagent.complete, deploy.live, job.complete
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _make_event(job_id: str, event_type: str, payload: dict,
                phase_id: str = None, agent_id: str = None) -> dict:
    ev = {
        "type": event_type,
        "jobId": job_id,
        "timestamp": int(time.time() * 1000),
        "payload": payload,
    }
    if phase_id:
        ev["phaseId"] = phase_id
    if agent_id:
        ev["agentId"] = agent_id
    return ev


def emit(job_id: str, event_type: str, payload: dict,
         phase_id: str = None, agent_id: str = None):
    """Fire-and-forget emit to all WebSocket clients for this job."""
    from adapter.websocket_manager import manager
    event = _make_event(job_id, event_type, payload, phase_id, agent_id)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast(job_id, event))
        else:
            loop.run_until_complete(manager.broadcast(job_id, event))
    except Exception as e:
        logger.debug("emit failed: %s", e)


# ── Mapping functions ─────────────────────────────────────────────────────────
# Call these from your orchestration hooks to feed the frontend

def on_job_started(job_id: str, goal: str, estimated_steps: int = 0):
    emit(job_id, "job.started", {
        "goal": goal,
        "estimatedSteps": estimated_steps,
    })


def on_phase_started(job_id: str, phase_name: str, description: str = "",
                     phase_id: str = None):
    emit(job_id, "phase.started", {
        "phaseName": phase_name,
        "description": description,
    }, phase_id=phase_id)


def on_phase_progress(job_id: str, phase_name: str, progress: float,
                      phase_id: str = None):
    emit(job_id, "phase.progress", {
        "phaseName": phase_name,
        "progress": progress,
    }, phase_id=phase_id)


def on_phase_complete(job_id: str, phase_name: str, artifacts: list = None,
                      phase_id: str = None):
    emit(job_id, "phase.complete", {
        "phaseName": phase_name,
        "artifacts": artifacts or [],
    }, phase_id=phase_id)


def on_phase_error(job_id: str, phase_name: str, error: str, phase_id: str = None):
    emit(job_id, "phase.error", {
        "phaseName": phase_name,
        "error": error,
    }, phase_id=phase_id)


def on_agent_thinking(job_id: str, thought: str, agent_id: str = None):
    emit(job_id, "agent.thinking", {
        "thought": thought,
    }, agent_id=agent_id)


def on_artifact_created(job_id: str, artifact_type: str, path: str,
                        content_snippet: str = "", agent_id: str = None):
    emit(job_id, "artifact.created", {
        "type": artifact_type,
        "path": path,
        "contentSnippet": content_snippet[:200],
    }, agent_id=agent_id)


def on_artifact_modified(job_id: str, path: str, diff_snippet: str = ""):
    emit(job_id, "artifact.modified", {
        "path": path,
        "diffSnippet": diff_snippet[:200],
    })


def on_issue_detected(job_id: str, title: str, description: str,
                      severity: str = "medium", cause: str = ""):
    emit(job_id, "issue.detected", {
        "title": title,
        "description": description,
        "severity": severity,
        "cause": cause,
    })


def on_issue_fixed(job_id: str, title: str, fix: str):
    emit(job_id, "issue.fixed", {
        "title": title,
        "fix": fix,
    })


def on_subagent_started(job_id: str, subagent_id: str, role: str, task: str):
    emit(job_id, "subagent.started", {
        "subagentId": subagent_id,
        "role": role,
        "task": task,
    })


def on_subagent_complete(job_id: str, subagent_id: str, result: Any = None):
    emit(job_id, "subagent.complete", {
        "subagentId": subagent_id,
        "result": result,
    })


def on_subagent_failed(job_id: str, subagent_id: str, error: str):
    emit(job_id, "subagent.failed", {
        "subagentId": subagent_id,
        "error": error,
    })


def on_deploy_ready(job_id: str, preview_url: str):
    emit(job_id, "deploy.ready", {"previewUrl": preview_url})


def on_deploy_live(job_id: str, url: str, preview_url: str = ""):
    emit(job_id, "deploy.live", {
        "url": url,
        "previewUrl": preview_url or url,
    })


def on_job_complete(job_id: str, quality_score: float, url: str = "",
                    summary: dict = None):
    emit(job_id, "job.complete", {
        "qualityScore": quality_score,
        "url": url,
        "summary": summary or {},
    })


def on_job_error(job_id: str, error: str, recoverable: bool = True):
    emit(job_id, "job.error", {
        "error": error,
        "recoverable": recoverable,
    })


def on_milestone_reached(job_id: str, title: str, description: str = ""):
    emit(job_id, "milestone.reached", {
        "title": title,
        "description": description,
    })


def on_steer_accepted(job_id: str, summary: str, before_phase: str = "",
                      after_phase: str = "", affected_agents: list = None):
    emit(job_id, "steer.accepted", {
        "summary": summary,
        "beforePhase": before_phase,
        "afterPhase": after_phase,
        "affectedAgents": affected_agents or [],
    })


def on_steer_rejected(job_id: str, reason: str):
    emit(job_id, "steer.rejected", {"reason": reason})


# ── Bridge from our internal SSE events → frontend events ────────────────────
# Call this to translate any internal event dict into frontend-compatible format

INTERNAL_TO_FRONTEND = {
    "brain_guidance":   lambda j, p: on_agent_thinking(j,
                            p.get("payload", p).get("headline") or
                            p.get("payload", p).get("summary", ""), j),
    "file_written":     lambda j, p: on_artifact_created(j, "file",
                            p.get("path", ""), "", p.get("agent_name", "")),
    "step_completed":   lambda j, p: on_phase_complete(j,
                            p.get("agent_name") or p.get("step_key", ""),
                            phase_id=p.get("id")),
    "step_failed":      lambda j, p: on_issue_detected(j,
                            p.get("agent_name", "Step failed"),
                            p.get("error_message", ""), "high",
                            p.get("error_details", "")),
    "step_retrying":    lambda j, p: on_issue_fixed(j,
                            p.get("agent_name", ""),
                            "Auto-repair applied, retrying"),
    "job_completed":    lambda j, p: on_job_complete(j,
                            p.get("quality_score", 0),
                            p.get("deploy_url", "")),
    "deploy_success":   lambda j, p: on_deploy_live(j,
                            p.get("url", ""), p.get("preview_url", "")),
}


def bridge_internal_event(job_id: str, event_type: str, payload: dict):
    """Translate an internal CrucibAI event to frontend format and emit."""
    handler = INTERNAL_TO_FRONTEND.get(event_type)
    if handler:
        try:
            handler(job_id, payload)
        except Exception as e:
            logger.debug("bridge_internal_event %s: %s", event_type, e)
