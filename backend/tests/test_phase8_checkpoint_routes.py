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
