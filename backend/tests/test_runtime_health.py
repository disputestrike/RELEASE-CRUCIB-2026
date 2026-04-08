from orchestration.runtime_health import default_api_healthcheck_url


def test_default_api_healthcheck_url_uses_explicit_env(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_HEALTHCHECK_URL", "http://example.test/healthz")
    monkeypatch.setenv("PORT", "12345")

    assert default_api_healthcheck_url() == "http://example.test/healthz"


def test_default_api_healthcheck_url_uses_railway_port(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_HEALTHCHECK_URL", raising=False)
    monkeypatch.setenv("PORT", "12345")

    assert default_api_healthcheck_url() == "http://127.0.0.1:12345/api/health"


def test_default_api_healthcheck_url_defaults_to_local_dev_port(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_HEALTHCHECK_URL", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    assert default_api_healthcheck_url() == "http://127.0.0.1:8000/api/health"
