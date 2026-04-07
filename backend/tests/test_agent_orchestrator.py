"""Crew orchestrator stubs."""
import os
import tempfile

import pytest

from orchestration.agent_orchestrator import architect_crew, run_crew_for_goal


@pytest.mark.asyncio
async def test_architect_crew_kickoff():
    crew = architect_crew("build a todo app")
    r = await crew.kickoff({"goal": "todo"})
    assert "context" in r
    assert "architecture" in r["context"]
    assert "schema" in r["context"]
    assert "openapi" in r["context"]


@pytest.mark.asyncio
async def test_run_crew_writes_files():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs"), exist_ok=True)
        out = await run_crew_for_goal("simple SaaS with Postgres", d)
        assert not out.get("skipped")
        assert "docs/CREW_ARCHITECTURE.md" in out["written"]
        assert "db/migrations/000_crew_schema.sql" in out["written"]
        assert "docs/CREW_OPENAPI_SKETCH.md" in out["written"]


@pytest.mark.asyncio
async def test_run_crew_writes_elite_proof_when_system_prompt_set():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs"), exist_ok=True)
        out = await run_crew_for_goal(
            "simple SaaS with Postgres",
            d,
            system_prompt="# Elite directive\n\nDo the right thing.\n",
        )
        assert not out.get("skipped")
        assert "proof/ELITE_EXECUTION_DIRECTIVE.md" in out["written"]
        proof = open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), encoding="utf-8").read()
        assert "SHA256 prefix" in proof
        assert "Elite directive" in proof


@pytest.mark.asyncio
async def test_real_agent_only_blocks_stub_execute():
    crew = architect_crew("x")
    os.environ["CRUCIBAI_REAL_AGENT_ONLY"] = "1"
    try:
        with pytest.raises(RuntimeError, match="stubbed"):
            await crew.kickoff({"goal": "x"})
    finally:
        os.environ.pop("CRUCIBAI_REAL_AGENT_ONLY", None)


@pytest.mark.asyncio
async def test_run_crew_system_prompt_reaches_agent_execute_digest():
    """Execution path: kickoff passes elite_system_prompt so stub Agent echoes authority."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs"), exist_ok=True)
        marker = "ELITE_PAYLOAD_MARKER_9f2a"
        crew_pack = await run_crew_for_goal(
            "simple SaaS with Postgres",
            d,
            system_prompt=f"# Directive\n\n{marker}\n",
        )
        final = (crew_pack.get("crew") or {}).get("final") or []
        assert final, "crew should produce agent outputs"
        joined = "\n".join((x.get("content") or "") for x in final)
        assert marker in joined
        assert "Execution authority digest" in joined
