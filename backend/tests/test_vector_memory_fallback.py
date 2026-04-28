"""
Full-path verification: VectorMemory must never hard-depend on Pinecone/OpenAI when keys are absent.
Covers add → retrieve → list → count → delete without external services.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def no_vector_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    from backend.memory import vector_db as vd

    vd._vector_memory = None
    yield vd
    vd._vector_memory = None


@pytest.mark.asyncio
async def test_vector_memory_in_memory_round_trip(no_vector_keys):
    from backend.memory.vector_db import VectorMemory

    vm = VectorMemory()
    assert vm.provider == "memory"

    pid = "test_project_vector_memory_round_trip"
    vid = await vm.add_memory(pid, "Ship the preview gate before Friday.", "decision", agent_name="tester", phase="plan")
    assert isinstance(vid, str) and len(vid) > 0

    matches = await vm.retrieve_context(pid, "preview gate Friday", top_k=5)
    assert isinstance(matches, list)
    assert any((m.get("text") or "").strip() for m in matches)

    recent = await vm.list_recent_context(pid, limit=10)
    assert isinstance(recent, list)
    assert len(recent) >= 1

    tokens = await vm.count_project_tokens(pid)
    assert isinstance(tokens, int) and tokens >= 0

    ok = await vm.delete_project_memory(pid)
    assert ok is True

    after = await vm.list_recent_context(pid, limit=5)
    assert after == []


@pytest.mark.asyncio
async def test_get_vector_memory_singleton(no_vector_keys):
    from backend.memory import vector_db as vd

    a = await vd.get_vector_memory()
    b = await vd.get_vector_memory()
    assert a is b
    assert a.provider == "memory"


@pytest.mark.asyncio
async def test_store_and_retrieve_helpers(no_vector_keys):
    from backend.memory import vector_db as vd

    vd._vector_memory = None
    pid = "test_helpers_project"
    await vd.store_memory(pid, "Memory line for helpers test", "note")
    rows = await vd.retrieve_memory(pid, "Memory line")
    assert isinstance(rows, list)

