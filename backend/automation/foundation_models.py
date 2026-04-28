from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RunStatus = Literal["pending", "running", "success", "failed", "cancelled", "waiting_approval"]
CapabilityStatus = Literal["available", "disabled", "requires_config", "coming_soon"]


class AutomationStepDefinition(BaseModel):
    key: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = False
    retry: Dict[str, Any] = Field(default_factory=lambda: {"max_attempts": 1})


class AutomationRunDefinition(BaseModel):
    name: str
    owner_id: Optional[str] = None
    description: Optional[str] = None
    steps: List[AutomationStepDefinition] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutomationStepResult(BaseModel):
    key: str
    status: RunStatus = "pending"
    attempt: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log_lines: List[str] = Field(default_factory=list)


class ScheduleDefinition(BaseModel):
    type: Literal["manual", "run_at", "cron", "webhook"] = "manual"
    owner_id: str
    enabled: bool = False
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    timezone: str = "UTC"
    next_run_at: Optional[datetime] = None
    last_run_result: Optional[Dict[str, Any]] = None


class ComputerUseActionDefinition(BaseModel):
    action: Literal["see", "click", "type", "wait", "screenshot", "navigate"]
    target: str
    selector: Optional[str] = None
    coordinates: Optional[Dict[str, int]] = None
    text: Optional[str] = None
    milliseconds: Optional[int] = None
    status: CapabilityStatus = "disabled"
    error: Optional[str] = None
    audit: Dict[str, Any] = Field(default_factory=dict)


class AssetGenerationRequest(BaseModel):
    prompt: str
    asset_type: Literal["image", "icon", "hero", "illustration", "texture"] = "image"
    provider: Optional[str] = None
    storage_scope: Literal["job", "project", "artifact"] = "artifact"
    job_id: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PreviewArtifactDescriptor(BaseModel):
    name: str
    artifact_type: str
    mime_type: Optional[str] = None
    status: CapabilityStatus
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    unsupported_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
