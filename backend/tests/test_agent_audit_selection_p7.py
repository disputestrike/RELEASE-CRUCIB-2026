"""P7 — agents marked not_fully_integrated in docs/agent_audit.json stay out of swarm selection."""

from orchestration.agent_audit_registry import agents_excluded_from_autorunner_selection
from orchestration.agent_selection_logic import explain_agent_selection


def test_audit_blocklist_loads():
    block = agents_excluded_from_autorunner_selection()
    assert isinstance(block, frozenset)
    assert "3D AR/VR Agent" in block
    # Do not blanket-block infra / web3 agents the swarm still expects
    assert "Smart Contract Agent" not in block


def test_ar_keyword_does_not_select_unwired_3d_agent():
    goal = "Build a simple augmented reality viewer for markers"
    exp = explain_agent_selection(goal, {})
    assert "3D AR/VR Agent" not in (exp.get("selected_agents") or [])
