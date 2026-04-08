from agent_dag import AGENT_DAG
from orchestration.agent_selection_logic import build_full_phases_from_dag, select_agents_for_goal


FULL_SYSTEM_PROMPT = (
    "Build a multi-tenant SaaS with React frontend, Node backend, PostgreSQL, Redis caching, "
    "RabbitMQ queues, Stripe payments, SendGrid email, real-time WebSockets, Kubernetes deployment."
)

HELIOS_PROMPT = (
    "Build Helios Aegis Command: a multi-tenant operations SaaS with CRM, quote workflow, "
    "project workflow, policy engine, immutable audit, analytics, background jobs, and tenant isolation."
)


def test_select_agents_for_goal_picks_infrastructure_and_tool_agents():
    agents = set(select_agents_for_goal(FULL_SYSTEM_PROMPT, {"requires_full_system_builder": True}))

    assert "File Tool Agent" in agents
    assert "Kubernetes Advanced Agent" in agents
    assert "Message Queue Advanced Agent" in agents
    assert "Payment Setup Agent" in agents
    assert "Email Agent" in agents
    assert "WebSocket Agent" in agents


def test_select_agents_for_goal_expands_dependencies():
    agents = set(select_agents_for_goal("Build a dapp with smart contracts and web3 wallet support"))

    assert "Smart Contract Agent" in agents
    assert "Blockchain Selector Agent" in agents
    assert "Contract Testing Agent" in agents


def test_select_agents_for_helios_includes_business_and_compliance_agents():
    agents = set(select_agents_for_goal(HELIOS_PROMPT, {"requires_full_system_builder": True}))

    assert "Approval Flow Agent" in agents
    assert "Business Rules Engine Agent" in agents
    assert "Workflow Agent" in agents
    assert "Audit & Compliance Engine Agent" in agents
    assert "Multi-tenant Agent" in agents
    assert "RBAC Agent" in agents


def test_build_full_phases_from_dag_only_uses_selected_agents():
    selected = select_agents_for_goal("Build a Kubernetes dashboard with Redis, RabbitMQ, and WebSockets")
    phases = build_full_phases_from_dag(selected, AGENT_DAG)
    flat = [agent for phase in phases for agent in phase]

    assert set(flat) == set(selected)
    assert "Kubernetes Advanced Agent" in flat
    assert "Message Queue Advanced Agent" in flat
    assert "WebSocket Agent" in flat


def test_server_legacy_orchestration_registry_is_dag_backed():
    source = open("backend/server.py", "r", encoding="utf-8", errors="replace").read()

    assert "_token_budget_for_orchestration_agent" in source
    assert "for phase in get_execution_phases(AGENT_DAG)" in source
