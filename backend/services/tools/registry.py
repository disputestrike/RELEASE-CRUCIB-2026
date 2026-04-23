from __future__ import annotations

from typing import Dict, Optional

from .contracts import ToolContract


def _contract_map() -> Dict[str, ToolContract]:
    contracts = {
        "file": ToolContract(
            name="file",
            aliases=["filesystem"],
            description="Read/write/list/mkdir operations in workspace-scoped paths.",
            input_schema={"type": "object", "required": ["action"], "properties": {"action": {"type": "string"}, "path": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "path": {"type": "string"}}},
            risk_level=0.6,
            side_effect_class="filesystem",
            requires_approval=False,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided", "auto-build", "inspect", "repair"],
            allowed_skills=[],
        ),
        "run": ToolContract(
            name="run",
            aliases=["exec", "command"],
            description="Execute allowlisted commands in project workspace.",
            input_schema={"type": "object", "required": ["command"], "properties": {"command": {"type": "array"}, "cwd": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "output": {"type": "string"}, "returncode": {"type": "number"}}},
            risk_level=0.8,
            side_effect_class="process",
            requires_approval=True,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided", "auto-build", "repair"],
            allowed_skills=[],
        ),
        "api": ToolContract(
            name="api",
            aliases=["http"],
            description="Fetch remote HTTP(S) resources with SSRF protections.",
            input_schema={"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "status": {"type": "number"}, "body": {"type": "string"}}},
            risk_level=0.55,
            side_effect_class="network",
            requires_approval=False,
            supports_dry_run=True,
            supports_undo=False,
            allowed_modes=["guided", "auto-build", "inspect", "what-if"],
            allowed_skills=[],
        ),
        "browser": ToolContract(
            name="browser",
            aliases=["web"],
            description="HTTP(S) browse/fetch tool for lightweight page preview body extraction.",
            input_schema={"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "body_preview": {"type": "string"}}},
            risk_level=0.5,
            side_effect_class="network",
            requires_approval=False,
            supports_dry_run=True,
            supports_undo=False,
            allowed_modes=["guided", "auto-build", "inspect", "what-if"],
            allowed_skills=[],
        ),
        "db": ToolContract(
            name="db",
            aliases=["sqlite"],
            description="Workspace-scoped SQLite query tool (read-select constraints by policy).",
            input_schema={"type": "object", "required": ["action"], "properties": {"action": {"type": "string"}, "path": {"type": "string"}, "sql": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "rows": {"type": "array"}}},
            risk_level=0.65,
            side_effect_class="data",
            requires_approval=True,
            supports_dry_run=False,
            supports_undo=False,
            allowed_modes=["guided", "inspect", "repair"],
            allowed_skills=[],
        ),
    }
    return contracts


def _validate_registry(contracts: Dict[str, ToolContract]) -> None:
    alias_to_name: Dict[str, str] = {}
    for name, contract in contracts.items():
        if name != contract.name:
            raise ValueError(f"Contract key mismatch: key={name} contract.name={contract.name}")
        for alias in contract.aliases:
            a = (alias or "").strip().lower()
            if not a:
                raise ValueError(f"Contract {name} has empty alias")
            prev = alias_to_name.get(a)
            if prev and prev != name:
                raise ValueError(f"Alias collision: '{a}' used by {prev} and {name}")
            alias_to_name[a] = name


_CONTRACTS = _contract_map()
_validate_registry(_CONTRACTS)
_ALIASES = {alias: name for name, c in _CONTRACTS.items() for alias in c.aliases}


def get_tool_contract(tool_name: str) -> Optional[ToolContract]:
    key = (tool_name or "").strip().lower()
    if not key:
        return None
    canonical = _ALIASES.get(key, key)
    return _CONTRACTS.get(canonical)


def list_tool_contracts() -> Dict[str, ToolContract]:
    return dict(_CONTRACTS)
