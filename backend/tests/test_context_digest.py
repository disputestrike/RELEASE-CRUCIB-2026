from backend.orchestration.context_digest import last_error_traces


def test_last_error_traces_from_fail_events():
    ev = [
        {"type": "step_failed", "payload": {"error": "preview broke"}},
        {"type": "heartbeat", "payload": {}},
    ]
    assert last_error_traces(ev, limit=2) == ["preview broke"]


def test_runtime_state_payload_json_shape():
    ev = [
        {
            "event_type": "verification_failed",
            "payload_json": '{"error": "vite build failed"}',
        }
    ]
    assert last_error_traces(ev, limit=2) == ["vite build failed"]


def test_issues_on_verification_event():
    ev = [
        {
            "type": "job_failed",
            "payload": {"issues": ["saas contract failed"], "reason": "preview_gate"},
        }
    ]
    assert "saas" in last_error_traces(ev, limit=1)[0].lower()
