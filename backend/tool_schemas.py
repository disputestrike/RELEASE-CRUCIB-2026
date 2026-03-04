"""
Pydantic request bodies for /api/tools/* endpoints.
All tool endpoints require authentication (get_current_user).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolBrowserRequest(BaseModel):
    """POST /api/tools/browser"""
    action: str = Field(..., max_length=50)
    url: Optional[str] = Field(None, max_length=2048)
    selector: Optional[str] = Field(None, max_length=500)
    form_data: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[str] = Field(None, max_length=260)  # filename only used for temp; path restricted in agent


class ToolFileRequest(BaseModel):
    """POST /api/tools/file"""
    action: str = Field(..., max_length=20)
    path: Optional[str] = Field(None, max_length=2048)
    content: Optional[str] = None
    destination: Optional[str] = Field(None, max_length=2048)


class ToolApiRequest(BaseModel):
    """POST /api/tools/api"""
    method: str = Field("GET", max_length=10)
    url: str = Field(..., max_length=2048)
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None


class ToolDatabaseRequest(BaseModel):
    """POST /api/tools/database — connection should be server-side only in production."""
    db_type: str = Field("postgres", max_length=20)
    connection: Optional[Dict[str, Any]] = None  # Restrict in production to connection_key or app DB
    query: str = Field(..., max_length=10000)
    params: Optional[List[Any]] = Field(default_factory=list, max_length=100)


class ToolDeployRequest(BaseModel):
    """POST /api/tools/deploy — project_path must be under allowed workspace."""
    platform: str = Field(..., max_length=20)
    project_path: str = Field(..., max_length=1024)
    config: Optional[Dict[str, Any]] = None
