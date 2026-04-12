"""
API route modules - all routes organized by domain.
"""

from fastapi import APIRouter
from . import auth, jobs, agents, monitoring, projects

# Create main router
api_router = APIRouter(prefix="/api", tags=["api"])


# Register all route modules
def include_all_routes(app):
    """Include all route modules in the FastAPI app"""
    app.include_router(auth.router, prefix="")
    app.include_router(jobs.router, prefix="")
    app.include_router(agents.router, prefix="")
    app.include_router(monitoring.router, prefix="")
    app.include_router(projects.router, prefix="")
    return app


__all__ = [
    "auth",
    "jobs",
    "agents",
    "monitoring",
    "projects",
    "include_all_routes",
]
