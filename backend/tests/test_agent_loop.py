"""
Tests for the agentic tool-using loop.

Covers:
  1.  Tool partitioning — read-only tools identified correctly
  2.  WORKSPACE_TOOLS_FOR_AGENTS definitions
  3.  _execute_workspace_tool_sync — each action dispatches to execute_tool
  4.  edit_file miss → error; edit_file hit → success
  5.  _call_llm_with_tools_loop — end_turn on first response (no tools used)
  6.  _call_llm_with_tools_loop — write_file call then end_turn
  7.  _call_llm_with_tools_loop — max_turns safety cap
  8.  _call_llm_with_tools_loop — tool error fed back as is_error=True
  9.  _call_llm_with_tools_loop — concurrent reads all resolved
  10. _call_llm_with_tools_loop — HTTP error breaks loop cleanly
  11. RuntimeEngine.run_task_loop — returns execution_completed
  12. RuntimeEngine.run_task_loop — brain.decide called with right message
  13. RuntimeEngine.run_task_loop — clarification_required propagated
  14. RuntimeEngine.run_task_loop — brain.decide failure → execution_failed
  15. RuntimeEngine.run_task_loop — agent exception recorded in result
  16. RuntimeEngine.run_task_loop — multiple agents all called
  17. RuntimeEngine.run_task_loop — no longer returns the old mock string
"""

from __future__ import annotations

import asyncio
import json
import re
import textwrap
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys

# ═══════════════════════════════════════════════════════════════════════════
# Dependency stubs — set up BEFORE any project code is imported
# ═══════════════════════════════════════════════════════════════════════════

def _stub(name: str, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# httpx — preserve the real module; only add AsyncClient shim if missing
# so that other test files that import httpx still get the real package.
try:
    import httpx as _real_httpx
    if not hasattr(_real_httpx, "AsyncClient"):
        _real_httpx.AsyncClient = object
    httpx_mod = _real_httpx
except ImportError:
    httpx_mod = _stub("httpx", AsyncClient=object)

# project_state
_stub("backend.project_state",
      WORKSPACE_ROOT=__import__("pathlib").Path("/tmp/test_ws"),
      DEFAULT_STATE={},
      load_state=lambda *a, **kw: {},
      save_state=lambda *a, **kw: None,
      update_state=lambda *a, **kw: {})

# anthropic_models
_stub(
    "backend.anthropic_models",
    ANTHROPIC_HAIKU_MODEL="claude-haiku-4-5-20251001",
    ANTHROPIC_SONNET_MODEL="claude-sonnet-4-6",
    normalize_anthropic_model=lambda m, default=None: m or default,
)

# execution_context — ALL names that execution_authority.py imports
from contextlib import contextmanager

@contextmanager
def _fake_scope(**_kw):
    yield

_stub(
    "backend.services.runtime.execution_context",
    runtime_execution_scope=_fake_scope,
    current_project_id=lambda: None,
    current_task_id=lambda: None,
    current_skill_hint=lambda: None,
)

# tool_executor — injectable fake results
_FAKE_TOOL_RESULTS: dict = {}

def _fake_execute_tool(project_id, tool_name, params):
    key = (tool_name, params.get("action", ""), params.get("path", ""))
    return _FAKE_TOOL_RESULTS.get(key, {"success": True, "output": f"ok:{tool_name}"})

_stub("backend.tool_executor", execute_tool=_fake_execute_tool)

# memory_graph
_stub("backend.services.runtime.memory_graph",
      add_node=lambda *a, **kw: None,
      add_edge=lambda *a, **kw: None,
      get_graph=lambda *a, **kw: {})

# event_bus
class _FakeBus:
    def emit(self, *a, **kw): pass

# Make backend.services.events a package-like stub so sub-imports work
_events_stub = _stub("backend.services.events", event_bus=_FakeBus())
_events_stub.__path__ = []  # marks it as a package
_events_stub.__package__ = "backend.services.events"
# Pre-stub the sub-modules server.py imports from backend.services.events
_stub("backend.services.events.persistent_sink",
      read_events=lambda *a, **kw: [])

# ═══════════════════════════════════════════════════════════════════════════
# Load server.py helpers via exec (avoids the full FastAPI import chain)
# ═══════════════════════════════════════════════════════════════════════════

def _load_server_helpers() -> dict:
    server_path = "/tmp/crucibai_repo/backend/server.py"
    with open(server_path) as f:
        src = f.read()
    start = src.find("_READONLY_TOOLS: frozenset")
    end   = src.find("async def _run_single_agent_with_context(")
    assert start != -1 and end != -1, "Agentic-loop section not found in server.py"
    snippet = src[start:end]
    ns: dict = {
        "__builtins__": __builtins__,
        "logging":  __import__("logging"),
        "asyncio":  asyncio,
        "os":       __import__("os"),
        "json":     json,
        "Path":     __import__("pathlib").Path,
        "List":     list,
        "Dict":     dict,
        "Any":      object,
        "Optional": type(None),
        "Tuple":    tuple,
        "subprocess": __import__("subprocess"),
    }
    exec(compile(snippet, "<server_loop_helpers>", "exec"), ns)
    return ns

_NS = _load_server_helpers()

_READONLY_TOOLS  = _NS["_READONLY_TOOLS"]
_exec_sync       = _NS["_execute_workspace_tool_sync"]
_exec_async      = _NS["_execute_workspace_tool_async"]
_call_loop       = _NS["_call_llm_with_tools_loop"]
WORKSPACE_TOOLS  = _NS["WORKSPACE_TOOLS_FOR_AGENTS"]


# ═══════════════════════════════════════════════════════════════════════════
# Load RuntimeEngine.run_task_loop via exec (class body only, lines 142-458)
# ═══════════════════════════════════════════════════════════════════════════

def _load_runtime_engine_class(brain_mock) -> object:
    """
    Exec only the RuntimeEngine class body from runtime_engine.py,
    inject all deps as globals, return an instance with brain wired in.
    """
    with open("/tmp/crucibai_repo/backend/services/runtime/runtime_engine.py") as f:
        lines = f.readlines()
    # Detect RuntimeEngine class boundaries dynamically (line numbers shift as code grows)
    start_idx = next(
        i for i, l in enumerate(lines) if l.startswith("class RuntimeEngine:")
    )
    end_idx = next(
        i for i, l in enumerate(lines) if l.startswith("runtime_engine = RuntimeEngine()")
    )
    class_src = "".join(lines[start_idx:end_idx])

    class _EC:
        def __init__(self, task_id="", user_id="", conversation_id=None,
                     project_id=None, **kw):
            self.task_id = task_id
            self.executed_steps = []
        def add_step(self, s):
            self.executed_steps.append(s)

    _fake_eb = type("EB", (), {"emit": staticmethod(lambda *a, **kw: None)})()

    ns = {
        "__builtins__":             __builtins__,
        "asyncio":                  asyncio,
        "logging":                  __import__("logging"),
        "uuid":                     __import__("uuid"),
        "time":                     __import__("time"),
        "os":                       __import__("os"),
        "json":                     json,
        "traceback":                __import__("traceback"),
        "datetime":                 __import__("datetime").datetime,
        "Path":                     __import__("pathlib").Path,
        "Optional":                 type(None),
        "List":                     list,
        "Dict":                     dict,
        "Any":                      object,
        "Callable":                 type(lambda: None),
        "dataclass":                __import__("dataclasses").dataclass,
        "field":                    __import__("dataclasses").field,
        "Enum":                     __import__("enum").Enum,
        "ExecutionPhase":           type("ExecutionPhase", (), {}),
        "ExecutionState":           type("ExecutionState", (), {}),
        "ExecutionContext":          _EC,
        "event_bus":                _fake_eb,
        "memory_add_node":          lambda *a, **kw: None,
        "memory_add_edge":          lambda *a, **kw: None,
        "logger":                   __import__("logging").getLogger("test_engine"),
        "runtime_execution_scope":  _fake_scope,
        "runtime_context_manager":  type("CM", (), {"update": lambda *a,**kw: None})(),
        "spawn_engine":             type("SE", (), {"spawn":  lambda *a,**kw: None})(),
        "resolve_skill":            lambda *a, **kw: None,
        "list_skills":              lambda *a, **kw: [],
        "get_skill":                lambda *a, **kw: None,
        "task_workspace":           lambda *a, **kw: "/tmp",
        "cost_tracker":             type("CT", (), {"record": lambda *a,**kw: None})(),
        "evaluate_tool_call":       lambda *a, **kw: True,
        "require_runtime_authority": lambda *a, **kw: None,
        "runtime_authority_snapshot": type("S", (), {
            "set_current_snapshot": lambda *a, **kw: None
        })(),
        "ConversationSession":      type("CS", (), {"__init__": lambda s,**kw: None}),
        "task_manager":             type("TM", (), {
            "create_task":   lambda *a,**kw: {"task_id": "t1"},
            "complete_task": lambda *a,**kw: None,
            "fail_task":     lambda *a,**kw: None,
            "kill_task":     lambda *a,**kw: None,
            "get_task":      lambda *a,**kw: {"status": "completed"},
        })(),
        "classifier":               type("C",  (), {"classify": lambda *a,**kw: {}})(),
        "llm_router":               type("LR", (), {"route":    lambda *a,**kw: {}})(),
        "BrainLayer":               lambda *a,**kw: brain_mock,
        "execute_tool":             lambda *a,**kw: {"success": True},
        "memory_store":             None,
        "MemoryScope":              None,
        "capability_inspector":     None,
        "WORKSPACE_ROOT":           "/tmp",
        "_classify_agent_failure":  lambda exc: (
            "timeout" if "timeout" in str(exc).lower() else
            "network" if "network" in str(exc).lower() else
            "unknown"
        ),
    }
    exec(compile(class_src, "<RuntimeEngine>", "exec"), ns)
    engine = ns["RuntimeEngine"]()
    engine._brain_factory = lambda: brain_mock
    return engine


def _make_brain(intent="generation", agents=None, status="ready",
                exec_result=None):
    brain = MagicMock()
    _agents = agents or ["FrontendAgent"]
    if exec_result is None:
        exec_result = {"status": "executed",
                       "execution": {"success": True, "result": "built"}}
    brain.decide.return_value = {
        "intent":                intent,
        "selected_agents":       _agents,
        "selected_agent_configs": [
            {"agent": a, "params": {}} for a in _agents
        ],
        "status":                status,
        "assistant_response":    "I'll build this for you.",
    }
    brain.execute_request = AsyncMock(return_value=exec_result)

    # New run_task_loop interface: dispatch via agent instances
    class _FakeAgent:
        def __init__(self, name, exc=None):
            self._name = name
            self._exc = exc
        async def run(self, ctx):
            await brain.execute_request(ctx.get("message", ""), ctx)
            if self._exc:
                raise self._exc
            return exec_result

    _inst = {a: _FakeAgent(a) for a in _agents}
    brain._get_agent_instances = lambda: _inst
    brain._build_agent_context = lambda cfg, msg, sess, extra: {**cfg, **extra, "message": msg}
    brain._summarize_execution  = lambda plan, execution: "done"
    return brain


def _make_session():
    s = MagicMock()
    s.session_id = "sess-test"
    s.user_id    = "user-test"
    s.get_context_enrichment.return_value = {}
    s.keywords   = []
    return s


# ═══════════════════════════════════════════════════════════════════════════
# Fake httpx helpers
# ═══════════════════════════════════════════════════════════════════════════

class _FakeResp:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body       = body
        self.text        = ""
    def json(self) -> dict:
        return self._body


class _FakeClient:
    def __init__(self, responses: list):
        self._iter = iter(responses)
    async def __aenter__(self):
        return self
    async def __aexit__(self, *_):
        pass
    async def post(self, *_a, **_kw):
        return next(self._iter)


def _patch_httpx(responses: list):
    return patch("httpx.AsyncClient", return_value=_FakeClient(responses))


def _end_turn(text="done") -> _FakeResp:
    return _FakeResp(200, {
        "stop_reason": "end_turn",
        "content":     [{"type": "text", "text": text}],
    })


def _tool_use(calls: list) -> _FakeResp:
    return _FakeResp(200, {"stop_reason": "tool_use", "content": calls})


# ═══════════════════════════════════════════════════════════════════════════
# Test classes
# ═══════════════════════════════════════════════════════════════════════════

class TestReadonlyToolSet(unittest.TestCase):
    def test_contains_expected(self):
        self.assertEqual(_READONLY_TOOLS, frozenset({"read_file","list_files","search_files"}))
    def test_write_not_readonly(self):
        self.assertNotIn("write_file", _READONLY_TOOLS)
    def test_run_not_readonly(self):
        self.assertNotIn("run_command", _READONLY_TOOLS)
    def test_edit_not_readonly(self):
        self.assertNotIn("edit_file", _READONLY_TOOLS)


class TestWorkspaceToolDefs(unittest.TestCase):
    def test_six_tools(self):
        self.assertEqual(len(WORKSPACE_TOOLS), 6)
    def test_all_have_required_fields(self):
        for t in WORKSPACE_TOOLS:
            self.assertIn("name",         t)
            self.assertIn("description",  t)
            self.assertIn("input_schema", t)
    def test_write_file_requires_path_content(self):
        w = next(t for t in WORKSPACE_TOOLS if t["name"] == "write_file")
        req = w["input_schema"].get("required", [])
        self.assertIn("path",    req)
        self.assertIn("content", req)
    def test_edit_file_requires_old_new(self):
        e = next(t for t in WORKSPACE_TOOLS if t["name"] == "edit_file")
        req = e["input_schema"].get("required", [])
        self.assertIn("old_text", req)
        self.assertIn("new_text", req)
    def test_run_command_array(self):
        r = next(t for t in WORKSPACE_TOOLS if t["name"] == "run_command")
        self.assertEqual(r["input_schema"]["properties"]["command"]["type"], "array")


class TestExecuteWorkspaceToolSync(unittest.TestCase):
    def setUp(self):
        _FAKE_TOOL_RESULTS.clear()
        # Set RuntimeEngine override so execute_tool_for_task uses the fake
        try:
            import backend.services.runtime.runtime_engine as _rte_mod
            _rte_mod.RuntimeEngine._execute_tool_override = staticmethod(_fake_execute_tool)
        except Exception:
            pass

    def tearDown(self):
        # Remove the override so other tests use the real execute_tool
        try:
            import backend.services.runtime.runtime_engine as _rte_mod
            _rte_mod.RuntimeEngine._execute_tool_override = None
        except Exception:
            pass

    def test_read_file(self):
        _FAKE_TOOL_RESULTS[("file","read","src/App.jsx")] = {"success":True,"output":"content"}
        r = _exec_sync("read_file", {"path":"src/App.jsx"}, "p1", "")
        self.assertTrue(r["success"])
        self.assertEqual(r["output"], "content")

    def test_write_file(self):
        _FAKE_TOOL_RESULTS[("file","write","out.js")] = {"success":True,"output":"ok"}
        r = _exec_sync("write_file", {"path":"out.js","content":"x"}, "p1", "")
        self.assertTrue(r["success"])

    def test_list_files(self):
        _FAKE_TOOL_RESULTS[("file","list","")] = {"success":True,"output":"src/"}
        r = _exec_sync("list_files", {}, "p1", "")
        self.assertTrue(r["success"])

    def test_run_command(self):
        _FAKE_TOOL_RESULTS[("run","","")] = {"success":True,"output":"passed"}
        r = _exec_sync("run_command", {"command":["npm","test"]}, "p1", "")
        self.assertTrue(r["success"])

    def test_edit_file_miss(self):
        _FAKE_TOOL_RESULTS[("file","read","f.py")] = {"success":True,"output":"hello world"}
        r = _exec_sync("edit_file", {"path":"f.py","old_text":"NONE","new_text":"x"}, "p1", "")
        self.assertFalse(r["success"])
        self.assertIn("edit_miss", r.get("error",""))

    def test_edit_file_success(self):
        _FAKE_TOOL_RESULTS[("file","read","f.py")] = {"success":True,"output":"def foo():\n    pass\n"}
        _FAKE_TOOL_RESULTS[("file","write","f.py")] = {"success":True,"output":"ok"}
        r = _exec_sync("edit_file",
            {"path":"f.py","old_text":"    pass","new_text":"    return 42"}, "p1", "")
        self.assertTrue(r["success"])

    def test_unknown_tool(self):
        r = _exec_sync("no_such_tool", {}, "p1", "")
        self.assertFalse(r["success"])
        self.assertIn("Unknown tool", r.get("output",""))


class TestCallLlmWithToolsLoop(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _FAKE_TOOL_RESULTS.clear()

    async def test_end_turn_first_response(self):
        with _patch_httpx([_end_turn("Generated code")]):
            text, meta = await _call_loop(
                message="Build a button", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=20,
            )
        self.assertEqual(text, "Generated code")
        self.assertEqual(meta["turns"], 1)
        self.assertEqual(meta["files_written"], [])

    async def test_write_file_then_end_turn(self):
        _FAKE_TOOL_RESULTS[("file","write","src/Button.jsx")] = {"success":True,"output":"ok"}
        with _patch_httpx([
            _tool_use([{"type":"tool_use","id":"t1","name":"write_file",
                        "input":{"path":"src/Button.jsx","content":"export const B = () => <b/>"}}]),
            _end_turn("Button written."),
        ]):
            text, meta = await _call_loop(
                message="Create Button", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=20,
            )
        self.assertEqual(text, "Button written.")
        self.assertEqual(meta["turns"], 2)
        self.assertIn("src/Button.jsx", meta["files_written"])

    async def test_max_turns_cap(self):
        _FAKE_TOOL_RESULTS[("file","list","")] = {"success":True,"output":"f.js"}
        looping = [_FakeResp(200,{
            "stop_reason":"tool_use",
            "content":[{"type":"tool_use","id":f"t{i}","name":"list_files","input":{}}],
        }) for i in range(10)]
        with _patch_httpx(looping):
            _, meta = await _call_loop(
                message="List", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=3,
            )
        self.assertEqual(meta["turns"], 3)

    async def test_tool_error_fed_back(self):
        _FAKE_TOOL_RESULTS[("file","read","missing.js")] = {
            "success":False,"output":"","error":"not_found"
        }
        with _patch_httpx([
            _tool_use([{"type":"tool_use","id":"tr","name":"read_file",
                        "input":{"path":"missing.js"}}]),
            _end_turn("handled"),
        ]):
            text, meta = await _call_loop(
                message="Read", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=5,
            )
        self.assertEqual(text, "handled")
        self.assertEqual(meta["turns"], 2)

    async def test_concurrent_reads_resolved(self):
        for name in ["a.js","b.js","c.js"]:
            _FAKE_TOOL_RESULTS[("file","read",name)] = {"success":True,"output":f"c_{name}"}
        with _patch_httpx([
            _tool_use([
                {"type":"tool_use","id":f"t{i}","name":"read_file","input":{"path":f"{c}.js"}}
                for i, c in enumerate(["a","b","c"])
            ]),
            _end_turn("all read"),
        ]):
            text, meta = await _call_loop(
                message="Read all", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=5,
            )
        self.assertEqual(meta["turns"], 2)
        self.assertEqual(text, "all read")

    async def test_http_error_breaks_loop(self):
        with _patch_httpx([_FakeResp(500, {})]):
            text, meta = await _call_loop(
                message="Go", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test", model="claude-haiku-4-5-20251001",
                max_turns=5,
            )
        self.assertEqual(meta["turns"], 1)
        self.assertEqual(text, "")


class TestRuntimeEngineRunTaskLoop(unittest.IsolatedAsyncioTestCase):

    async def test_returns_execution_completed(self):
        brain = _make_brain()
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="Build a login page",
            planner=brain,
        )
        self.assertEqual(result["status"], "executed")
        self.assertIn("FrontendAgent", result["selected_agents"])
        self.assertTrue(result["execution"]["success"])

    async def test_brain_decide_called_with_message(self):
        brain = _make_brain()
        engine = _load_runtime_engine_class(brain)
        session = _make_session()
        await engine.run_task_loop(
            session=session,
            project_id="proj1", task_id="task1",
            user_message="Build a dashboard",
            planner=brain,
        )
        brain.decide.assert_called_once_with(session, "Build a dashboard")

    async def test_clarification_required_propagated(self):
        brain = _make_brain(status="clarification_required")
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="?",
            planner=brain,
        )
        self.assertEqual(result["status"], "clarification_required")
        brain.execute_request.assert_not_called()

    async def test_brain_decide_failure_returns_execution_failed(self):
        brain = MagicMock()
        brain.decide.side_effect = RuntimeError("LLM timeout")
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="Build something",
            planner=brain,
        )
        self.assertEqual(result["status"], "execution_failed")
        self.assertFalse(result["execution"]["success"])
        self.assertIn("LLM timeout", result["execution"]["error"])

    async def test_agent_exception_recorded(self):
        brain = _make_brain(agents=["FailingAgent"])
        brain = _make_brain(agents=["FailingAgent"])
        _inst = brain._get_agent_instances()
        class _BoomAgent:
            async def run(self, ctx): raise Exception("agent crash")
        _inst["FailingAgent"] = _BoomAgent()
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="Do thing",
            planner=brain,
        )
        self.assertEqual(result["status"], "execution_failed")
        self.assertIn("FailingAgent", result["execution"].get("error", ""))

    async def test_multiple_agents_all_called(self):
        brain = _make_brain(agents=["PlannerAgent","FrontendAgent","BackendAgent"])
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="Build full stack app",
            planner=brain,
        )
        self.assertEqual(len(result["execution"]["agent_outputs"]), 3)
        self.assertEqual(len(result["selected_agents"]), 3)

    async def test_no_longer_returns_mock_string(self):
        brain = _make_brain()
        engine = _load_runtime_engine_class(brain)
        result = await engine.run_task_loop(
            session=_make_session(),
            project_id="proj1", task_id="task1",
            user_message="Build",
            planner=brain,
        )
        exec_result = result.get("execution", {}).get("result", "")
        self.assertNotEqual(
            exec_result, "Mocked loop result",
            "run_task_loop still returning the old stub value!"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ═══════════════════════════════════════════════════════════════════════════
# Adaptive thinking tests
# ═══════════════════════════════════════════════════════════════════════════

_THINKING_AGENTS    = _NS["_THINKING_AGENTS"]
_THINKING_CAPABLE   = _NS["_THINKING_CAPABLE_MODELS"]
_THINKING_BUDGET    = _NS["_THINKING_BUDGET_TOKENS"]


class TestThinkingAgentSet(unittest.TestCase):
    """_THINKING_AGENTS must contain the high-stakes agents and nothing trivial."""

    def test_planner_in_thinking_agents(self):
        self.assertIn("Planner", _THINKING_AGENTS)

    def test_architecture_in_thinking_agents(self):
        self.assertIn("Architecture Agent", _THINKING_AGENTS)

    def test_security_agent_in_thinking_agents(self):
        self.assertIn("Security Agent", _THINKING_AGENTS)

    def test_backend_generation_in_thinking_agents(self):
        self.assertIn("Backend Generation", _THINKING_AGENTS)

    def test_frontend_generation_in_thinking_agents(self):
        self.assertIn("Frontend Generation", _THINKING_AGENTS)

    def test_budget_is_positive_int(self):
        self.assertIsInstance(_THINKING_BUDGET, int)
        self.assertGreater(_THINKING_BUDGET, 0)

    def test_capable_models_include_sonnet(self):
        self.assertTrue(any("sonnet" in m for m in _THINKING_CAPABLE))


class TestAdaptiveThinkingLoop(unittest.IsolatedAsyncioTestCase):
    """Verify that use_thinking=True sends the right API payload."""

    def setUp(self):
        _FAKE_TOOL_RESULTS.clear()

    def _capture_client(self, responses):
        """Return a fake client that records every request body."""
        captured = []
        class _Capturing(_FakeClient):
            async def post(self, *args, **kwargs):
                captured.append(kwargs.get("json", {}))
                return await super().post(*args, **kwargs)
        return _Capturing(responses), captured

    async def test_thinking_block_sent_on_turn_1_for_capable_model(self):
        client, captured = self._capture_client([_end_turn("plan done")])
        with patch("httpx.AsyncClient", return_value=client):
            await _call_loop(
                message="Plan the app",
                system_message="You are a planner",
                project_id="p1", workspace_path="",
                api_key="sk-test",
                model="claude-sonnet-4-6",   # matches "claude-sonnet-4" prefix
                agent_name="Planner",
                use_thinking=True,
                max_turns=5,
            )
        self.assertTrue(len(captured) >= 1, "No API call was made")
        body = captured[0]
        self.assertIn("thinking", body, "thinking key missing from request body")
        self.assertEqual(body["thinking"]["type"], "enabled")
        self.assertEqual(body["thinking"]["budget_tokens"], _THINKING_BUDGET)

    async def test_max_tokens_increased_when_thinking(self):
        client, captured = self._capture_client([_end_turn("done")])
        with patch("httpx.AsyncClient", return_value=client):
            await _call_loop(
                message="Plan", system_message="Planner",
                project_id="p1", workspace_path="",
                api_key="sk-test",
                model="claude-sonnet-4-6",
                use_thinking=True,
                max_turns=1,
            )
        body = captured[0]
        self.assertGreater(
            body.get("max_tokens", 0), _THINKING_BUDGET,
            "max_tokens must exceed budget_tokens when thinking is on",
        )

    async def test_thinking_NOT_sent_for_incapable_model(self):
        """Non-Anthropic models (Cerebras, etc.) must NOT get the thinking block."""
        client, captured = self._capture_client([_end_turn("done")])
        with patch("httpx.AsyncClient", return_value=client):
            await _call_loop(
                message="Plan", system_message="Planner",
                project_id="p1", workspace_path="",
                api_key="sk-test",
                model="llama-3.3-70b",       # Cerebras model — not thinking-capable
                use_thinking=True,            # caller requested it, model can't do it
                max_turns=1,
            )
        body = captured[0]
        self.assertNotIn("thinking", body,
            "thinking key must NOT appear for non-Anthropic models")

    async def test_thinking_NOT_sent_on_turn_2(self):
        """Thinking fires only on turn 1. Subsequent turns must not include it."""
        _FAKE_TOOL_RESULTS[("file", "list", "")] = {"success": True, "output": "src/"}
        responses = [
            # Turn 1: model uses a tool
            _FakeResp(200, {
                "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "id": "t1",
                              "name": "list_files", "input": {}}],
            }),
            # Turn 2: model ends
            _end_turn("done"),
        ]
        client, captured = self._capture_client(responses)
        with patch("httpx.AsyncClient", return_value=client):
            await _call_loop(
                message="Plan", system_message="Planner",
                project_id="p1", workspace_path="",
                api_key="sk-test",
                model="claude-sonnet-4-6",
                use_thinking=True,
                max_turns=5,
            )
        self.assertEqual(len(captured), 2, "Expected exactly 2 API calls")
        self.assertIn("thinking", captured[0],   "Turn 1 must have thinking")
        self.assertNotIn("thinking", captured[1], "Turn 2 must NOT have thinking")

    async def test_thinking_false_skips_block(self):
        """use_thinking=False must produce a clean request with no thinking key."""
        client, captured = self._capture_client([_end_turn("done")])
        with patch("httpx.AsyncClient", return_value=client):
            await _call_loop(
                message="Write code", system_message="Coder",
                project_id="p1", workspace_path="",
                api_key="sk-test",
                model="claude-sonnet-4-6",
                use_thinking=False,
                max_turns=1,
            )
        body = captured[0]
        self.assertNotIn("thinking", body)
        self.assertEqual(body.get("max_tokens"), 8096)
