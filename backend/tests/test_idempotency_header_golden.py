"""Golden tests: Idempotency-Key header parsing for LLM credit paths (#17)."""

import pytest
from starlette.requests import Request


@pytest.mark.golden
def test_idempotency_key_from_request_reads_header():
    from server import _idempotency_key_from_request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/ai/chat",
        "raw_path": b"/api/ai/chat",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"idempotency-key", b"  client-retry-001  ")],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }
    req = Request(scope)
    assert _idempotency_key_from_request(req) == "client-retry-001"


@pytest.mark.golden
def test_idempotency_key_from_request_x_prefixed():
    from server import _idempotency_key_from_request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"x-idempotency-key", b"alt-key")],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }
    req = Request(scope)
    assert _idempotency_key_from_request(req) == "alt-key"


@pytest.mark.golden
def test_idempotency_key_rejects_oversized():
    from server import _idempotency_key_from_request

    big = "x" * 300
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"idempotency-key", big.encode("utf-8"))],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }
    req = Request(scope)
    assert _idempotency_key_from_request(req) is None
