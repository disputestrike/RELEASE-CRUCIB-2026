"""
Smart Error Recovery System for CrucibAI
Handles failures gracefully with project-specific fallbacks and retry logic.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """Manages error recovery with intelligent fallbacks."""
    
    # Project-specific fallbacks
    FALLBACK_TEMPLATES = {
        "Frontend Generation": """import React from 'react';

export default function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Welcome to Your App</h1>
      <p>Frontend generation encountered an issue. This is a fallback template.</p>
      <p>Please check the error logs and try again.</p>
    </div>
  );
}""",
        
        "Backend Generation": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Generated API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Backend generation encountered an issue. This is a fallback template."}

@app.get("/health")
async def health():
    return {"status": "ok"}
""",
        
        "Database Agent": """-- Fallback database schema
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
""",
        
        "Test Generation": """import pytest

def test_placeholder():
    '''Placeholder test - generation failed.'''
    assert True

def test_example():
    '''Example test structure.'''
    result = 1 + 1
    assert result == 2
""",
        
        "Image Generation": """{
  "hero": "Professional business image with modern design elements",
  "feature_1": "Team collaboration and productivity visualization",
  "feature_2": "Analytics and data visualization dashboard"
}""",
        
        "Design Agent": """{
  "design_system": {
    "colors": {
      "primary": "#1A1A1A",
      "secondary": "#808080",
      "accent": "#999999"
    },
    "typography": {
      "heading": "Inter, system-ui, sans-serif",
      "body": "Inter, system-ui, sans-serif"
    }
  },
  "layouts": [
    {"name": "Hero Section", "description": "Full-width hero with CTA"},
    {"name": "Feature Grid", "description": "3-column feature showcase"}
  ]
}""",
    }
    
    def __init__(self, db=None):
        self.db = db
        self.retry_history = {}
        self.error_context = {}
    
    async def execute_with_recovery(
        self,
        agent_name: str,
        task_func: Callable,
        context: Dict[str, Any],
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Execute a task with automatic retry and fallback.
        
        Returns: {
            "success": bool,
            "result": Any,
            "error": str,
            "retries": int,
            "used_fallback": bool,
            "execution_time": float
        }
        """
        start_time = datetime.now()
        result = {
            "success": False,
            "result": None,
            "error": None,
            "retries": 0,
            "used_fallback": False,
            "execution_time": 0
        }
        
        # Initialize retry history for this agent
        if agent_name not in self.retry_history:
            self.retry_history[agent_name] = []
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Executing {agent_name} (attempt {attempt + 1}/{max_retries})")
                
                # Execute with timeout
                task_result = await asyncio.wait_for(
                    task_func(context),
                    timeout=timeout_seconds
                )
                
                result["success"] = True
                result["result"] = task_result
                result["retries"] = attempt
                
                logger.info(f"✅ {agent_name} succeeded on attempt {attempt + 1}")
                break
            
            except asyncio.TimeoutError:
                error_msg = f"Task timeout after {timeout_seconds}s"
                result["error"] = error_msg
                logger.warning(f"⏱️ {agent_name} timeout: {error_msg}")
                
                # Store error context
                self._store_error_context(agent_name, error_msg, attempt)
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                result["error"] = error_msg
                logger.error(f"❌ {agent_name} failed: {error_msg}")
                
                # Store error context
                self._store_error_context(agent_name, error_msg, attempt)
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        # If all retries failed, use fallback
        if not result["success"]:
            logger.warning(f"All retries failed for {agent_name}, using fallback")
            result["result"] = self._get_fallback(agent_name)
            result["used_fallback"] = True
        
        # Calculate execution time
        result["execution_time"] = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def _store_error_context(self, agent_name: str, error: str, attempt: int):
        """Store error context for analysis."""
        if agent_name not in self.error_context:
            self.error_context[agent_name] = []
        
        self.error_context[agent_name].append({
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "attempt": attempt
        })
    
    def _get_fallback(self, agent_name: str) -> str:
        """Get fallback output for an agent."""
        if agent_name in self.FALLBACK_TEMPLATES:
            return self.FALLBACK_TEMPLATES[agent_name]
        
        # Generic fallback
        return f"// Fallback output for {agent_name}\n// Generation failed, please check error logs."
    
    def get_error_summary(self, agent_name: str) -> Dict[str, Any]:
        """Get error summary for an agent."""
        if agent_name not in self.error_context:
            return {"agent": agent_name, "errors": []}
        
        errors = self.error_context[agent_name]
        return {
            "agent": agent_name,
            "total_errors": len(errors),
            "errors": errors,
            "last_error": errors[-1] if errors else None
        }
    
    def should_cascade_failure(self, agent_name: str, criticality: str) -> bool:
        """
        Determine if failure should cascade to dependent agents.
        
        Returns: True if build should stop, False if can continue
        """
        if criticality == "critical":
            return True
        elif criticality == "high":
            # Check if fallback is available
            return agent_name not in self.FALLBACK_TEMPLATES
        else:
            return False
