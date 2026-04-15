"""API route modules - modular include helpers."""

from importlib import import_module
from typing import Iterable
import logging

from fastapi import FastAPI

from modular_env import modular_safe_import_env

logger = logging.getLogger(__name__)

ROUTE_MODULES = [
    "auth",
    "jobs",
    "agents",
    "monitoring",
    "projects",
    "workspace",
    "orchestrator",
    "chat",
    "deploy",
    "misc",
    "skills",
    "tokens",
    "automation",
    "mobile",
    "trust",
    "ai",
    "community",
    "ecosystem",
    "git",
    "git_sync",
    "ide",
    "sso",
    "terminal",
    "vibecoding",
]


def _module_router(module_name: str):
    try:
        with modular_safe_import_env():
            mod = import_module(f"routes.{module_name}")
    except BaseException as exc:
        logger.warning("Skipping route module %s during modular include: %s", module_name, exc)
        return None, str(exc)
    for candidate in ("router", f"{module_name}_router", "agents_router"):
        router = getattr(mod, candidate, None)
        if router is not None:
            return router, None
    return None, "No router exported"


def include_all_routes(app: FastAPI, modules: Iterable[str] | None = None):
    """Include all route modules that expose a router.

    This is intentionally tolerant so the modular entrypoint can reuse existing
    route files without forcing one naming convention immediately.
    """
    for module_name in (modules or ROUTE_MODULES):
        router, error = _module_router(module_name)
        if router is not None:
            app.include_router(router, prefix="")
    return app


def inspect_route_modules(modules: Iterable[str] | None = None):
    """Return a simple audit structure of which route modules expose a router."""
    report = []
    for module_name in (modules or ROUTE_MODULES):
        router, error = _module_router(module_name)
        report.append({
            "module": module_name,
            "loaded": router is not None,
            "router_name": getattr(router, "prefix", None) if router is not None else None,
            "error": error,
        })
    return report


__all__ = ["include_all_routes", "ROUTE_MODULES", "inspect_route_modules"]
