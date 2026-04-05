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
