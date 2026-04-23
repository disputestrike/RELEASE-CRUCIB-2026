"""Sandbox resource limit parsing (fifty-point #14)."""

from sandbox_executor import MAX_CPU_SECONDS, MAX_MEMORY_MB, get_sandbox_resource_limits


def test_get_sandbox_resource_limits_defaults(monkeypatch):
    for key in (
        "CRUCIBAI_SANDBOX_MAX_MEMORY_MB",
        "CRUCIBAI_SANDBOX_CPU_SECONDS",
        "CRUCIBAI_SANDBOX_MAX_NPROC",
        "CRUCIBAI_SANDBOX_MAX_FSIZE_MB",
    ):
        monkeypatch.delenv(key, raising=False)
    lim = get_sandbox_resource_limits()
    assert lim["max_memory_mb"] == MAX_MEMORY_MB
    assert lim["max_cpu_seconds"] == MAX_CPU_SECONDS
    assert lim["max_nproc"] == 10
    assert lim["max_fsize_mb"] == 50


def test_get_sandbox_resource_limits_env_override(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SANDBOX_MAX_MEMORY_MB", "256")
    monkeypatch.setenv("CRUCIBAI_SANDBOX_CPU_SECONDS", "15")
    monkeypatch.setenv("CRUCIBAI_SANDBOX_MAX_NPROC", "4")
    monkeypatch.setenv("CRUCIBAI_SANDBOX_MAX_FSIZE_MB", "32")
    lim = get_sandbox_resource_limits()
    assert lim["max_memory_mb"] == 256
    assert lim["max_cpu_seconds"] == 15
    assert lim["max_nproc"] == 4
    assert lim["max_fsize_mb"] == 32


def test_get_sandbox_resource_limits_clamps_invalid(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SANDBOX_MAX_MEMORY_MB", "not-a-number")
    lim = get_sandbox_resource_limits()
    assert lim["max_memory_mb"] == MAX_MEMORY_MB


def test_get_sandbox_resource_limits_clamps_high(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SANDBOX_MAX_MEMORY_MB", "999999")
    lim = get_sandbox_resource_limits()
    assert lim["max_memory_mb"] == 8192
