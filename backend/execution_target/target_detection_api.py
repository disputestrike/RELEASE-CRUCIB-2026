"""
API endpoint for execution target detection
Provides auto-selection suggestions to frontend
"""

import logging

from execution_target.intent_analyzer import IntentAnalyzer
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/execution-target", tags=["execution-target"])

analyzer = IntentAnalyzer()


class TargetDetectionRequest(BaseModel):
    """Request to detect execution targets"""

    user_request: str
    allow_secondary: bool = True


class TargetSuggestion(BaseModel):
    """Suggestion for execution targets"""

    primary_target: str
    secondary_targets: list
    confidence: float
    reasoning: str
    features_detected: list


@router.post("/detect", response_model=TargetSuggestion)
async def detect_execution_target(request: TargetDetectionRequest):
    """
    Detect optimal execution target(s) for a user request

    Example:
    ```
    POST /api/execution-target/detect
    {
        "user_request": "Build me a dashboard with real-time data",
        "allow_secondary": true
    }

    Response:
    {
        "primary_target": "fullstack-web",
        "secondary_targets": ["api-backend-first"],
        "confidence": 92,
        "reasoning": "Keywords: dashboard, real-time",
        "features_detected": ["real-time"]
    }
    ```
    """
    try:
        logger.info(f"Detecting target for request: {request.user_request[:50]}...")

        result = analyzer.analyze(request.user_request)

        # If confidence is too low, filter secondary targets
        if result["confidence"] < 50:
            result["secondary_targets"] = []

        if not request.allow_secondary:
            result["secondary_targets"] = []

        logger.info(
            f"Detected: {result['primary_target']} (confidence: {result['confidence']})"
        )

        return TargetSuggestion(**result)

    except Exception as e:
        logger.error(f"Error detecting target: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets")
async def list_available_targets():
    """List all available execution targets"""
    return {
        "targets": [
            {
                "id": "fullstack-web",
                "name": "Full-stack Web",
                "description": "Vite + React + Node.js API",
                "best_for": ["Dashboards", "Interactive UIs", "Real-time apps"],
            },
            {
                "id": "nextjs-app",
                "name": "Next.js App Router",
                "description": "Server-side rendering with App Router",
                "best_for": ["SEO-critical sites", "Server rendering", "API routes"],
            },
            {
                "id": "marketing-static",
                "name": "Marketing/Static Site",
                "description": "Pure static site (HTML/CSS/JS)",
                "best_for": ["Landing pages", "Blogs", "Documentation"],
            },
            {
                "id": "api-backend-first",
                "name": "API & Backend-First",
                "description": "FastAPI/Node.js backend with minimal UI",
                "best_for": ["Microservices", "Data APIs", "Backend services"],
            },
            {
                "id": "agents-automation",
                "name": "Agents & Automation",
                "description": "Intelligent agent orchestration",
                "best_for": ["Automation workflows", "Intelligent agents", "Task bots"],
            },
        ]
    }
