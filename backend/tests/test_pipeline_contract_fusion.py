import json
import importlib

import pytest

from backend.orchestration import pipeline_orchestrator
from backend.orchestration import claude_code_backbone
from backend.orchestration.enterprise_proof import generate_enterprise_proof_artifacts


def test_generate_prompt_contains_crucib_grade_directive():
    prompt = pipeline_orchestrator._GENERATE_SYSTEM_PROMPT

    assert "CRUCIB-GRADE BUILD STANDARD" in prompt
    assert "Frozen BuildContract" not in prompt
    assert "Do not fake critical paths" in prompt
    assert "Every frontend API call must map to a real backend route" in prompt


def test_clean_room_claude_code_backbone_is_vendored_and_fused():
    root = claude_code_backbone.vendored_source_root()

    assert claude_code_backbone.backbone_available() is True
    assert (root / "agent.py").exists()
    assert (root / "tool_registry.py").exists()
    assert (root / "NOTICE.md").exists()

    fused = claude_code_backbone.build_backbone_system_prompt("BASE")
    assert "CLAUDE CODE BACKBONE RUNTIME" in fused
    assert "Read/Glob/Grep" in fused
    assert "Do not default to SaaS" in fused

    tool_names = {tool["name"] for tool in claude_code_backbone.get_claude_code_tool_definitions()}
    assert {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}.issubset(tool_names)


@pytest.mark.asyncio
async def test_backbone_translates_runtime_tool_events():
    events = []

    async def collect(event_type, payload):
        events.append((event_type, payload))

    callback = claude_code_backbone.make_backbone_event_callback(collect)
    await callback("tool_call", {"tool_name": "read_file", "path": "src/App.tsx"})
    await callback("tool_result", {"tool_name": "run_command", "output": "exit_code=0", "success": True})

    backbone_events = [(kind, payload) for kind, payload in events if kind.startswith("claude_code_")]
    assert backbone_events[0][0] == "claude_code_tool_start"
    assert backbone_events[0][1]["event"] == "ToolStart"
    assert backbone_events[0][1]["name"] == "Read"
    assert backbone_events[1][0] == "claude_code_tool_end"
    assert backbone_events[1][1]["event"] == "ToolEnd"
    assert backbone_events[1][1]["name"] == "Bash"


def test_pre_generation_contract_is_written_and_attached_to_plan(tmp_path):
    plan = {
        "build_type": "fullstack_web",
        "stack": "react+vite+ts",
        "file_manifest": ["src/App.tsx"],
    }

    contract = pipeline_orchestrator._materialize_pre_generation_contract(
        str(tmp_path),
        job_id="tsk_contract_first",
        goal="Build a SaaS MVP with authentication, PayPal billing, and user dashboard",
        plan=plan,
    )

    contract_path = tmp_path / ".crucibai" / "build_contract.json"
    assert contract_path.exists()
    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert plan["build_contract"]["build_id"] == "tsk_contract_first"
    assert contract["build_id"] == "tsk_contract_first"
    assert payload["auth_requirements"]
    assert payload["billing_requirements"]
    assert payload["required_proof_types"]
    assert plan["contract_satisfied"] is False


def test_contract_completion_profile_uses_prompt_derived_contract():
    plan = {
        "build_type": "healthcare_platform",
        "build_contract": {
            "build_class": "healthcare_platform",
            "product_name": "ClinicOps Command",
            "core_workflows": ["patient intake", "appointment triage", "PHI audit"],
            "required_database_tables": ["patients", "appointments", "phi_access_log"],
        },
    }

    profile = pipeline_orchestrator._contract_completion_profile(
        plan,
        "Build a healthcare platform for patient intake and audit",
    )

    assert profile["product_name"] == "ClinicOps Command"
    assert profile["domain_items"][:3] == ["Patient Intake", "Appointment Triage", "Phi Audit"]
    assert profile["tables"][:3] == ["patients", "appointments", "phi_access_log"]
    assert profile["nav_label"] == "Patient Intake"


@pytest.mark.asyncio
async def test_generic_fullstack_contract_does_not_force_saas_or_billing(tmp_path):
    goal = "Build a full-stack web app with user authentication and dashboard"
    plan = {
        "build_type": "fullstack_web",
        "build_contract": {
            "build_class": "fullstack_web",
            "original_goal": goal,
            "auth_requirements": ["login", "current user"],
            "core_workflows": ["login", "dashboard"],
            "required_database_tables": ["users", "sessions", "dashboard_records"],
            "required_api_endpoints": ["/api/auth/login", "/api/dashboard/overview"],
        },
        "file_manifest": ["src/App.tsx"],
    }

    profile = pipeline_orchestrator._contract_completion_profile(plan, goal)
    assert profile["build_class"] == "fullstack_web"

    written = await pipeline_orchestrator._write_contract_completion_workspace(
        str(tmp_path),
        goal,
        plan,
    )
    assert "backend/routes/auth.py" in written
    assert "backend/routes/billing.py" not in written
    assert "src/pages/BillingPage.tsx" not in written

    all_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".py", ".md", ".json", ".sql", ".example"}
    )
    assert "PayPal" not in all_text
    assert "paypal" not in all_text
    assert "SaaS MVP" not in all_text


@pytest.mark.asyncio
async def test_contract_completion_workspace_satisfies_strict_saas_gate(tmp_path):
    goal = "Build a SaaS MVP with authentication, PayPal billing, and user dashboard"
    plan = {
        "build_type": "fullstack_saas",
        "stack": "react+vite+ts+fastapi+postgres",
        "file_manifest": ["src/App.tsx"],
    }
    pipeline_orchestrator._materialize_pre_generation_contract(
        str(tmp_path),
        job_id="tsk_contract_completion",
        goal=goal,
        plan=plan,
    )

    written = await pipeline_orchestrator._write_contract_completion_workspace(
        str(tmp_path),
        goal,
        plan,
    )
    assert "backend/routes/auth.py" in written
    assert "backend/routes/billing.py" in written
    assert "db/migrations/001_initial.sql" in written
    assert pipeline_orchestrator._contract_completion_required(plan, goal) is True

    result = generate_enterprise_proof_artifacts(
        str(tmp_path),
        {"id": "tsk_contract_completion", "goal": goal},
        plan={"build_command": ["npm", "run", "build"], "build_contract": plan["build_contract"]},
        assemble_result={"success": True},
        verify_result={"passed": True, "returncode": 0, "dist_exists": True},
    )

    gate = result["delivery_gate"]
    assert gate["status"] == "PASS"
    assert gate["allowed"] is True
    assert result["api_alignment"]["passed"] is True
    assert result["classification"]["blocked"] == []
    assert result["classification"]["mocked"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("build_class", "goal", "expected_files"),
    [
        (
            "ecommerce",
            "Build an e-commerce store with product catalog, cart, checkout, and PayPal payments",
            ["src/pages/DomainPage.tsx", "backend/routes/domain.py", "db/migrations/001_initial.sql"],
        ),
        (
            "ai_agent_platform",
            "Build an AI agent platform with tool runs and proof trail",
            ["src/pages/DomainPage.tsx", "backend/routes/domain.py", "db/migrations/001_initial.sql"],
        ),
        (
            "mobile_expo",
            "Build a React Native mobile app with navigation and multiple screens",
            ["app.json", "eas.json", "App.mobile.tsx", "src/mobile/MobileNavigator.tsx"],
        ),
        (
            "api_backend",
            "Build a REST API backend with database, schemas, and tests",
            ["backend/main.py", "backend/routes/domain.py", "tests/test_api_contract.py"],
        ),
    ],
)
async def test_contract_completion_supports_non_saas_classes(tmp_path, build_class, goal, expected_files):
    plan = {
        "build_type": build_class,
        "build_contract": {
            "build_class": build_class,
            "original_goal": goal,
        },
        "file_manifest": ["src/App.tsx"],
    }

    written = await pipeline_orchestrator._write_contract_completion_workspace(
        str(tmp_path),
        goal,
        plan,
    )
    for path in expected_files:
        assert path in written
        assert (tmp_path / path).exists()

    result = generate_enterprise_proof_artifacts(
        str(tmp_path),
        {"id": f"tsk_{build_class}", "goal": goal},
        plan={"build_command": ["npm", "run", "build"], "build_contract": plan["build_contract"]},
        assemble_result={"success": True},
        verify_result={"passed": True, "returncode": 0, "dist_exists": True},
    )

    assert result["delivery_gate"]["status"] == "PASS"
    assert result["delivery_gate"]["allowed"] is True
    assert result["api_alignment"]["passed"] is True
    assert result["classification"]["blocked"] == []
    assert result["classification"]["mocked"] == []


def test_generate_caller_uses_cerebras_when_primary_provider_requests_it(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-present")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-present")
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "cerebras")

    _caller, loop_type = pipeline_orchestrator._pick_generate_caller()

    assert loop_type == "text"


def test_cerebras_key_pool_round_robins(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "key-zero")
    monkeypatch.setenv("CEREBRAS_API_KEY_1", "key-one")
    monkeypatch.setenv("CEREBRAS_API_KEY_2", "key-zero")

    import backend.cerebras_roundrobin as roundrobin

    roundrobin = importlib.reload(roundrobin)
    try:
        assert roundrobin.get_available_key_count() == 2
        assert [roundrobin.get_next_cerebras_key_with_index()[1] for _ in range(3)] == [0, 1, 0]
    finally:
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.delenv("CEREBRAS_API_KEY_1", raising=False)
        monkeypatch.delenv("CEREBRAS_API_KEY_2", raising=False)
        importlib.reload(roundrobin)
