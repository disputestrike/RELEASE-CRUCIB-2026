"""Structured logs carry correlation_id alongside request_id (fifty-point #35)."""
import json
import logging

import pytest


@pytest.fixture
def structured_logs_on(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_STRUCTURED_LOGS", "1")


def test_log_request_event_correlation_id_matches_request_id(structured_logs_on):
    from orchestration.observability import (
        bind_http_request_context,
        clear_http_request_context,
        log_request_event,
    )

    log = logging.getLogger("observability_test")
    log.setLevel(logging.INFO)
    captured = []

    class Capture(logging.Handler):
        def emit(self, record):
            captured.append(record.getMessage())

    h = Capture()
    log.addHandler(h)
    bind_http_request_context(request_id="corr-test-1", trace_id="tr-1", tenant_id="")
    try:
        log_request_event(log, "unit_test", path="/x")
    finally:
        clear_http_request_context()
        log.removeHandler(h)

    assert len(captured) == 1
    payload = json.loads(captured[0])
    assert payload["request_id"] == "corr-test-1"
    assert payload["correlation_id"] == "corr-test-1"
    assert payload["event"] == "unit_test"
