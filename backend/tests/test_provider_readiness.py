"""Provider readiness and live-model wiring tests."""
from provider_readiness import build_provider_readiness, env_contract, selected_chain_for_prompt


def test_provider_env_contract_names_are_exact():
    contract = env_contract()
    providers = contract["providers"]
    assert providers["anthropic"]["key_env"] == "ANTHROPIC_API_KEY"
    assert providers["anthropic"]["model_env"] == "ANTHROPIC_MODEL"
    assert providers["cerebras"]["key_env"][0] == "CEREBRAS_API_KEY"
    assert "CEREBRAS_API_KEY_5" in providers["cerebras"]["key_env"]
    assert providers["llama"]["key_env"] == "LLAMA_API_KEY"


def test_provider_readiness_reports_missing_keys_without_secret_values():
    readiness = build_provider_readiness(env={})
    assert readiness["status"] == "not_configured"
    assert readiness["secret_values_included"] is False
    assert "no_live_provider_configured" in readiness["warnings"]
    assert readiness["providers"]["anthropic"]["missing_env"] == ["ANTHROPIC_API_KEY"]


def test_provider_readiness_selects_anthropic_for_complex_build_when_configured():
    readiness = build_provider_readiness(
        prompt="Build a full-stack app with auth, database, deployment, and proof.",
        env={"ANTHROPIC_API_KEY": "test-key"},
    )
    assert readiness["status"] == "ready"
    assert readiness["prompt_classification"] == "complex"
    assert readiness["selected_chain"][0]["provider"] == "anthropic"
    assert readiness["providers"]["anthropic"]["configured"] is True


def test_provider_readiness_selects_cerebras_for_simple_task_when_configured():
    complexity, chain = selected_chain_for_prompt(
        "Format this paragraph.",
        env={"CEREBRAS_API_KEY": "test-key"},
    )
    assert complexity == "simple"
    assert chain[0]["provider"] == "cerebras"


def test_provider_readiness_reports_cerebras_key_pool():
    readiness = build_provider_readiness(
        prompt="Format this paragraph.",
        env={"CEREBRAS_API_KEY": "key-a", "CEREBRAS_API_KEY_2": "key-b"},
    )
    assert readiness["providers"]["cerebras"]["key_count"] == 2
    assert readiness["providers"]["cerebras"]["configured_key_envs"] == [
        "CEREBRAS_API_KEY",
        "CEREBRAS_API_KEY_2",
    ]
