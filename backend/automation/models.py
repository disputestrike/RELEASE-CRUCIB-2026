"""
Pydantic models for user_agents and agent_runs.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TriggerConfig(BaseModel):
    """Trigger configuration for an agent."""
    type: str  # "schedule" | "webhook"
    cron_expression: Optional[str] = None  # e.g. "0 9 * * *" for 9am daily
    run_at: Optional[str] = None  # one-time ISO datetime
    webhook_secret: Optional[str] = None  # for webhook trigger


class ActionConfig(BaseModel):
    """Single action in an agent workflow."""
    type: str  # "http" | "email" | "slack" | "run_agent" | "approval"
    config: Dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = False


class AgentCreate(BaseModel):
    """Request body for creating an agent."""
    name: str
    description: Optional[str] = None
    trigger: TriggerConfig
    actions: List[ActionConfig] = Field(default_factory=list, min_length=1)
    enabled: bool = True


class AgentUpdate(BaseModel):
    """Request body for updating an agent (partial)."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[TriggerConfig] = None
    actions: Optional[List[ActionConfig]] = None
    enabled: Optional[bool] = None


class AgentResponse(BaseModel):
    """Agent as returned by API."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_config: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool
    created_at: str
    updated_at: str
    webhook_url: Optional[str] = None
    run_count: Optional[int] = None
    last_run_at: Optional[str] = None
    last_run_status: Optional[str] = None


class RunResponse(BaseModel):
    """Single run as returned by API."""
    id: str
    agent_id: str
    user_id: str
    triggered_at: str
    triggered_by: str  # "schedule" | "webhook" | "manual"
    status: str  # "running" | "success" | "failed" | "cancelled" | "waiting_approval"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    output_summary: Optional[Dict[str, Any]] = None
    step_index: Optional[int] = None  # when waiting_approval
