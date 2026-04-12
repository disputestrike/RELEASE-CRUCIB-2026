import pytest

from anthropic_models import (
    ANTHROPIC_HAIKU_MODEL,
    ANTHROPIC_SONNET_MODEL,
    normalize_anthropic_model,
)
from llm_client import get_llm_config
from provider_readiness import build_provider_readiness


def test_normalize_anthropic_model_maps_retired_haiku():
    assert (
        normalize_anthropic_model("claude-3-5-haiku-20241022") == ANTHROPIC_HAIKU_MODEL
    )


def test_normalize_anthropic_model_maps_retired_sonnet():
    assert (
        normalize_anthropic_model("claude-3-5-sonnet-20241022")
        == ANTHROPIC_SONNET_MODEL
    )


def test_provider_readiness_normalizes_stale_anthropic_env():
    readiness = build_provider_readiness(
        prompt="Build a full-stack app with auth, database, deployment, and proof.",
        env={
            "ANTHROPIC_API_KEY": "test-key",
            "ANTHROPIC_MODEL": "claude-3-5-haiku-20241022",
        },
    )
    assert readiness["providers"]["anthropic"]["model"] == ANTHROPIC_HAIKU_MODEL
    assert readiness["selected_chain"][0]["model"] == ANTHROPIC_HAIKU_MODEL


def test_llm_client_normalizes_stale_anthropic_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    config = get_llm_config()

    assert config is not None
    assert config.provider == "anthropic"
    assert config.model == ANTHROPIC_SONNET_MODEL


@pytest.mark.asyncio
async def test_base_agent_normalizes_retired_model_before_call(monkeypatch):
    from agents.base_agent import BaseAgent

    captured: dict[str, str] = {}

    class FakeUsage:
        input_tokens = 11
        output_tokens = 7

    class FakeText:
        text = "ok"

    class FakeResponse:
        content = [FakeText()]
        usage = FakeUsage()

    class FakeMessages:
        async def create(self, **kwargs):
            captured["model"] = kwargs["model"]
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    class DummyAgent(BaseAgent):
        async def execute(self, context):
            return {"ok": True}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("agents.base_agent.AsyncAnthropic", FakeAnthropic)

    agent = DummyAgent(llm_client=None, config={})
    content, tokens = await agent.call_llm(
        user_prompt="Build schema",
        system_prompt="You are a database agent.",
        model="claude-3-5-haiku-20241022",
        stream=False,
    )

    assert content == "ok"
    assert tokens == 18
    assert captured["model"] == ANTHROPIC_HAIKU_MODEL
