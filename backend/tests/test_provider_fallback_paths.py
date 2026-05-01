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


@pytest.mark.asyncio
async def test_explicit_dict_model_chain_bypasses_router(monkeypatch):
    """Swarm / _get_model_chain pass Cerebras-first dicts; router must not replace them."""
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    def _router_must_not_run(**_kwargs):
        raise AssertionError("llm_router.get_model_chain must not run when explicit chain is set")

    monkeypatch.setattr(llm_service.llm_router, "get_model_chain", _router_must_not_run)

    async def _ok_cerebras(*_args, **_kwargs):
        return "from-cerebras"

    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _ok_cerebras)

    with runtime_execution_scope(project_id="proj-explicit-1", task_id="tsk-explicit-1"):
        text, model = await llm_service._call_llm_with_fallback(
            message="generate react dashboard",
            system_message="sys",
            session_id="sess-explicit-1",
            model_chain=[
                {"provider": "cerebras", "model": "llama3.1-8b"},
                {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
            ],
            api_keys={"cerebras": "test-cerebras-key-only"},
            agent_name="Frontend Generation",
        )

    assert text == "from-cerebras"
    assert model == "cerebras/llama3.1-8b"


@pytest.mark.asyncio
async def test_explicit_chain_anthropic_credit_fail_falls_through_to_cerebras(monkeypatch):
    """Anthropic-style billing/credit errors must not stop the chain when Cerebras follows."""
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    def _router_must_not_run(**_kwargs):
        raise AssertionError("router must not run when explicit dict chain is provided")

    monkeypatch.setattr(llm_service.llm_router, "get_model_chain", _router_must_not_run)

    async def _bad_anthropic(*_a, **_kw):
        raise Exception("Anthropic API returned 402: credit balance too low")

    async def _ok_cerebras(*_a, **_kw):
        return "cerebras-recovered"

    monkeypatch.setattr(llm_service, "_call_anthropic_direct", _bad_anthropic)
    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _ok_cerebras)

    with runtime_execution_scope(project_id="proj-anth-fail-cb", task_id="tsk-anth-fail-cb"):
        text, model = await llm_service._call_llm_with_fallback(
            message="ship dashboard",
            system_message="sys",
            session_id="sess-anth-fail-cb",
            model_chain=[
                {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
                {"provider": "cerebras", "model": "llama3.1-8b"},
            ],
            api_keys={"anthropic": "test-anthropic", "cerebras": "test-cerebras"},
            agent_name="Frontend Generation",
        )

    assert text == "cerebras-recovered"
    assert model.startswith("cerebras/")


@pytest.mark.asyncio
async def test_workspace_cerebras_key_used_without_env_key(monkeypatch):
    """Cerebras calls must use api_keys.cerebras when env pool is empty."""
    from services import llm_service
    from services.runtime.execution_context import runtime_execution_scope

    def _router_must_not_run(**_kwargs):
        raise AssertionError("router must not run when explicit dict chain is provided")

    monkeypatch.setattr(llm_service.llm_router, "get_model_chain", _router_must_not_run)
    monkeypatch.setattr(llm_service, "_get_cerebras_key", lambda: "")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    captured: dict = {}

    async def _capture_cerebras(*_a, api_key=None, **_kw):
        captured["api_key"] = api_key
        return "ok-ws-key"

    monkeypatch.setattr(llm_service, "_call_cerebras_direct", _capture_cerebras)

    with runtime_execution_scope(project_id="proj-ws-cb", task_id="tsk-ws-cb"):
        text, model = await llm_service._call_llm_with_fallback(
            message="fix button",
            system_message="sys",
            session_id="sess-ws-cb",
            model_chain=[{"provider": "cerebras", "model": "llama3.1-8b"}],
            api_keys={"cerebras": "workspace-only-secret"},
            agent_name="Design Agent",
        )

    assert text == "ok-ws-key"
    assert captured.get("api_key") == "workspace-only-secret"
    assert model == "cerebras/llama3.1-8b"
