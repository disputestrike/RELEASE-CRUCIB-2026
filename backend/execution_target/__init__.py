"""
Execution Target Detection Module
Intelligently determines which execution target(s) to use for a request
"""

from backend.execution_target.intent_analyzer import IntentAnalyzer, ExecutionTarget
from backend.execution_target.target_detection_api import router as execution_target_router

__all__ = ["IntentAnalyzer", "ExecutionTarget", "execution_target_router"]

