"""MCP (Model Context Protocol) client + registry.

This is a minimal dispatch layer that lets the runtime call out to external
tool servers using a uniform `mcp.<server>.<tool>` tool-id convention. It is
intentionally narrow: full MCP spec JSON-RPC handshake is out of scope here —
adapters are registered directly in-process and called via HTTP.

Usage:

    from backend.services.mcp_client import registry as mcp_registry
    result = await mcp_registry.dispatch("mcp.slack.send",
                                         {"channel": "#eng", "text": "hi"})
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

Handler = Callable[[dict], Awaitable[dict]]


@dataclass
class AdapterTool:
    name: str
    description: str
    handler: Handler
    schema: Optional[dict] = None


class Adapter:
    """A named collection of tools sharing a config (env-provided token, etc.)."""

    def __init__(self, name: str, enabled: bool, reason: str = ""):
        self.name = name
        self.enabled = enabled
        self.reason = reason
        self._tools: dict[str, AdapterTool] = {}

    def register(self, tool: AdapterTool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "schema": t.schema or {}}
            for t in self._tools.values()
        ]

    async def call(self, tool_name: str, args: dict) -> dict:
        t = self._tools.get(tool_name)
        if t is None:
            raise KeyError(f"adapter {self.name!r} has no tool {tool_name!r}")
        if not self.enabled:
            raise RuntimeError(
                f"adapter {self.name!r} is disabled: {self.reason or 'missing credentials'}"
            )
        return await t.handler(args)


class McpRegistry:
    """Routes `mcp.<server>.<tool>` tool-ids to the matching adapter."""

    def __init__(self):
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.name] = adapter
        logger.info(
            "MCP: registered adapter %s (enabled=%s tools=%d)",
            adapter.name, adapter.enabled, len(adapter.list_tools()),
        )

    def get(self, server: str) -> Optional[Adapter]:
        return self._adapters.get(server)

    def list_servers(self) -> list[dict]:
        return [
            {
                "name": a.name,
                "enabled": a.enabled,
                "reason": a.reason,
                "tools": a.list_tools(),
            }
            for a in self._adapters.values()
        ]

    async def dispatch(self, tool_id: str, args: dict) -> Any:
        """tool_id must look like `mcp.<server>.<tool>`."""
        parts = (tool_id or "").split(".", 2)
        if len(parts) != 3 or parts[0] != "mcp":
            raise ValueError(f"invalid MCP tool_id {tool_id!r} — expected 'mcp.<server>.<tool>'")
        _, server, tool = parts
        ad = self.get(server)
        if ad is None:
            raise KeyError(f"no MCP adapter named {server!r}")
        return await ad.call(tool, args)


# Process-wide registry
registry = McpRegistry()


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name, "").strip()
    return v or None


def bootstrap_registry() -> McpRegistry:
    """Register built-in adapters. Called once at app startup."""
    # Import here so adapter modules don't need to be importable at module load time.
    from backend.services.mcp_adapters import slack as slack_adapter
    from backend.services.mcp_adapters import github as github_adapter
    from backend.services.mcp_adapters import notion as notion_adapter

    registry.register(slack_adapter.build(env_get=_env))
    registry.register(github_adapter.build(env_get=_env))
    registry.register(notion_adapter.build(env_get=_env))
    return registry
