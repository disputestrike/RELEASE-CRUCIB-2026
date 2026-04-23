from __future__ import annotations

import pytest

import tool_executor
from tool_executor import execute_tool
from services.tools.contracts import ToolContract
from services.tools.registry import get_tool_contract, list_tool_contracts


def test_unknown_tool_rejected_with_contract_reason(monkeypatch):
    monkeypatch.setattr(tool_executor, "require_runtime_authority", lambda *_args, **_kwargs: None)
    res = execute_tool("proj-test", "not-a-tool", {})
    assert res["success"] is False
    assert res["policy"]["reason"] == "unknown_tool_contract"
    assert res["tool"]["known"] is False


def test_known_tool_response_includes_contract_metadata(monkeypatch):
    monkeypatch.setattr(tool_executor, "require_runtime_authority", lambda *_args, **_kwargs: None)
    res = execute_tool("proj-test", "file", {"action": "mkdir", "path": "tmp/contracts"})
    assert res["success"] is True
    assert res["tool"]["name"] == "file"
    assert "risk_level" in res["tool"]
    assert res["tool"]["side_effect_class"] == "filesystem"


def test_registry_contains_expected_tools_and_aliases():
    contracts = list_tool_contracts()
    assert {"file", "run", "api", "browser", "db"}.issubset(set(contracts.keys()))

    assert get_tool_contract("filesystem").name == "file"
    assert get_tool_contract("exec").name == "run"
    assert get_tool_contract("http").name == "api"
    assert get_tool_contract("web").name == "browser"
    assert get_tool_contract("sqlite").name == "db"


def test_tool_contract_enforces_risk_bounds():
    with pytest.raises(ValueError, match="risk_level"):
        ToolContract(
            name="bad",
            aliases=["badalias"],
            description="bad",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            risk_level=1.5,
            side_effect_class="filesystem",
            requires_approval=False,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided"],
            allowed_skills=[],
        )


def test_tool_contract_enforces_schema_shape():
    with pytest.raises(ValueError, match="input_schema.type"):
        ToolContract(
            name="badschema",
            aliases=["badschemaalias"],
            description="bad schema",
            input_schema={"type": "array"},
            output_schema={"type": "object", "properties": {}},
            risk_level=0.5,
            side_effect_class="filesystem",
            requires_approval=False,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided"],
            allowed_skills=[],
        )


def test_tool_contract_enforces_alias_rules():
    with pytest.raises(ValueError, match="cannot include the canonical name"):
        ToolContract(
            name="dup",
            aliases=["dup"],
            description="dup",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            risk_level=0.3,
            side_effect_class="filesystem",
            requires_approval=False,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided"],
            allowed_skills=[],
        )
