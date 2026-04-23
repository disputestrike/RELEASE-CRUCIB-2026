from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_full_fusion_pipeline_task_tool_policy_skill_events_and_fallback(monkeypatch):
    from routes import chat as chat_route
    from services import llm_service
    from services.brain_layer import BrainLayer
    from services.events import event_bus
    from services.runtime.task_manager import task_manager
    from tool_executor import execute_tool

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    monkeypatch.setenv("RUN_IN_SANDBOX", "0")

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(event_bus, "emit", _emit)

    # Provider fallback path: first provider fails, fallback provider succeeds.
    monkeypatch.setattr(
        llm_service.llm_router,
        "get_model_chain",
        lambda **_: [
            ("cerebras", "primary-model", "cerebras"),
            ("haiku", "fallback-model", "anthropic"),
        ],
    )
    monkeypatch.setattr(llm_service.llm_router, "cerebras_available", True)
    monkeypatch.setattr(llm_service.llm_router, "haiku_available", True)
    monkeypatch.setattr(llm_service.llm_router, "llama_available", False)

    async def _fail_primary(*_args, **_kwargs):
        raise Exception("primary provider failed")

    async def _ok_fallback(*_args, **_kwargs):
        return "fallback-ok"

    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _fail_primary)
    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _ok_fallback)

    class _Agent:
        async def run(self, context):
            text, model_used = await llm_service._call_llm_with_fallback(
                message=context.get("user_prompt", ""),
                system_message="system",
                session_id=context.get("session_context", {}).get("session_id", "sess"),
                model_chain=[],
                agent_name="FusionAgent",
            )

            task_id = context.get("task_id")
            project_id = context.get("project_id")

            allowed = execute_tool(
                project_id=project_id,
                tool_name="run",
                params={
                    "command": ["python", "--version"],
                    "skill": "/commit",
                    "task_id": task_id,
                },
            )
            denied = execute_tool(
                project_id=project_id,
                tool_name="run",
                params={
                    "command": ["rm -rf /"],
                    "skill": "/commit",
                    "task_id": task_id,
                },
            )

            return {
                "llm_text": text,
                "model_used": model_used,
                "allowed_tool": allowed,
                "denied_tool": denied,
            }

    def _assess(_self, _session, _message):
        return {
            "assistant_response": "planned",
            "suggestions": [],
            "intent": "generation",
            "intent_confidence": 0.9,
            "routing": {"intent": "generation"},
            "selected_agents": ["FusionAgent"],
            "selected_agent_configs": [{"agent": "FusionAgent", "params": {}}],
            "status": "ready",
        }

    monkeypatch.setattr(BrainLayer, "assess_request", _assess)
    monkeypatch.setattr(BrainLayer, "_get_agent_instances", lambda _self: {"FusionAgent": _Agent()})

    resp = await chat_route.send_chat_message(
        {
            "session_id": "sess-fusion-full-1",
            "project_id": "proj-fusion-full-1",
            "message": "run fused flow",
        }
    )

    assert resp["status"] == "executed"
    assert resp["task_id"]
    assert resp["task_status"] == "completed"

    persisted = task_manager.get_task("proj-fusion-full-1", resp["task_id"])
    assert persisted is not None
    assert persisted["status"] == "completed"

    execution = resp["execution"]
    out = execution["agent_outputs"][0]["result"]

    # Allowed tool call succeeds and returns policy metadata.
    assert out["allowed_tool"]["success"] is True
    assert "policy" in out["allowed_tool"]
    assert out["allowed_tool"]["policy"]["mode"] in {"allow", "disabled", "fallback"}

    # Denied tool call is blocked by permission policy.
    assert out["denied_tool"]["success"] is False
    assert out["denied_tool"]["policy"]["mode"] == "deny"

    event_types = [e for e, _ in emitted]

    # Task lifecycle
    assert "task.started" in event_types
    assert "task.updated" in event_types
    assert "task_start" in event_types
    assert "task_end" in event_types

    # Brain/agent lifecycle
    assert "brain.assessed" in event_types
    assert "brain.execution.started" in event_types
    assert "brain.agent.started" in event_types
    assert "brain.agent.completed" in event_types
    assert "brain.execution.completed" in event_types

    # Provider fallback with model_call emission
    assert "provider.call.started" in event_types
    assert "provider.call.failed" in event_types
    assert "provider.call.succeeded" in event_types
    assert "model_call" in event_types

    # Tool lifecycle
    assert "tool.start" in event_types
    assert "tool.fail" in event_types
    assert "tool.finish" in event_types
    assert "tool_start" in event_types
    assert "tool_end" in event_types


@pytest.mark.asyncio
async def test_full_fusion_pipeline_task_can_be_cancelled(monkeypatch):
    from services.brain_layer import BrainLayer
    from services.conversation_manager import ContextManager
    from services.runtime.task_manager import task_manager

    project_id = "proj-fusion-cancel-1"
    t = task_manager.create_task(project_id=project_id, description="cancel pipeline")

    class _AgentOne:
        async def run(self, _context):
            task_manager.kill_task(project_id, t["task_id"], reason="test-cancel")
            await asyncio.sleep(0)
            return {"step": 1}

    class _AgentTwo:
        async def run(self, _context):
            raise AssertionError("should not execute after cancellation")

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
    monkeypatch.setattr(brain, "_get_agent_instances", lambda: {"A1": _AgentOne(), "A2": _AgentTwo()})

    session = ContextManager().create_session("sess-fusion-cancel")
    out = await brain.execute_request(
        session,
        "cancel this flow",
        execution_meta={"project_id": project_id, "task_id": t["task_id"]},
    )

    assert out["status"] == "execution_cancelled"
    saved = task_manager.get_task(project_id, t["task_id"])
    assert saved is not None
    assert saved["status"] == "killed"


@pytest.mark.asyncio
async def test_runtime_engine_spawn_agent_isolated_and_evented(monkeypatch):
    from services.runtime.runtime_engine import runtime_engine
    from services.events import event_bus

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(event_bus, "emit", _emit)

    class _SpawnAgent:
        async def run(self, context):
            assert context.get("subagent") is True
            assert context.get("workspace_dir")
            return {"ok": True, "workspace": context.get("workspace_dir")}

    class _Brain:
        def _get_agent_instances(self):
            return {"SpawnWorker": _SpawnAgent()}

    monkeypatch.setattr(runtime_engine, "_brain_factory", lambda: _Brain())

    out = await runtime_engine.spawn_agent(
        project_id="proj-spawn-1",
        task_id="tsk-spawn-1",
        parent_message="spawn task",
        agent_name="SpawnWorker",
        context={"skill": "commit"},
        depth=1,
    )

    assert out["success"] is True
    assert out.get("workspace")
    event_types = [e for e, _ in emitted]
    assert "spawn.started" in event_types
    assert "spawn.completed" in event_types
