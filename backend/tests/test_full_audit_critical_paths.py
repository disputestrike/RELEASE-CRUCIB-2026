"""
Full audit: critical paths, agent wiring, deploy readiness.
Ensures every critical piece is wired and no prompt-only agents in critical path.
"""
import pytest
from agent_dag import AGENT_DAG, get_execution_phases, get_system_prompt_for_agent
from agent_real_behavior import STATE_WRITERS, ARTIFACT_PATHS, TOOL_RUNNER_STATE_KEYS, run_agent_real_behavior
from agent_resilience import AGENT_CRITICALITY, generate_fallback, get_criticality, get_timeout
from project_state import DEFAULT_STATE, load_state, update_state


def test_dag_has_native_config_and_store_prep():
    """Mobile agents must be in DAG with real behavior."""
    assert "Native Config Agent" in AGENT_DAG
    assert "Store Prep Agent" in AGENT_DAG
    assert AGENT_DAG["Native Config Agent"]["depends_on"] == ["Stack Selector"]
    assert "Frontend Generation" in (AGENT_DAG["Store Prep Agent"]["depends_on"])
    assert "Native Config Agent" in (AGENT_DAG["Store Prep Agent"]["depends_on"])


def test_native_config_and_store_prep_have_real_behavior():
    """No prompt-only: Native Config and Store Prep must write state or artifact."""
    assert "Native Config Agent" in STATE_WRITERS
    assert "Store Prep Agent" in STATE_WRITERS
    assert "Store Prep Agent" in ARTIFACT_PATHS


def test_project_state_has_mobile_keys():
    """State schema includes native_config and store_prep."""
    assert "native_config" in DEFAULT_STATE
    assert "store_prep" in DEFAULT_STATE


def test_all_dag_agents_have_system_prompt():
    """Every agent in DAG has a non-empty system prompt (no bare stub)."""
    for name in AGENT_DAG:
        prompt = get_system_prompt_for_agent(name)
        assert prompt, f"{name} must have system_prompt"


def test_critical_agents_have_criticality_and_timeout():
    """Planner, Stack Selector, Frontend, Backend have defined criticality and timeout."""
    critical = ["Planner", "Stack Selector", "Frontend Generation", "Backend Generation"]
    for name in critical:
        assert name in AGENT_CRITICALITY, f"{name} must be in AGENT_CRITICALITY"
        assert get_timeout(name) >= 60, f"{name} must have timeout >= 60"


def test_every_agent_has_fallback():
    """generate_fallback returns non-empty string for every DAG agent."""
    for name in AGENT_DAG:
        fb = generate_fallback(name)
        assert isinstance(fb, str) and len(fb.strip()) > 0, f"{name} must have fallback"


def test_phases_include_all_agents_exactly_once():
    """Execution phases cover every agent exactly once."""
    phases = get_execution_phases(AGENT_DAG)
    all_in_phases = [a for p in phases for a in p]
    assert set(all_in_phases) == set(AGENT_DAG.keys())
    assert len(all_in_phases) == len(AGENT_DAG)


def test_real_agent_runner_imports():
    """Real agent runner and tool executor are importable (wiring exists)."""
    from real_agent_runner import REAL_AGENT_NAMES, run_real_agent
    assert len(REAL_AGENT_NAMES) >= 5
    assert "File Tool Agent" in REAL_AGENT_NAMES
    assert "Deployment Tool Agent" in REAL_AGENT_NAMES


def test_tool_executor_imports():
    """Tool executor is importable and has execute_tool."""
    from tool_executor import execute_tool
    assert callable(execute_tool)


def test_autonomy_loop_imports():
    """Autonomy loop is importable (self-heal)."""
    from autonomy_loop import run_bounded_autonomy_loop
    assert callable(run_bounded_autonomy_loop)


def test_run_agent_real_behavior_does_not_raise_for_unknown():
    """run_agent_real_behavior does not raise for unknown agent (no-op)."""
    run_agent_real_behavior("UnknownAgentXYZ", "test-project-id", {"output": "x"}, {})


@pytest.mark.asyncio
async def test_export_zip_endpoint_accepts_post(app_client):
    """POST /api/export/zip accepts files dict (deploy path)."""
    r = await app_client.post("/api/export/zip", json={"files": {"src/App.jsx": "const App = () => null; export default App;"}})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip") or "octet-stream" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_health_and_build_phases_ready_for_deploy(app_client):
    """Health and build/phases respond (Railway deploy readiness)."""
    r = await app_client.get("/api/health")
    assert r.status_code == 200
    r2 = await app_client.get("/api/build/phases")
    assert r2.status_code == 200
    data = r2.json()
    assert "phases" in data
    assert isinstance(data["phases"], list)
