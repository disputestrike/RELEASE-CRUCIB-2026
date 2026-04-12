import pytest
from orchestration.controller_brain import (
    build_live_job_progress,
    build_plan_controller_summary,
)


def test_build_plan_controller_summary_exposes_selection_reasons():
    summary = build_plan_controller_summary(
        goal="Build realtime collaboration with socket.io and rate limiting",
        phases=[
            {"label": "Planning", "steps": [{"key": "planning.analyze"}]},
            {
                "label": "Agents",
                "steps": [
                    {"key": "agents.websocket_agent"},
                    {"key": "agents.rate_limiting_agent"},
                ],
            },
        ],
        selected_agents=[
            "Planner",
            "WebSocket Agent",
            "Real-Time Collaboration Agent",
            "Rate Limiting Agent",
        ],
        selection_explanation={
            "matched_keywords": ["socket.io", "rate limiting"],
            "matched_rules": ["rule:realtime_collaboration", "rule:rate_limiting"],
            "specialized_agent_count": 3,
        },
    )

    assert summary["controller_mode"] == "selective_parallel_swarm"
    assert summary["specialized_agent_count"] == 3
    assert "socket.io" in summary["matched_keywords"]
    assert summary["has_parallel_phases"] is True
    assert summary["execution_strategy"] == "dependency_aware_parallelism"
    assert summary["parallel_groups"][0]["step_count"] == 2
    assert "launch_parallel_specialists" in summary["next_actions"]
    assert summary["memory_strategy"] == "scoped_project_job_phase_memory"


def test_live_job_progress_derives_phases_and_blockers():
    payload = build_live_job_progress(
        job={"id": "job-1", "status": "running"},
        steps=[
            {
                "id": "1",
                "step_key": "planning.analyze",
                "agent_name": "Planner",
                "phase": "planning",
                "status": "completed",
                "order_index": 1,
            },
            {
                "id": "2",
                "step_key": "agents.frontend_generation",
                "agent_name": "Frontend Generation",
                "phase": "agents.phase_01",
                "status": "running",
                "order_index": 2,
            },
            {
                "id": "3",
                "step_key": "agents.security_checker",
                "agent_name": "Security Checker",
                "phase": "agents.phase_01",
                "status": "failed",
                "order_index": 3,
                "error_message": "missing CSP",
            },
        ],
        events=[
            {
                "event_type": "step_started",
                "created_at": "2026-04-09T00:00:00+00:00",
                "payload": {"agent_name": "Frontend Generation"},
            },
            {
                "event_type": "step_failed",
                "created_at": "2026-04-09T00:00:01+00:00",
                "payload": {"agent_name": "Security Checker", "error": "missing CSP"},
            },
        ],
    )

    assert payload["current_phase"] == "agents.phase_01"
    assert payload["controller"]["status"] == "attention_required"
    assert payload["controller"]["blocker_count"] == 1
    assert payload["phases"][1]["status"] == "error"
    assert payload["logs"][-1]["level"] == "error"
    assert payload["controller"]["active_agent_count"] == 1
    assert payload["controller"]["recommended_focus"] == "Unblock Security Checker"
    assert (
        payload["controller"]["repair_plan"][0]["action"]
        == "run_security_hardening_pass"
    )
