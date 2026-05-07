"""Tests for multi-turn workspace tool loop (runtime_engine + server swarm hook)."""

from unittest.mock import AsyncMock

import pytest

from backend.orchestration.runtime_engine import extract_final_assistant_text


def test_runtime_advertises_claude_code_tool_names():
    from backend.orchestration import runtime_engine as re

    names = {tool["name"] for tool in re.TOOL_DEFINITIONS}
    assert {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}.issubset(names)
    assert "read_file" not in names
    assert "run_command" not in names


@pytest.mark.asyncio
async def test_extract_final_assistant_text_prefers_last_assistant():
    messages = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "first"},
                {"type": "tool_use", "id": "x", "name": "list_files", "input": {}},
            ],
        },
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "[]"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "final answer"}]},
    ]
    assert extract_final_assistant_text(messages) == "final answer"


@pytest.mark.asyncio
async def test_run_agent_loop_two_turns_tool_then_text(tmp_path):
    from backend.orchestration import runtime_engine as re

    responses = iter(
        [
            {
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "list_files",
                        "input": {"subdir": ""},
                    }
                ],
            },
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "Listed workspace."}],
            },
        ]
    )

    async def fake_llm(messages, system, tools, thinking=None):
        return next(responses)

    out = await re.run_agent_loop(
        agent_name="Test Agent",
        system_prompt="You are a test agent.",
        user_message="Inspect the workspace.",
        workspace_path=str(tmp_path),
        call_llm=fake_llm,
        max_iterations=8,
    )

    assert out["iterations"] == 2
    assert extract_final_assistant_text(out["messages"]) == "Listed workspace."


@pytest.mark.asyncio
async def test_run_agent_loop_executes_claude_code_named_tools(tmp_path):
    from backend.orchestration import runtime_engine as re

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("export default function App() { return null; }\n", encoding="utf-8")

    events = []

    async def on_event(event_type, payload):
        events.append((event_type, payload))

    responses = iter(
        [
            {
                "stop_reason": "tool_use",
                "content": [
                    {"type": "tool_use", "id": "read_1", "name": "Read", "input": {"file_path": "src/App.tsx"}},
                    {"type": "tool_use", "id": "grep_1", "name": "Grep", "input": {"pattern": "export", "path": "src"}},
                ],
            },
            {
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "edit_1",
                        "name": "Edit",
                        "input": {
                            "file_path": "src/App.tsx",
                            "old_string": "return null",
                            "new_string": "return <main>Built</main>",
                        },
                    }
                ],
            },
            {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Edited workspace."}]},
        ]
    )

    async def fake_llm(messages, system, tools, thinking=None):
        assert {tool["name"] for tool in tools} >= {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}
        return next(responses)

    out = await re.run_agent_loop(
        agent_name="GenerateAgent",
        system_prompt="sys",
        user_message="task",
        workspace_path=str(tmp_path),
        call_llm=fake_llm,
        max_iterations=5,
        on_event=on_event,
    )

    assert out["iterations"] == 3
    assert "return <main>Built</main>" in (tmp_path / "src" / "App.tsx").read_text(encoding="utf-8")
    assert any(payload.get("name") == "Read" for kind, payload in events if kind == "tool_call")
    assert any(payload.get("name") == "Edit" for kind, payload in events if kind == "tool_result")


@pytest.mark.asyncio
async def test_run_agent_loop_accumulates_anthropic_usage(tmp_path):
    from backend.orchestration import runtime_engine as re

    responses = iter(
        [
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        ]
    )

    async def fake_llm(messages, system, tools, thinking=None):
        return next(responses)

    out = await re.run_agent_loop(
        agent_name="planner",
        system_prompt="sys",
        user_message="task",
        workspace_path=str(tmp_path),
        call_llm=fake_llm,
        max_iterations=4,
    )
    assert out.get("usage") == {"input_tokens": 100, "output_tokens": 50}


@pytest.mark.asyncio
async def test_run_single_agent_with_context_tool_loop_when_workspace_and_key(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")

    from backend import server
    from backend.orchestration import runtime_engine as re

    monkeypatch.setattr(server, "REAL_AGENT_NAMES", set())
    monkeypatch.setattr(server, "persist_agent_output", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "run_agent_real_behavior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        server,
        "run_real_post_step",
        AsyncMock(side_effect=lambda agent_name, project_id, previous_outputs, result: result),
    )
    monkeypatch.setattr(server, "_init_agent_learning", AsyncMock(return_value=None))

    async def fake_loop(**kwargs):
        return {
            "agent_name": kwargs.get("agent_name"),
            "iterations": 1,
            "files_written": [],
            "elapsed_seconds": 0.01,
            "usage": {"input_tokens": 400, "output_tokens": 100},
            "messages": [
                {"role": "user", "content": kwargs.get("user_message", "")},
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "tool-loop-output"}],
                },
            ],
        }

    monkeypatch.setattr(re, "run_agent_loop", fake_loop)
    monkeypatch.setattr(
        server,
        "_call_llm_with_fallback",
        AsyncMock(side_effect=AssertionError("single-shot LLM should not run")),
    )

    result = await server._run_single_agent_with_context(
        project_id="proj-ws",
        user_id="user-1",
        agent_name="Planner",
        project_prompt="Build something",
        previous_outputs={},
        effective={"anthropic": "sk-test"},
        model_chain=[{"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}],
        build_kind="fullstack",
        workspace_path=str(tmp_path),
    )

    assert result["status"] == "completed"
    assert result["output"] == "tool-loop-output"
    assert result["tokens_used"] == 500
    assert result.get("anthropic_usage") == {"input_tokens": 400, "output_tokens": 100}
    assert result.get("tool_loop") is True
    assert result.get("tool_loop_iterations") == 1


@pytest.mark.asyncio
async def test_run_single_agent_skips_tool_loop_without_workspace(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_DEV", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")

    from backend import server
    from backend.orchestration import runtime_engine as re

    monkeypatch.setattr(server, "REAL_AGENT_NAMES", set())
    monkeypatch.setattr(server, "persist_agent_output", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "run_agent_real_behavior", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        server,
        "run_real_post_step",
        AsyncMock(side_effect=lambda agent_name, project_id, previous_outputs, result: result),
    )
    monkeypatch.setattr(server, "_init_agent_learning", AsyncMock(return_value=None))

    monkeypatch.setattr(
        re,
        "run_agent_loop",
        AsyncMock(side_effect=AssertionError("tool loop should not run without workspace")),
    )
    monkeypatch.setattr(
        server,
        "_call_llm_with_fallback",
        AsyncMock(return_value=("Planner output", {})),
    )

    result = await server._run_single_agent_with_context(
        project_id="proj-1",
        user_id="user-1",
        agent_name="Planner",
        project_prompt="Build something",
        previous_outputs={},
        effective={"anthropic": "sk-test"},
        model_chain=[{"provider": "anthropic", "model": "claude-sonnet"}],
        build_kind="fullstack",
        workspace_path="",
    )

    assert result["output"] == "Planner output"


@pytest.mark.asyncio
async def test_run_agent_loop_run_command_allowlisted(tmp_path, monkeypatch):
    """run_command invokes allowlisted argv and attaches output to transcript."""

    monkeypatch.setenv("CRUCIB_SWARM_CMD_TIMEOUT_S", "30")

    from backend.orchestration import runtime_engine as re

    responses = iter(
        [
            {
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_rc",
                        "name": "run_command",
                        "input": {"argv": ["python", "--version"]},
                    },
                ],
            },
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "Got command output."}],
            },
        ]
    )

    async def fake_llm(messages, system, tools, thinking=None):
        return next(responses)

    out = await re.run_agent_loop(
        agent_name="Test Runner",
        system_prompt="You test builds.",
        user_message="Check Python version.",
        workspace_path=str(tmp_path),
        call_llm=fake_llm,
        max_iterations=8,
    )

    assert out["iterations"] == 2
    transcript = repr(out["messages"])
    assert "exit_code=" in transcript or "[stdout]" in transcript
    assert re.extract_final_assistant_text(out["messages"]) == "Got command output."
