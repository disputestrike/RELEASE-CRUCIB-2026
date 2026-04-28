from __future__ import annotations

import os

import pytest


@pytest.mark.asyncio
async def test_chat_fused_execution_path_smoke(monkeypatch):
    from backend.routes import chat as route
    from backend.services import llm_service
    from backend.services.brain_layer import BrainLayer
    from backend.services.events import event_bus
    from backend.services.runtime.task_manager import task_manager
    from backend.tool_executor import execute_tool

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    monkeypatch.setenv("RUN_IN_SANDBOX", "0")

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(event_bus, "emit", _emit)

    # Deterministic provider chain + successful provider call
    monkeypatch.setattr(
        llm_service.llm_router,
        "get_model_chain",
        lambda **_: [("haiku", "claude-haiku", "anthropic")],
    )
    monkeypatch.setattr(llm_service.llm_router, "haiku_available", True)

    async def _ok_llm(*_args, **_kwargs):
        return "llm-ok"

    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _ok_llm)

    class _FakeAgent:
        async def run(self, context):
            text, model_used = await llm_service._call_llm_with_fallback(
                message=context.get("user_prompt", ""),
                system_message="system",
                session_id=context.get("session_context", {}).get("session_id", "sess"),
                model_chain=[],
                agent_name="FakeAgent",
            )
            tool_res = execute_tool(
                project_id=context.get("project_id", "proj-fused"),
                tool_name="run",
                params={"command": ["python", "--version"], "skill": "/commit"},
            )
            return {"llm": text, "model": model_used, "tool": tool_res}

    def _assess(_self, _session, _message):
        return {
            "assistant_response": "planned",
            "suggestions": ["next"],
            "intent": "generation",
            "intent_confidence": 0.9,
            "routing": {"intent": "generation"},
            "selected_agents": ["FakeAgent"],
            "selected_agent_configs": [{"agent": "FakeAgent", "params": {}}],
            "status": "ready",
        }

    monkeypatch.setattr(BrainLayer, "assess_request", _assess)
    monkeypatch.setattr(BrainLayer, "_get_agent_instances", lambda _self: {"FakeAgent": _FakeAgent()})

    req = {
        "session_id": "sess-fused-1",
        "project_id": "proj-fused-1",
        "message": "run fused smoke",
    }
    response = await route.send_chat_message(req)

    assert response["session_id"] == "sess-fused-1"
    assert response["project_id"] == "proj-fused-1"
    assert response.get("task_id")
    assert response.get("task_status") == "completed"
    assert response.get("status") == "executed"

    task = task_manager.get_task("proj-fused-1", response["task_id"])
    assert task is not None
    assert task["status"] == "completed"

    event_types = [t for t, _ in emitted]
    assert "chat.request.started" in event_types
    assert "brain.assessed" in event_types
    assert "brain.execution.started" in event_types
    assert "provider.chain.selected" in event_types
    assert "provider.call.started" in event_types
    assert "provider.call.succeeded" in event_types
    assert "task.started" in event_types
    assert "task.updated" in event_types
    assert "chat.request.completed" in event_types


@pytest.mark.asyncio
async def test_cancellation_propagates_to_brain_execution(monkeypatch):
    from backend.services.brain_layer import BrainLayer
    from backend.services.conversation_manager import ContextManager
    from backend.services.runtime.task_manager import task_manager

    project_id = "proj-cancel-1"
    task = task_manager.create_task(project_id=project_id, description="cancel me")

    class _Agent1:
        async def run(self, _context):
            # Simulate external cancellation while executing first step.
            task_manager.kill_task(project_id, task["task_id"], reason="test_cancel")
            return {"step": 1}

    class _Agent2:
        async def run(self, _context):
            raise AssertionError("second agent must not run after cancellation")

    def _agents(self):
        return {"A1": _Agent1(), "A2": _Agent2()}

    monkeypatch.setattr(BrainLayer, "_get_agent_instances", _agents)
    brain = BrainLayer()

    monkeypatch.setattr(
        brain,
        "assess_request",
        lambda _session, _message: {
            "assistant_response": "planned",
            "suggestions": [],
            "intent": "generation",
            "intent_confidence": 0.9,
            "routing": {"intent": "generation"},
            "selected_agents": ["A1", "A2"],
            "selected_agent_configs": [{"agent": "A1", "params": {}}, {"agent": "A2", "params": {}}],
            "status": "ready",
        },
    )

    session = ContextManager().create_session("sess-cancel")
    out = await brain.execute_request(
        session,
        "cancel scenario",
        execution_meta={"project_id": project_id, "task_id": task["task_id"]},
    )

    assert out["status"] == "execution_cancelled"
    saved = task_manager.get_task(project_id, task["task_id"])
    assert saved and saved["status"] == "killed"
