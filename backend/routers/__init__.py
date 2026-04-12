"""
Domain routers for CrucibAI server.
Mount these on the main app to split concerns: monitoring, health, auth, projects, tools, orchestration.
"""

from .health import router as health_router
from .monitoring import router as monitoring_router

__all__ = ["monitoring_router", "health_router"]
