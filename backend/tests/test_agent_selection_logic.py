from agent_dag import AGENT_DAG
from orchestration.agent_selection_logic import (
    _keyword_match,
    build_full_phases_from_dag,
    select_agents_for_goal,
)
from orchestration.planner import _should_use_agent_selection

FULL_SYSTEM_PROMPT = (
    "Build a multi-tenant SaaS with React frontend, Node backend, PostgreSQL, Redis caching, "
    "RabbitMQ queues, Stripe payments, SendGrid email, real-time WebSockets, Kubernetes deployment."
)

HELIOS_PROMPT = (
    "Build Helios Aegis Command: a multi-tenant operations SaaS with CRM, quote workflow, "
    "project workflow, policy engine, immutable audit, analytics, background jobs, and tenant isolation."
)


def test_select_agents_for_goal_picks_infrastructure_and_tool_agents():
    agents = set(
        select_agents_for_goal(
            FULL_SYSTEM_PROMPT, {"requires_full_system_builder": True}
        )
    )

    assert "File Tool Agent" in agents
    assert "Kubernetes Advanced Agent" in agents
    assert "Message Queue Advanced Agent" in agents
    assert "Payment Setup Agent" in agents
    assert "Email Agent" in agents
    assert "WebSocket Agent" in agents


def test_select_agents_for_goal_expands_dependencies():
    agents = set(
        select_agents_for_goal(
            "Build a dapp with smart contracts and web3 wallet support"
        )
    )

    assert "Smart Contract Agent" in agents
    assert "Blockchain Selector Agent" in agents
    assert "Contract Testing Agent" in agents


def test_keyword_match_uses_word_boundaries():
    assert _keyword_match("ar", "augmented reality")
    assert not _keyword_match("ar", "smart contract")
    assert not _keyword_match("ar", "Build smart contract system - NOT an AR app")
    assert _keyword_match("smart contract", "build ethereum smart contract")


def test_blockchain_goal_does_not_pull_false_positive_3d_agent():
    agents = set(select_agents_for_goal("Build Ethereum smart contract DeFi dApp"))

    assert "Smart Contract Agent" in agents
    assert "3D AR/VR Agent" not in agents


def test_negated_ar_phrase_does_not_pull_ar_vr_agent():
    agents = set(select_agents_for_goal("Build smart contract system - NOT an AR app"))

    assert "Smart Contract Agent" in agents
    assert "3D AR/VR Agent" not in agents


def test_select_agents_for_helios_includes_business_and_compliance_agents():
    agents = set(
        select_agents_for_goal(HELIOS_PROMPT, {"requires_full_system_builder": True})
    )

    assert "Approval Flow Agent" in agents
    assert "Business Rules Engine Agent" in agents
    assert "Workflow Agent" in agents
    assert "Audit & Compliance Engine Agent" in agents
    assert "Multi-tenant Agent" in agents
    assert "RBAC Agent" in agents


def test_build_full_phases_from_dag_only_uses_selected_agents():
    selected = select_agents_for_goal(
        "Build a Kubernetes dashboard with Redis, RabbitMQ, and WebSockets"
    )
    phases = build_full_phases_from_dag(selected, AGENT_DAG)
    flat = [agent for phase in phases for agent in phase]

    assert set(flat) == set(selected)
    assert "Kubernetes Advanced Agent" in flat
    assert "Message Queue Advanced Agent" in flat
    assert "WebSocket Agent" in flat


def test_should_use_agent_selection_routes_specialized_prompts():
    assert _should_use_agent_selection("Build 3D product visualizer with Three.js")
    assert _should_use_agent_selection("Build Ethereum smart contract DeFi dApp")
    assert _should_use_agent_selection("Build ML recommendation engine with TensorFlow")
    assert not _should_use_agent_selection("Build a simple todo app")


def test_should_use_agent_selection_false_for_small_portal_without_special_rules():
    """Generic product language should not expand the DAG via keyword:* noise alone."""
    assert not _should_use_agent_selection(
        "Build a customer portal with profile pages and account settings."
    )


def test_ml_model_phrase_still_enables_selection():
    assert _should_use_agent_selection(
        "Train an ml model to predict churn with scikit-learn"
    )


def test_tenant_data_model_does_not_match_ml_model_keyword():
    from orchestration.agent_selection_logic import _keyword_match

    assert not _keyword_match(
        "ml model",
        "Multi-tenant B2B SaaS with tenant data model, OAuth, and CRM pipeline.",
    )


SAAS_MVP_PROMPT = (
    "Build a SaaS MVP with login, password reset, Stripe subscription billing, "
    "an admin dashboard with charts and KPI visualization, and device fingerprinting for fraud."
)


def test_saas_mvp_avoids_iot_and_3d_false_positive_agents():
    agents = set(select_agents_for_goal(SAAS_MVP_PROMPT))
    assert "Data Visualization Agent" in agents
    assert "IoT Dashboard Agent" not in agents
    assert "IoT Mobile App Agent" not in agents
    assert "IoT Security Agent" not in agents
    assert "Microcontroller Firmware Agent" not in agents
    for name in (
        "3D Model Agent",
        "3D Scene Agent",
        "3D Interaction Agent",
        "3D Engine Selector Agent",
    ):
        assert name not in agents


def test_iot_dashboard_prompt_includes_iot_dashboard_agent():
    agents = set(
        select_agents_for_goal(
            "MQTT telemetry with an IoT dashboard for connected devices and sensors"
        )
    )
    assert "IoT Dashboard Agent" in agents


def test_generic_encryption_does_not_select_iot_security_agent():
    agents = set(
        select_agents_for_goal(
            "Add at-rest encryption for PostgreSQL and TLS for the REST API"
        )
    )
    assert "IoT Security Agent" not in agents
    assert "Network Security Agent" in agents


def test_three_js_prompt_still_selects_3d_stack():
    agents = set(
        select_agents_for_goal("3D product viewer with Three.js, WebGL, and orbit controls")
    )
    assert "3D Model Agent" in agents or "3D Scene Agent" in agents


def test_generic_mobile_does_not_select_iot_mobile_agent():
    agents = set(
        select_agents_for_goal(
            "Progressive web app with mobile responsive layout and touch-friendly UI"
        )
    )
    assert "IoT Mobile App Agent" not in agents
    assert "Mobile Responsive Agent" in agents


def test_iot_mobile_phrase_selects_iot_mobile_agent():
    agents = set(
        select_agents_for_goal(
            "Companion IoT mobile app to pair BLE sensors and show live readings"
        )
    )
    assert "IoT Mobile App Agent" in agents


def test_server_legacy_orchestration_registry_is_dag_backed():
    import pathlib

    # Resolve from this test file's location: tests/ -> backend/ -> server.py
    server_path = pathlib.Path(__file__).parent.parent / "server.py"
    if not server_path.exists():
        # Fallback: try relative paths for different working directories
        for candidate in ["server.py", "backend/server.py", "../server.py"]:
            p = pathlib.Path(candidate)
            if p.exists():
                server_path = p
                break
    source = server_path.read_text(encoding="utf-8", errors="replace")

    assert "_token_budget_for_orchestration_agent" in source
    assert "for phase in get_execution_phases(AGENT_DAG)" in source
    assert "/debug/agent-info" in source
    assert "/debug/agent-selection-logs" in source
    assert '@api_router.post("/build")' in source
    assert '"/api/build"' in source
    assert "LAST_BUILD_STATE" in source
