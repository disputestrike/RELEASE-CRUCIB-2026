from __future__ import annotations

from types import SimpleNamespace

import pytest


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_get_latest_thread_checkpoint_returns_resume_state(monkeypatch):
    from routes import artifacts as route

    class _AgentLoop:
        async def load_checkpoint(self, *, thread_id, db):
            return {
                "id": "cp-1",
                "thread_id": thread_id,
                "phase": "execute",
                "status": "saved",
                "created_at": "2026-04-20T00:00:00Z",
                "checkpoint_data": {"run_id": "run-1", "phase": "execute"},
            }

    async def _get_db():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_db=_get_db))
    monkeypatch.setitem(__import__("sys").modules, "services.agent_loop", SimpleNamespace(agent_loop=_AgentLoop()))

    out = await route.get_latest_thread_checkpoint("thread-1", user={"id": "u1"})
    assert out["thread_id"] == "thread-1"
    assert out["checkpoint"]["id"] == "cp-1"
    assert out["resume_state"]["run_id"] == "run-1"
    assert out["resume_state"]["phase"] == "execute"


@pytest.mark.asyncio
async def test_resume_thread_returns_resume_state(monkeypatch):
    from routes import artifacts as route

    class _AgentLoop:
        async def load_checkpoint(self, *, thread_id, db):
            return {
                "id": "cp-2",
                "thread_id": thread_id,
                "phase": "test",
                "status": "saved",
                "checkpoint_data": {"run_id": "run-2", "phase": "test"},
            }

        async def resume(self, run_id):
            return {"run_id": run_id, "status": "resumed"}

    async def _get_db():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_db=_get_db))
    monkeypatch.setitem(__import__("sys").modules, "services.agent_loop", SimpleNamespace(agent_loop=_AgentLoop()))

    out = await route.resume_thread("thread-2", _FakeRequest({}), user={"id": "u2"})
    assert out["thread_id"] == "thread-2"
    assert out["resume_state"]["run_id"] == "run-2"
    assert out["resume_state"]["status"] == "resumed"


@pytest.mark.asyncio
async def test_get_latest_thread_checkpoint_none(monkeypatch):
    from routes import artifacts as route

    class _AgentLoop:
        async def load_checkpoint(self, *, thread_id, db):
            return None

    async def _get_db():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_db=_get_db))
    monkeypatch.setitem(__import__("sys").modules, "services.agent_loop", SimpleNamespace(agent_loop=_AgentLoop()))

    out = await route.get_latest_thread_checkpoint("thread-empty", user={"id": "u3"})
    assert out["thread_id"] == "thread-empty"
    assert out["checkpoint"] is None


@pytest.mark.asyncio
async def test_get_thread_memory_summary_uses_checkpoint_run_id(monkeypatch):
    from routes import artifacts as route

    class _AgentLoop:
        async def load_checkpoint(self, *, thread_id, db):
            return {
                "id": "cp-3",
                "thread_id": thread_id,
                "checkpoint_data": {"run_id": "run-3", "phase": "execute"},
            }

    async def _get_db():
        return object()

    def _query_nodes(project_id, *, task_id=None, node_type=None, tag=None, limit=50):
        assert task_id == "run-3"
        return [
            {
                "id": "n1",
                "type": "step_result",
                "tags": ["step", "run-3"],
                "payload": {"step_id": "run-3-step-1", "skill": "build", "provider": {"alias": "haiku"}, "success": True},
                "ts": 1.0,
            },
            {
                "id": "n2",
                "type": "step_result",
                "tags": ["step", "run-3", "provider:haiku"],
                "payload": {"step_id": "run-3-step-2", "skill": "build", "provider": {"alias": "haiku"}, "success": False},
                "ts": 2.0,
            }
        ]

    def _get_graph(project_id):
        return {"nodes": {"n1": {}}, "edges": [{"from": "n1", "to": "n1", "relation": "next_step"}]}

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_db=_get_db))
    monkeypatch.setitem(__import__("sys").modules, "services.agent_loop", SimpleNamespace(agent_loop=_AgentLoop()))
    monkeypatch.setitem(
        __import__("sys").modules,
        "services.runtime.memory_graph",
        SimpleNamespace(query_nodes=_query_nodes, get_graph=_get_graph),
    )

    out = await route.get_thread_memory_summary("thread-3", limit=25, user={"id": "u3"})
    assert out["thread_id"] == "thread-3"
    summary = out["summary"]
    assert summary["run_id"] == "run-3"
    assert summary["node_count"] == 2
    assert summary["edge_count"] == 1
    assert summary["recent"][0]["provider"] == "haiku"
    assert summary["top_skills"][0]["name"] == "build"
    assert summary["top_skills"][0]["count"] == 2
    assert summary["top_providers"][0]["name"] == "haiku"
    assert summary["state_timeline"][0]["state"] in {"failed", "succeeded", "unknown"}


@pytest.mark.asyncio
async def test_get_thread_memory_summary_without_checkpoint(monkeypatch):
    from routes import artifacts as route

    class _AgentLoop:
        async def load_checkpoint(self, *, thread_id, db):
            return None

    async def _get_db():
        return object()

    monkeypatch.setitem(__import__("sys").modules, "db_pg", SimpleNamespace(get_db=_get_db))
    monkeypatch.setitem(__import__("sys").modules, "services.agent_loop", SimpleNamespace(agent_loop=_AgentLoop()))

    out = await route.get_thread_memory_summary("thread-empty", user={"id": "u4"})
    summary = out["summary"]
    assert summary["run_id"] is None
    assert summary["node_count"] == 0
    assert summary["edge_count"] == 0
    assert summary["top_skills"] == []
    assert summary["top_providers"] == []
    assert summary["state_timeline"] == []
