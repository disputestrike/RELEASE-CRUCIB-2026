from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_provider_primary_failure_fallback_success(monkeypatch):
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(llm_service.event_bus, "emit", _emit)
    monkeypatch.setattr(
        llm_service.llm_router,
        "get_model_chain",
        lambda **_: [
            ("cerebras", "m-primary", "cerebras"),
            ("haiku", "m-fallback", "anthropic"),
        ],
    )
    monkeypatch.setattr(llm_service.llm_router, "cerebras_available", True)
    monkeypatch.setattr(llm_service.llm_router, "haiku_available", True)
    monkeypatch.setattr(llm_service.llm_router, "llama_available", False)

    async def _fail_primary(*_args, **_kwargs):
        raise Exception("primary failed")

    async def _ok_fallback(*_args, **_kwargs):
        return "fallback-ok"

    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _fail_primary)
    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _ok_fallback)

    with runtime_execution_scope(project_id="proj-fallback-1", task_id="tsk-fallback-1"):
        text, model = await llm_service._call_llm_with_fallback(
            message="build app",
            system_message="sys",
            session_id="sess-fb-1",
            model_chain=[],
            agent_name="Planner",
        )

    assert text == "fallback-ok"
    assert model == "haiku/m-fallback"

    event_types = [t for t, _ in emitted]
    assert "provider.chain.selected" in event_types
    assert "provider.call.started" in event_types
    assert "provider.call.failed" in event_types
    assert "provider.call.succeeded" in event_types


@pytest.mark.asyncio
async def test_provider_total_failure_path(monkeypatch):
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    emitted = []

    def _emit(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(llm_service.event_bus, "emit", _emit)
    monkeypatch.setattr(
        llm_service.llm_router,
        "get_model_chain",
        lambda **_: [
            ("cerebras", "m-primary", "cerebras"),
            ("haiku", "m-fallback", "anthropic"),
        ],
    )
    monkeypatch.setattr(llm_service.llm_router, "cerebras_available", True)
    monkeypatch.setattr(llm_service.llm_router, "haiku_available", True)
    monkeypatch.setattr(llm_service.llm_router, "llama_available", False)

    async def _fail(*_args, **_kwargs):
        raise Exception("all failed")

    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _fail)
    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _fail)

    with pytest.raises(Exception):
        with runtime_execution_scope(project_id="proj-fallback-2", task_id="tsk-fallback-2"):
            await llm_service._call_llm_with_fallback(
                message="build app",
                system_message="sys",
                session_id="sess-fb-2",
                model_chain=[],
                agent_name="Planner",
            )

    event_types = [t for t, _ in emitted]
    assert "provider.chain.selected" in event_types
    assert "provider.call.failed" in event_types
    assert "provider.call.succeeded" not in event_types
