from __future__ import annotations

from backend import server


def test_cors_wildcard_not_used_with_credentials_enabled():
    if server.cors_allow_credentials:
        assert server.cors_origins
        assert server.cors_origins != ["*"]


def test_cors_configuration_has_explicit_runtime_signal():
    # Ensure the runtime is explicit about whether credentials are enabled.
    assert isinstance(server.cors_allow_credentials, bool)
