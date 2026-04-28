"""WS-B smoke test for react_stream event contract."""
import asyncio
import pytest

from services.react_loop import react_stream


def _run(gen_coro):
    async def _collect():
        return [e async for e in gen_coro]
    return asyncio.run(_collect())


def test_default_stream_emits_thought_text_final():
    events = _run(react_stream("what is 1+1?"))
    kinds = [e["type"] for e in events]
    assert "thought" in kinds
    assert "text" in kinds
    assert kinds[-1] == "final"
    assert events[-1]["budget"] == 8000


def test_tool_dispatch():
    async def add(name, args):
        return args["a"] + args["b"]

    async def llm(prompt, history):
        if not history:
            return {"thought": "add first", "tool_call": {"id": "t1", "name": "add", "args": {"a": 2, "b": 3}}}
        return {"thought": "done", "final": f"answer={history[-1]['result']}"}

    events = _run(react_stream("2+3?", tools={"add": add}, llm_call=llm))
    kinds = [e["type"] for e in events]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert events[-1]["type"] == "final"
    assert "answer=5" in events[-1]["content"]
