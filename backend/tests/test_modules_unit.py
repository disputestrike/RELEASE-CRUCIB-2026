"""
Fortune 100 Layer 2: Unit tests for every module (agents, utils, quality).
"""

import os

import pytest

# ==================== AGENT DAG ====================


def test_agent_dag_import():
    """agent_dag module loads."""
    import agent_dag

    assert agent_dag is not None


def test_agent_dag_has_all_agents():
    """AGENT_DAG contains expected agents."""
    from agent_dag import AGENT_DAG

    required = {
        "Planner",
        "Frontend Generation",
        "Backend Generation",
        "Image Generation",
        "Video Generation",
    }
    for name in required:
        assert name in AGENT_DAG, f"Missing agent: {name}"


def test_agent_dag_dependencies_acyclic():
    """All depends_on references exist and form acyclic graph."""
    from agent_dag import AGENT_DAG, topological_sort

    nodes = set(AGENT_DAG.keys())
    for name, cfg in AGENT_DAG.items():
        for dep in cfg.get("depends_on", []):
            assert dep in nodes, f"Agent {name} depends on unknown {dep}"
    order = topological_sort(AGENT_DAG)
    assert len(order) == len(nodes)
    assert set(order) == nodes


def test_agent_dag_get_system_prompt():
    """get_system_prompt returns non-empty for known agent."""
    from agent_dag import get_system_prompt_for_agent

    p = get_system_prompt_for_agent("Planner")
    assert isinstance(p, str)
    assert len(p) > 0


def test_agent_dag_get_system_prompt_unknown():
    """get_system_prompt returns empty for unknown agent."""
    from agent_dag import get_system_prompt_for_agent

    p = get_system_prompt_for_agent("UnknownAgentXYZ")
    assert p == ""


def test_agent_dag_context_max_chars():
    """get_context_max_chars returns positive int."""
    from agent_dag import get_context_max_chars

    n = get_context_max_chars()
    assert isinstance(n, int)
    assert n > 0


def test_agent_dag_build_context_truncates():
    """build_context_from_previous_agents truncates long outputs."""
    from agent_dag import build_context_from_previous_agents

    outputs = {"A": {"output": "x" * 5000}, "B": {"output": "short"}}
    ctx = build_context_from_previous_agents("C", outputs, "Build a todo app")
    assert len(ctx) < 6000
    assert "short" in ctx


# ==================== UTILS RBAC ====================


def test_rbac_role_enum():
    """Role enum has expected values."""
    from utils.rbac import Role

    assert Role.OWNER.value == "owner"
    assert Role.VIEWER.value == "viewer"


def test_rbac_get_user_role_default():
    """get_user_role returns OWNER for empty/unknown."""
    from utils.rbac import Role, get_user_role

    assert get_user_role({}) == Role.OWNER
    assert get_user_role({"role": "viewer"}) == Role.VIEWER


def test_rbac_has_permission_owner():
    """Owner has all permissions."""
    from utils.rbac import Permission, has_permission

    assert has_permission({"role": "owner"}, Permission.MANAGE_BILLING)
    assert has_permission({"role": "owner"}, Permission.DELETE_PROJECT)


def test_rbac_has_permission_viewer():
    """Viewer has limited permissions."""
    from utils.rbac import Permission, has_permission

    assert has_permission({"role": "viewer"}, Permission.VIEW_PROJECT)
    assert not has_permission({"role": "viewer"}, Permission.DELETE_PROJECT)


# ==================== UTILS AUDIT LOG ====================


def test_audit_logger_init():
    """Audit logger initializes with db."""
    from utils.audit_log import AuditLogger

    class FakeDb:
        audit_log = type(
            "FakeCol",
            (),
            {"insert_one": lambda s, d: type("R", (), {"inserted_id": "x"})},
        )()

    logger = AuditLogger(FakeDb())
    assert logger is not None
    assert hasattr(logger, "log")


# ==================== AGENTS LEGAL COMPLIANCE ====================


def test_legal_compliance_import():
    """legal_compliance module loads."""
    from agents import legal_compliance

    assert legal_compliance is not None


def test_legal_check_request_blocks_illegal():
    """check_request blocks illegal content."""
    from agents.legal_compliance import check_request

    r = check_request("how to make bomb instructions")
    assert r.get("allowed") is False
    assert r.get("category")


def test_legal_check_request_allows_safe():
    """check_request allows safe content."""
    from agents.legal_compliance import check_request

    r = check_request("build a todo app with React")
    assert r.get("allowed") is True


# ==================== QUALITY ====================


def test_quality_score_empty():
    """score_generated_code handles empty inputs."""
    from quality import score_generated_code

    q = score_generated_code()
    assert "overall_score" in q
    assert "verdict" in q


def test_quality_score_with_code():
    """score_generated_code scores with frontend code."""
    from quality import score_generated_code

    q = score_generated_code(frontend_code="function App() { return <div>Hi</div>; }")
    assert q.get("overall_score", 0) >= 0
    assert q.get("verdict") in (
        "poor",
        "fair",
        "good",
        "excellent",
        None,
    ) or isinstance(q.get("verdict"), str)


# ==================== CODE_QUALITY ====================


def test_code_quality_score():
    """code_quality.score_generated_code returns breakdown."""
    from code_quality import score_generated_code

    q = score_generated_code(frontend_code="function App() { return null; }")
    assert "breakdown" in q or "overall_score" in q or "frontend" in str(q)
