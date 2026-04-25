from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SimulationCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    assumptions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationRunRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, max_length=12000)
    assumptions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    rounds: int = Field(default=5, ge=1, le=8)
    agent_count: int = Field(default=8, ge=3, le=24)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationFeedback(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScenarioClassification(BaseModel):
    domain: str
    scenario_type: str
    time_sensitivity: str
    required_evidence: List[str]
    output_style: str
    interpretation: str
    ambiguity: str = "low"
    assumptions: List[str] = Field(default_factory=list)

