import ast

import pytest

from agents.code_repair_agent import CodeRepairAgent, coerce_text_output


@pytest.mark.asyncio
async def test_code_repair_agent_fixes_missing_python_colon():
    broken = """async def create_job(data: dict)
    job = data
    return job
"""

    repaired = await CodeRepairAgent.repair_output(
        agent_name="ML Model Definition Agent",
        output=broken,
    )

    assert repaired["valid"] is True
    assert repaired["repaired"] is True
    assert repaired["language"] == "python"
    assert repaired["strategy"] in {"add_missing_colons", "ensure_block_body", "llm_repair"}
    ast.parse(repaired["output"])
    assert "async def create_job(data: dict):" in repaired["output"]


def test_coerce_text_output_handles_dict_without_slice_errors():
    value = {"framework": "tensorflow", "layers": [64, 32, 1]}
    rendered = coerce_text_output(value, limit=200)

    assert isinstance(rendered, str)
    assert '"framework": "tensorflow"' in rendered


@pytest.mark.asyncio
async def test_repair_workspace_files_updates_broken_python_file(tmp_path):
    target = tmp_path / "backend" / "model.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "def build_model(config)\n    return config\n",
        encoding="utf-8",
    )

    changed = await CodeRepairAgent.repair_workspace_files(
        str(tmp_path),
        ["backend/model.py"],
        verification_issues=["SyntaxError: expected ':'"],
    )

    assert changed == ["backend/model.py"]
    ast.parse(target.read_text(encoding="utf-8"))
