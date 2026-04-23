from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ToolContract:
    name: str
    aliases: List[str]
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: float
    side_effect_class: str
    requires_approval: bool
    supports_dry_run: bool
    supports_undo: bool
    allowed_modes: List[str]
    allowed_skills: List[str]

    def __post_init__(self) -> None:
        name = (self.name or "").strip().lower()
        if not name:
            raise ValueError("ToolContract.name must be a non-empty string")
        if float(self.risk_level) < 0.0 or float(self.risk_level) > 1.0:
            raise ValueError("ToolContract.risk_level must be between 0.0 and 1.0")

        sec = (self.side_effect_class or "").strip().lower()
        if not sec:
            raise ValueError("ToolContract.side_effect_class must be non-empty")

        self._validate_json_schema("input_schema", self.input_schema)
        self._validate_json_schema("output_schema", self.output_schema)

        aliases = [str(a or "").strip().lower() for a in (self.aliases or [])]
        if any(not a for a in aliases):
            raise ValueError("ToolContract.aliases cannot contain empty values")
        if name in aliases:
            raise ValueError("ToolContract.aliases cannot include the canonical name")
        if len(set(aliases)) != len(aliases):
            raise ValueError("ToolContract.aliases must be unique")

    @staticmethod
    def _validate_json_schema(field_name: str, schema: Dict[str, Any]) -> None:
        if not isinstance(schema, dict):
            raise ValueError(f"ToolContract.{field_name} must be a dict")
        schema_type = schema.get("type")
        if schema_type != "object":
            raise ValueError(f"ToolContract.{field_name}.type must be 'object'")
        properties = schema.get("properties")
        if properties is not None and not isinstance(properties, dict):
            raise ValueError(f"ToolContract.{field_name}.properties must be a dict when present")
        required = schema.get("required")
        if required is not None:
            if not isinstance(required, list):
                raise ValueError(f"ToolContract.{field_name}.required must be a list when present")
            for item in required:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(f"ToolContract.{field_name}.required items must be non-empty strings")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "aliases": list(self.aliases),
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "risk_level": self.risk_level,
            "side_effect_class": self.side_effect_class,
            "requires_approval": self.requires_approval,
            "supports_dry_run": self.supports_dry_run,
            "supports_undo": self.supports_undo,
            "allowed_modes": list(self.allowed_modes),
            "allowed_skills": list(self.allowed_skills),
        }