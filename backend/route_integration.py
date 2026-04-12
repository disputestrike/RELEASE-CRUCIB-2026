"""
Route Integration Module
Centralizes all modular routes and registers them with the FastAPI app.
This module bridges between the extracted routes and the main server.py
"""

from fastapi import FastAPI
from backend.routes import auth, jobs, agents, monitoring, projects


def register_all_routes(app: FastAPI) -> FastAPI:
    """
    Register all modular routes with the FastAPI app.

    This centralizes route registration and makes it easy to:
    - Add new route modules
    - Remove routes
    - Organize routes by domain

    Args:
        app: FastAPI application instance

    Returns:
        FastAPI app with all routes registered
    """

    print("📡 Registering modular API routes...")

    # Register auth routes
    app.include_router(auth.router, prefix="/api", tags=["authentication"])
    print("  ✅ Auth routes registered (14 endpoints)")

    # Register job routes
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])
    print("  ✅ Job routes registered (12 endpoints)")

    # Register agent routes
    app.include_router(agents.router, prefix="/api", tags=["agents"])
    print("  ✅ Agent routes registered (13 endpoints)")

    # Register monitoring routes
    app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])
    print("  ✅ Monitoring routes registered")

    # Register project routes
    app.include_router(projects.router, prefix="/api", tags=["projects"])
    print("  ✅ Project routes registered")

    print("\n✅ All 39 modular routes registered successfully!")
    return app


__all__ = ["register_all_routes"]
