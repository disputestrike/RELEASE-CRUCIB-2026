from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_llm_fallback_emits_provider_events(monkeypatch):
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(llm_service.event_bus, "emit", _emit)
    monkeypatch.setattr(
        llm_service.llm_router,
        "get_model_chain",
        lambda **_: [("haiku", "claude-haiku", "anthropic")],
    )
    monkeypatch.setattr(llm_service.llm_router, "haiku_available", True)
    monkeypatch.setattr(llm_service.llm_router, "cerebras_available", False)
    monkeypatch.setattr(llm_service.llm_router, "llama_available", False)

    async def _ok(*_args, **_kwargs):
        return "ok"

    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _ok)

    with runtime_execution_scope(project_id="proj-events", task_id="tsk-events"):
        text, model = await llm_service._call_llm_with_fallback(
            message="build a todo app",
            system_message="you are helpful",
            session_id="sess-1",
            model_chain=[],
            agent_name="Planner",
        )

    assert text == "ok"
    assert model == "haiku/claude-haiku"
    assert any(t == "provider.chain.selected" for t, _ in emitted)
    assert any(t == "provider.call.started" for t, _ in emitted)
    assert any(t == "provider.call.succeeded" for t, _ in emitted)


@pytest.mark.asyncio
async def test_brain_layer_emits_execution_events(monkeypatch):
    from services.brain_layer import BrainLayer
    from services.runtime.task_manager import task_manager

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    from services import events as events_module

    monkeypatch.setattr(events_module.event_bus, "emit", _emit)

    brain = BrainLayer()

    monkeypatch.setattr(
        brain,
        "assess_request",
        lambda _session, _message: {
            "status": "ready",
            "intent": "generation",
            "intent_confidence": 0.9,
            "assistant_response": "plan",
            "selected_agents": ["Planner"],
            "selected_agent_configs": [{"agent": "Planner", "confidence": 0.9}],
        },
    )

    class _PlannerAgent:
        async def run(self, _context):
            return {"files": ["a"]}

    monkeypatch.setattr(brain, "_get_agent_instances", lambda: {"Planner": _PlannerAgent()})

    class _Session:
        def get_context_enrichment(self):
            return {}

        keywords = []

    t = task_manager.create_task(project_id="proj-brain-events", description="build app")

    result = await brain.execute_request(
        _Session(),
        "build app",
        execution_meta={"project_id": "proj-brain-events", "task_id": t["task_id"]},
    )
    assert result["status"] == "executed"

    emitted_types = [t for t, _ in emitted]
    assert "brain.assessed" in emitted_types
    assert "brain.execution.started" in emitted_types
    assert "brain.execution.completed" in emitted_types
