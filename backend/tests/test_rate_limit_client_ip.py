"""Rate limit middleware client IP extraction (Fifty-point #16)."""

from typing import List, Optional, Tuple

import pytest
from middleware import RateLimitMiddleware
from starlette.requests import Request


def _make_request(
    *, client_host: str, headers: Optional[List[Tuple[bytes, bytes]]] = None
) -> Request:
    hdrs = headers or []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/health",
        "raw_path": b"/api/health",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": hdrs,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.golden
def test_rate_limit_prefers_x_forwarded_for():
    req = _make_request(
        client_host="127.0.0.1",
        headers=[(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")],
    )
    assert RateLimitMiddleware._client_ip(req) == "203.0.113.9"


@pytest.mark.golden
def test_rate_limit_falls_back_to_socket_client():
    req = _make_request(client_host="192.168.1.50", headers=[])
    assert RateLimitMiddleware._client_ip(req) == "192.168.1.50"
