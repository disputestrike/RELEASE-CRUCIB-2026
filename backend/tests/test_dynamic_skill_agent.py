from backend.routes.skills import _draft_skill_contract


def test_dynamic_skill_contract_for_document_ingestion_is_honest():
    skill = _draft_skill_contract(
        "Create a skill for ingesting PDFs and turning them into app requirements",
        "user_test",
    )

    assert skill["generated_by"] == "dynamic_skill_agent"
    assert skill["category"] == "knowledge"
    assert "pdfs" in skill["trigger_phrases"]
    assert "requires_config" in skill["instructions"]
    assert "Persist source documents" in skill["instructions"]
    assert skill["execution_contract"]["kind"] == "instruction_skill"
    assert "validation_results" in skill["execution_contract"]["artifact_outputs"]
