"""BuilderAgent: elite directive in LLM system context."""
from __future__ import annotations

import json

import pytest

from agents.builder_agent import BuilderAgent, _load_elite_directive, _parse_build_intent, _spec_echo_blocked


def test_load_elite_directive_reads_workspace(tmp_path):
    p = tmp_path / "proof" / "ELITE_EXECUTION_DIRECTIVE.md"
    p.parent.mkdir(parents=True)
    p.write_text("DIRECTIVE_TEST_MARKER", encoding="utf-8")
    assert _load_elite_directive(str(tmp_path)) == "DIRECTIVE_TEST_MARKER"


def test_parse_gauntlet_intent():
    g = "BLACK-BELT OMEGA GAUNTLET\nsomething"
    i = _parse_build_intent(g)
    assert i["target"] == "Helios Aegis Command"
    assert i["mode"] == "BUILD"


def test_spec_echo_blocked():
    assert _spec_echo_blocked('bad const goal = "I MADE IT MORE DIFFICULT') is True
    assert _spec_echo_blocked("{goal}</p>") is True
    assert _spec_echo_blocked('{"files":{}}') is False


@pytest.mark.asyncio
async def test_execute_injects_directive_into_system_prompt(tmp_path):
    proof = tmp_path / "proof" / "ELITE_EXECUTION_DIRECTIVE.md"
    proof.parent.mkdir(parents=True)
    proof.write_text("## Elite\nInjected directive block.\n", encoding="utf-8")

    captured: dict = {}

    class FakeLLM:
        async def chat(self, system="", messages=None, **kwargs):
            captured["system"] = system
            captured["kwargs"] = kwargs
            return json.dumps(
                {
                    "files": {"main.py": "print(1)"},
                    "api_spec": {"endpoints": []},
                    "setup_instructions": ["pip install -r requirements.txt"],
                }
            )

    agent = BuilderAgent(llm_client=FakeLLM(), config={})
    out = await agent.execute(
        {"workspace_path": str(tmp_path), "goal": "FastAPI service for todos"}
    )
    assert out.get("_elite_directive_injected") is True
    assert "Injected directive block" in captured["system"]
    assert "[EXECUTION MODE] BUILD" in captured["system"]
    assert "[WORKSPACE]" in captured["system"]
    assert captured["kwargs"].get("temperature") == 0.1
    assert out["files"]["main.py"] == "print(1)"


@pytest.mark.asyncio
async def test_execute_critical_block_on_spec_echo(tmp_path):
    proof = tmp_path / "proof" / "ELITE_EXECUTION_DIRECTIVE.md"
    proof.parent.mkdir(parents=True)
    proof.write_text("x", encoding="utf-8")

    class FakeLLM:
        async def chat(self, **kwargs):
            return 'const goal = "I MADE IT MORE DIFFICULT'

    agent = BuilderAgent(llm_client=FakeLLM(), config={})
    out = await agent.execute({"workspace_path": str(tmp_path), "goal": "build"})
    assert out.get("status") == "❌ CRITICAL BLOCK"
    assert "echoed spec" in out.get("reason", "").lower() or "spec" in out.get("reason", "").lower()
