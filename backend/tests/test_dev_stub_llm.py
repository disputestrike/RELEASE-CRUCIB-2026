"""Dev stub LLM: local preview without API keys — must not activate under REAL_AGENT_ONLY."""

from dev_stub_llm import chat_llm_available, is_real_agent_only, stub_build_enabled


def test_chat_llm_available_from_effective_keys():
    assert chat_llm_available({"anthropic": "sk-test", "cerebras": None}) is True
    assert chat_llm_available({"anthropic": "", "cerebras": "x"}) is True


def test_is_real_agent_only_env(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_REAL_AGENT_ONLY", raising=False)
    assert is_real_agent_only() is False
    monkeypatch.setenv("CRUCIBAI_REAL_AGENT_ONLY", "1")
    assert is_real_agent_only() is True


def test_stub_disabled_when_real_agent_only(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_TEST", raising=False)
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("CRUCIBAI_REAL_AGENT_ONLY", "1")
    assert stub_build_enabled() is False


def test_stub_disabled_in_pytest_even_with_dev(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_TEST", "1")
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.delenv("CRUCIBAI_REAL_AGENT_ONLY", raising=False)
    assert stub_build_enabled() is False
