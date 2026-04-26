from __future__ import annotations

from backend.agent_dag import get_system_prompt_for_agent
from backend.orchestration.code_generation_standard import (
    CODE_GENERATION_AGENT_APPENDIX,
    required_quality_paths,
)
from backend.orchestration.generated_app_template import build_frontend_file_set


def test_generation_agents_receive_senior_codebase_standard(monkeypatch):
    monkeypatch.delenv("USE_TOKEN_OPTIMIZED_PROMPTS", raising=False)

    prompt = get_system_prompt_for_agent("Frontend Generation")

    assert "CRUCIBAI CODEBASE STANDARD" in prompt
    assert "CODE_MANIFEST.md" in prompt
    assert "runtime/ingestion" in prompt
    assert "REQUIREMENTS_FROM_DOCUMENTS.md" in prompt
    assert "App thin" in prompt or "App entry files stay thin" in CODE_GENERATION_AGENT_APPENDIX


def test_token_optimized_generation_prompts_still_include_standard(monkeypatch):
    monkeypatch.setenv("USE_TOKEN_OPTIMIZED_PROMPTS", "1")

    prompt = get_system_prompt_for_agent("Backend Generation")

    assert prompt.startswith("Backend.")
    assert "CRUCIBAI CODEBASE STANDARD" in prompt
    assert "routes/controllers/services/repositories" in prompt
    assert "document-ingestion" in prompt


def test_generated_template_includes_quality_structure_and_docs():
    files = build_frontend_file_set(
        {
            "goal": (
                "Build a SaaS admin app with dashboard, users, permissions, "
                "approvals, reports, workflows, and audit logs."
            )
        }
    )
    paths = {path for path, _ in files}

    assert len(files) >= 80
    for path in required_quality_paths():
        assert path in paths
    assert "src/App.jsx" in paths
    assert "docs/CODE_MANIFEST.md" in paths
    assert "docs/FEATURE_COVERAGE.md" in paths
    assert "docs/ARCHITECTURE.md" in paths
    assert "docs/REQUIREMENTS_FROM_DOCUMENTS.md" in paths
    assert "docs/DESIGN_BRIEF_FROM_DOCUMENTS.md" in paths
    assert "docs/TECHNICAL_SPEC_FROM_DOCUMENTS.md" in paths
    assert "docs/source_documents/.gitkeep" in paths
    assert "docs/extracted_text/.gitkeep" in paths
    assert "docs/summaries/.gitkeep" in paths
    assert "runtime/ingestion/ingestion_manifest.json" in paths
    assert "runtime/ingestion/source_map.json" in paths
    assert "runtime/ingestion/extraction_log.json" in paths
