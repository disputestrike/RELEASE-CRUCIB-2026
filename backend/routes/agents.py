"""Agent catalog and run surfaces.

This module keeps the required ``backend.routes.agents`` import alive and
delegates to the compatibility implementations that expose the real DAG-backed
catalog and truthful run metadata.
"""

from __future__ import annotations

from fastapi import APIRouter

try:
    from .compat import (

    agents_advantage_compat,
    automation_list_compat,
    list_agent_templates_compat,
    list_agents_compat,
    memory_list_compat,
    run_agent_compat,
    )
except ImportError:
    from routes.compat import (  # type: ignore[import]

    agents_advantage_compat,
    automation_list_compat,
    list_agent_templates_compat,
    list_agents_compat,
    memory_list_compat,
    run_agent_compat,
    )

router = APIRouter(prefix="/api", tags=["agents"])

router.add_api_route("/agents", list_agents_compat, methods=["GET"])
router.add_api_route("/agents/templates", list_agent_templates_compat, methods=["GET"])
router.add_api_route("/agents/advantage", agents_advantage_compat, methods=["GET"])
router.add_api_route("/agents/run/{agent_name}", run_agent_compat, methods=["POST"])
router.add_api_route("/agents/run/memory-list", memory_list_compat, methods=["GET"])
router.add_api_route("/agents/run/automation-list", automation_list_compat, methods=["GET"])

