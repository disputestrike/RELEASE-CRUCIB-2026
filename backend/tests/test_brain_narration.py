"""Unit tests for brain narration / steering copy."""

from orchestration.brain_narration import (
    build_execution_think_payload,
    build_phase_progress_narrative,
    build_steering_guidance,
)


def test_steering_guidance_resume_uses_resume_coach():
    g = build_steering_guidance("fix it", resume=True, job_status="failed")
    assert "re-queued" in g["summary"].lower() or "continuing" in g["headline"].lower()


def test_steering_guidance_running_job_no_resume():
    g = build_steering_guidance("what happened?", resume=False, job_status="running")
    assert g["headline"] == "Message recorded"
    assert "re-queued" not in g["summary"].lower()


def test_steering_guidance_failed_no_resume():
    g = build_steering_guidance("try again", resume=False, job_status="failed")
    assert "re-queued" not in g["summary"].lower()
    assert "resume" in g["summary"].lower() or "saved" in g["summary"].lower()


def test_phase_progress_narrative_counts_and_humanizes():
    steps = [
        {"status": "completed", "step_key": "plan"},
        {"status": "running", "step_key": "verification.preview"},
    ]
    p = build_phase_progress_narrative(steps, phase_label="verify_bundle")
    assert p["kind"] == "progress_narrative"
    assert "1/2" in p["summary"].replace(" ", "")
    assert "Verifying preview" in p["summary"]


def test_execution_think_fresh_run_all_pending():
    steps = [
        {"status": "pending", "step_key": "a"},
        {"status": "pending", "step_key": "b"},
    ]
    p = build_execution_think_payload({"current_phase": ""}, steps)
    assert p["kind"] == "execution_think"
    assert "starting" in p["headline"].lower()
    assert "plan" in p["summary"].lower()


def test_execution_think_resume_after_failure_phase():
    steps = [
        {"status": "completed", "step_key": "x"},
        {"status": "pending", "step_key": "y"},
    ]
    p = build_execution_think_payload(
        {"current_phase": "resuming_after_failure"}, steps
    )
    assert p["kind"] == "execution_think"
    assert "continuing" in p["headline"].lower()
    assert "blocked" in p["summary"].lower() or "stopped" in p["summary"].lower()


def test_execution_think_mid_run_partial_progress():
    steps = [
        {"status": "completed", "step_key": "x"},
        {"status": "pending", "step_key": "y"},
    ]
    p = build_execution_think_payload({"current_phase": "running"}, steps)
    assert p["kind"] == "execution_think"
    assert "continuing" in p["headline"].lower()


def test_execution_think_no_steps():
    p = build_execution_think_payload({"current_phase": ""}, [])
    assert p["kind"] == "execution_think"
    assert "organized" in p["headline"].lower() or "lining" in p["summary"].lower()


def test_phase_progress_narrative_flags_blocked():
    steps = [
        {"status": "completed"},
        {"status": "blocked", "step_key": "agents.foo"},
    ]
    p = build_phase_progress_narrative(steps, phase_label="x")
    assert "needs attention" in p["headline"].lower()
