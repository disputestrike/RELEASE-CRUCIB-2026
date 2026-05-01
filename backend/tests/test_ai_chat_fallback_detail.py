from backend.routes.ai import _format_fallback_detail, _provider_from_model_used


def test_provider_from_model_used_parses_known_prefixes():
    assert _provider_from_model_used("cerebras/llama3.1-8b") == "cerebras"
    assert _provider_from_model_used("haiku/claude-3-5-haiku") == "anthropic"
    assert _provider_from_model_used("anthropic/claude-3-5-sonnet") == "anthropic"


def test_format_fallback_detail_includes_attempt_chain_and_flags():
    exc = RuntimeError("Anthropic API returned 400: credit balance too low")
    detail = _format_fallback_detail(
        exc,
        [
            ("haiku", "claude-3-5-haiku", "anthropic"),
            ("cerebras-fast", "llama3.1-8b", "cerebras"),
        ],
    )
    assert detail["error"] == "llm_fallback_failed"
    assert detail["provider_attempted"] == "anthropic"
    assert detail["fallback_provider_attempted"] is True
    assert detail["fallback_provider_succeeded"] is False
    assert len(detail["provider_attempt_chain"]) == 2
