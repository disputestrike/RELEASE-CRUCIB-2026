"""SSRF validator unit tests (Fifty-point #11 / #12)."""
import pytest

from ssrf_prevention import SSRFValidator


@pytest.mark.golden
def test_ssrf_private_loopback():
    v = SSRFValidator()
    assert v.is_private_ip("127.0.0.1") is True
    assert v.is_private_ip("10.0.0.1") is True


@pytest.mark.golden
def test_ssrf_public_ip_not_private():
    v = SSRFValidator()
    assert v.is_private_ip("8.8.8.8") is False


@pytest.mark.golden
def test_ssrf_dangerous_ports():
    v = SSRFValidator()
    assert v.is_dangerous_port(5432) is True
    assert v.is_dangerous_port(6379) is True
    assert v.is_dangerous_port(443) is False
    assert v.is_dangerous_port(80) is False


@pytest.mark.golden
def test_ssrf_whitelisted_host_short_circuits():
    v = SSRFValidator(allowed_domains={"example.com", "api.example.com"})
    assert v.validate_url("https://example.com/foo") is True


@pytest.mark.golden
def test_ssrf_rejects_public_hostname_resolving_to_loopback(monkeypatch):
    """DNS-style rebinding: hostname must not resolve to private space for non-whitelisted URLs."""
    v = SSRFValidator(allowed_domains=set())
    monkeypatch.setattr("ssrf_prevention.socket.gethostbyname", lambda _host: "127.0.0.1")
    assert v.validate_url("https://fake-public.example/path") is False
