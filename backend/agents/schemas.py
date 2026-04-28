from typing import List
from pydantic import BaseModel, Field

class IntentSchema(BaseModel):
    goal: str = Field(..., description="The primary goal extracted from the user's prompt.")
    constraints: List[str] = Field(default_factory=list, description="List of constraints identified in the prompt.")
    risk_level: int = Field(..., ge=1, le=5, description="Assessed risk level of the task (1-5, 5 being highest).")
    required_tools: List[str] = Field(default_factory=list, description="List of tools identified as necessary for the task.")
