from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SimulationCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    assumptions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationRunRequest(BaseModel):
    simulation_id: Optional[str] = Field(default=None, max_length=128)
    prompt: Optional[str] = Field(default=None, max_length=12000)
    assumptions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    depth: str = Field(default="balanced", max_length=24)
    use_live_evidence: bool = True
    population_size: Optional[int] = Field(default=None, ge=100, le=10000)
    evidence_depth: Optional[int] = Field(default=None, ge=1, le=10)
    rounds: int = Field(default=5, ge=1, le=8)
    agent_count: int = Field(default=8, ge=3, le=24)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    require_live_retrieval_success: bool = Field(
        default=False,
        description="If true, current-data runs return 422 when retrieval_debug.gate.passed is false.",
    )


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
