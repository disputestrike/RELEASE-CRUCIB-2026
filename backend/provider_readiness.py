"""Provider readiness reporting for CrucibAI live-model paths.

This module is intentionally side-effect free: it never calls a provider and it
never returns secret values. It reports the exact environment variable contract
and the provider chain the runtime should use for a representative prompt.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model

ANTHROPIC_MODEL_DEFAULT = ANTHROPIC_HAIKU_MODEL
CEREBRAS_MODEL_DEFAULT = "llama-3.3-70b"
LLAMA_MODEL_DEFAULT = "meta-llama/Llama-2-70b-chat-hf"
CEREBRAS_KEY_ENV_NAMES = ["CEREBRAS_API_KEY"] + [f"CEREBRAS_API_KEY_{i}" for i in range(1, 6)]


def _sandbox_status(env: "Mapping[str, str]") -> "dict[str, Any]":
    """Report E2B sandbox readiness."""
    e2b_key = _env_value(env, "E2B_API_KEY")
    return {
        "e2b": {
            "configured": bool(e2b_key),
            "key_env": "E2B_API_KEY",
            "missing_env": [] if e2b_key else ["E2B_API_KEY"],
            "fallback": "in-process sandbox (resource-limited)" if not e2b_key else None,
            "role": "isolated code execution for Test Executor and Backend Generation validation",
        }
    }


COMPLEX_KEYWORDS = {
    "architecture",
    "auth",
    "authentication",
    "backend",
    "build",
    "database",
    "deploy",
    "full stack",
    "generate",
    "implement",
    "migration",
    "performance",
    "refactor",
    "security",
    "workspace",
}

SIMPLE_KEYWORDS = {
    "comment",
    "format",
    "rename",
    "spacing",
    "style",
    "typo",
}

CRITICAL_AGENT_HINTS = {
    "security checker",
    "deployment agent",
    "database agent",
    "backend generation",
    "auth setup agent",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_value(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name) or "").strip()


def _env_bool(env: Mapping[str, str], name: str) -> bool:
    return _env_value(env, name).lower() in {"1", "true", "yes", "on"}


def env_contract() -> dict[str, Any]:
    """Return the live-provider environment contract without secret values."""
    return {
        "required_for_any_live_llm": [
            "one of ANTHROPIC_API_KEY, CEREBRAS_API_KEY, CEREBRAS_API_KEY_1..5, LLAMA_API_KEY",
        ],
        "providers": {
            "anthropic": {
                "key_env": "ANTHROPIC_API_KEY",
                "model_env": "ANTHROPIC_MODEL",
                "default_model": ANTHROPIC_MODEL_DEFAULT,
                "role": "quality/complex build fallback and preferred complex build path",
            },
            "cerebras": {
                "key_env": CEREBRAS_KEY_ENV_NAMES,
                "model_env": "CEREBRAS_MODEL",
                "default_model": CEREBRAS_MODEL_DEFAULT,
                "role": "fast/simple generation path and fallback when configured",
            },
            "llama": {
                "key_env": "LLAMA_API_KEY",
                "model_env": "LLAMA_MODEL",
                "default_model": LLAMA_MODEL_DEFAULT,
                "role": "optional Together-hosted Llama path when configured",
            },
        },
        "sandbox": {
            "e2b": {
                "key_env": "E2B_API_KEY",
                "role": "isolated code execution for Test Executor and Backend Generation validation",
                "fallback": "in-process sandbox when E2B_API_KEY not set",
            },
        },
    }


def classify_prompt(prompt: str, agent_name: str = "") -> str:
    """Mirror the runtime's coarse task classification for readiness reporting."""
    text = (prompt or "").lower()
    agent = (agent_name or "").lower()
    if any(hint in agent for hint in CRITICAL_AGENT_HINTS):
        return "critical"
    if any(word in text for word in COMPLEX_KEYWORDS) or len(text) > 150:
        return "complex"
    if any(word in text for word in SIMPLE_KEYWORDS):
        return "simple"
    return "moderate"


def _provider_status(env: Mapping[str, str]) -> dict[str, Any]:
    anthropic_key = _env_value(env, "ANTHROPIC_API_KEY")
    cerebras_keys = [name for name in CEREBRAS_KEY_ENV_NAMES if _env_value(env, name)]
    llama_key = _env_value(env, "LLAMA_API_KEY")

    return {
        "anthropic": {
            "configured": bool(anthropic_key),
            "missing_env": [] if anthropic_key else ["ANTHROPIC_API_KEY"],
            "model": normalize_anthropic_model(
                _env_value(env, "ANTHROPIC_MODEL"),
                default=ANTHROPIC_MODEL_DEFAULT,
            ),
            "disabled": _env_bool(env, "CRUCIBAI_DISABLE_ANTHROPIC"),
            "key_count": 1 if anthropic_key else 0,
        },
        "cerebras": {
            "configured": bool(cerebras_keys),
            "missing_env": [] if cerebras_keys else CEREBRAS_KEY_ENV_NAMES,
            "model": _env_value(env, "CEREBRAS_MODEL") or CEREBRAS_MODEL_DEFAULT,
            "disabled": _env_bool(env, "CRUCIBAI_DISABLE_CEREBRAS"),
            "key_count": len(cerebras_keys),
            "configured_key_envs": cerebras_keys,
        },
        "llama": {
            "configured": bool(llama_key),
            "missing_env": [] if llama_key else ["LLAMA_API_KEY"],
            "model": _env_value(env, "LLAMA_MODEL") or LLAMA_MODEL_DEFAULT,
            "disabled": _env_bool(env, "CRUCIBAI_DISABLE_LLAMA"),
            "key_count": 1 if llama_key else 0,
        },
    }


def _append_available(chain: list[dict[str, str]], providers: Mapping[str, Any], provider: str) -> None:
    status = providers[provider]
    if status["configured"] and not status["disabled"]:
        chain.append({"provider": provider, "model": status["model"]})


def selected_chain_for_prompt(
    prompt: str,
    *,
    agent_name: str = "",
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    env: Mapping[str, str] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Return the production-faithful provider order for a representative prompt."""
    env = env or os.environ
    providers = _provider_status(env)
    complexity = classify_prompt(prompt, agent_name)

    names: list[str]
    if user_tier == "free":
        names = ["cerebras", "llama", "anthropic"] if complexity == "simple" else ["llama", "cerebras", "anthropic"]
    elif user_tier == "builder":
        names = ["cerebras", "llama", "anthropic"] if speed_selector == "lite" else ["llama", "cerebras", "anthropic"]
    else:
        names = ["cerebras", "llama", "anthropic"] if speed_selector == "lite" else ["llama", "cerebras", "anthropic"]

    if complexity == "critical" and "llama" in names:
        names = ["llama"] + [name for name in names if name != "llama"]
    if complexity == "simple" and "cerebras" in names:
        names = ["cerebras"] + [name for name in names if name != "cerebras"]
    if available_credits < 10 and "anthropic" in names:
        names = [name for name in names if name != "anthropic"] + ["anthropic"]

    chain: list[dict[str, str]] = []
    for name in names:
        _append_available(chain, providers, name)
    return complexity, chain


def build_provider_readiness(
    *,
    prompt: str = "Build a full-stack todo app with auth and deploy proof.",
    agent_name: str = "",
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return readiness state for provider wiring. Secret values are never included."""
    env = env or os.environ
    providers = _provider_status(env)
    complexity, chain = selected_chain_for_prompt(
        prompt,
        agent_name=agent_name,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        env=env,
    )
    warnings: list[str] = []
    if not chain:
        warnings.append("no_live_provider_configured")
    if complexity in {"complex", "critical"} and not providers["anthropic"]["configured"]:
        warnings.append("complex_or_critical_prompt_without_anthropic_key")
    if providers["cerebras"]["configured"] and providers["cerebras"]["key_count"] == 1:
        warnings.append("single_cerebras_key_no_rotation_pool")

    return {
        "generated_at": _now_iso(),
        "status": "ready" if chain else "not_configured",
        "live_invocation": "not_run",
        "secret_values_included": False,
        "prompt_classification": complexity,
        "selected_chain": chain,
        "providers": providers,
        "sandbox": _sandbox_status(env),
        "warnings": warnings,
        "env_contract": env_contract(),
    }


def _write_json(path: Path, data: MutableMapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write CrucibAI provider readiness proof JSON.")
    parser.add_argument("--prompt", default="Build a full-stack todo app with auth and deploy proof.")
    parser.add_argument("--agent-name", default="")
    parser.add_argument("--user-tier", default="free")
    parser.add_argument("--speed-selector", default="lite")
    parser.add_argument("--available-credits", type=int, default=0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    readiness = build_provider_readiness(
        prompt=args.prompt,
        agent_name=args.agent_name,
        user_tier=args.user_tier,
        speed_selector=args.speed_selector,
        available_credits=args.available_credits,
    )
    if args.output:
        _write_json(Path(args.output), readiness)
    print(json.dumps(readiness, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
