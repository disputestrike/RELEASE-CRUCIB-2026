import json

from backend.orchestration import pipeline_orchestrator


def test_generate_prompt_contains_crucib_grade_directive():
    prompt = pipeline_orchestrator._GENERATE_SYSTEM_PROMPT

    assert "CRUCIB-GRADE BUILD STANDARD" in prompt
    assert "Frozen BuildContract" not in prompt
    assert "Do not fake critical paths" in prompt
    assert "Every frontend API call must map to a real backend route" in prompt


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

