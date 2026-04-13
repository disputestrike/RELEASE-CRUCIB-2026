"""
Execution Target Detection Module
Intelligently determines which execution target(s) to use for a request

Phases:
  Phase 1: Intent Recognition - Auto-detect targets from requests
  Phase 2: Conditional UI - Smart frontend selector (hide/show based on confidence)
  Phase 3: Dynamic Execution - Switch targets mid-stream, multi-target support
  Phase 4: Learning System - Improve confidence over time based on outcomes
"""

from execution_target.dynamic_executor import DynamicExecutor, ExecutionMode
from execution_target.integrated_api import router as integrated_router
from execution_target.intent_analyzer import ExecutionTarget, IntentAnalyzer
from execution_target.learning_analytics import LearningAnalytics
from execution_target.target_detection_api import router as detection_router
from execution_target.target_learning import TargetLearningSystem

__all__ = [
    "IntentAnalyzer",
    "ExecutionTarget",
    "DynamicExecutor",
    "ExecutionMode",
    "TargetLearningSystem",
    "LearningAnalytics",
    "detection_router",
    "integrated_router",
]
