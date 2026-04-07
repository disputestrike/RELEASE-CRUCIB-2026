"""
Golden-path regression tests: deterministic, no external LLM calls.
Marked with @pytest.mark.golden for `scripts/run_golden_eval.py` and Fifty-point #43–#44, #50.
"""
import pytest
from fastapi.testclient import TestClient

from dev_stub_llm import detect_build_kind
from server import app


@pytest.mark.golden
def test_detect_build_kind_landing_stable():
    assert detect_build_kind("Build a one page marketing site") == "landing"


@pytest.mark.golden
def test_detect_build_kind_saas_stable():
    assert detect_build_kind("saas dashboard with subscription billing") == "saas"


@pytest.mark.golden
def test_detect_build_kind_mobile_stable():
    assert detect_build_kind("expo react native ios app") == "mobile"


@pytest.mark.golden
def test_detect_build_kind_ai_agent_stable():
    assert detect_build_kind("customer support chatbot with automation") == "ai_agent"


@pytest.mark.golden
def test_detect_build_kind_game_stable():
    assert detect_build_kind("simple 2d game in the browser") == "game"


@pytest.mark.golden
def test_detect_build_kind_fullstack_default():
    assert detect_build_kind("generic crud app with users") == "fullstack"


@pytest.mark.golden
def test_openapi_json_includes_health_paths():
    with TestClient(app) as c:
        r = c.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert str(data.get("openapi", "")).startswith("3.")
        paths = data.get("paths") or {}
        assert any("health" in p for p in paths), "expected at least one /api/health* path in OpenAPI"
        assert any("/api/" in p for p in paths), "expected /api-prefixed routes in OpenAPI"
        chatish = [p for p in paths if "chat" in p.lower()]
        assert chatish, "expected at least one chat-related path (e.g. /api/chat) in OpenAPI"


@pytest.mark.golden
def test_health_live_always_200():
    with TestClient(app) as c:
        r = c.get("/api/health/live")
        assert r.status_code == 200
        body = r.json()
        assert body.get("check") == "liveness"
        assert body.get("status") == "healthy"


@pytest.mark.golden
def test_health_ready_reports_database():
    with TestClient(app) as c:
        r = c.get("/api/health/ready")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("check") == "readiness"
        assert body.get("database") == "ok"


@pytest.mark.golden
def test_api_responses_include_sandpack_aware_csp():
    """Middleware CSP allows Codesandbox/Sandpack + jsDelivr (PreviewPanel tailwind CDN)."""
    with TestClient(app) as c:
        r = c.get("/api/health/live")
        assert r.status_code == 200
        csp = r.headers.get("content-security-policy") or ""
        assert "frame-src" in csp and "codesandbox" in csp
        assert "cdn.jsdelivr.net" in csp
