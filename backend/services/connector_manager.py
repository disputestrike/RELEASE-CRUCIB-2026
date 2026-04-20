"""
backend/services/connector_manager.py
──────────────────────────────────────
Auth-aware connector wrappers for external integrations.

Spec: F – Tool Registry + Connector Layer
Branch: engineering/master-list-closeout

Supported connectors:
  • GitHub  – repo, issues, PRs via PyGitHub / REST
  • Railway – deployments via Railway API
  • Vercel  – deployments via Vercel API
  • Slack   – messages via webhooks
  • Stripe  – billing events (read-only)

Design:
  • Each connector is stateless; credentials pulled from env at call time.
  • ConnectorManager.get(name) returns the named connector instance.
  • All connectors implement the ConnectorBase interface.
  • Structured integrations preferred over visual operator actions.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class ConnectorBase(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials are present."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# GitHub connector
# ─────────────────────────────────────────────────────────────────────────────

class GitHubConnector(ConnectorBase):
    name = "github"

    def __init__(self) -> None:
        self._token = os.environ.get("GITHUB_TOKEN", "")
        self._base  = "https://api.github.com"

    def is_available(self) -> bool:
        return bool(self._token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def list_repos(self, org: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{self._base}/orgs/{org}/repos" if org else f"{self._base}/user/repos"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers=self._headers(), params={"per_page": 30})
            r.raise_for_status()
            return r.json()

    async def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict[str, Any]:
        url = f"{self._base}/repos/{owner}/{repo}/issues"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers=self._headers(), json={"title": title, "body": body})
            r.raise_for_status()
            return r.json()

    async def list_prs(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        url = f"{self._base}/repos/{owner}/{repo}/pulls"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers=self._headers(), params={"state": state, "per_page": 20})
            r.raise_for_status()
            return r.json()

    async def create_branch(self, owner: str, repo: str, branch: str, from_sha: str) -> Dict[str, Any]:
        url = f"{self._base}/repos/{owner}/{repo}/git/refs"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers=self._headers(),
                             json={"ref": f"refs/heads/{branch}", "sha": from_sha})
            r.raise_for_status()
            return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Railway connector
# ─────────────────────────────────────────────────────────────────────────────

class RailwayConnector(ConnectorBase):
    name = "railway"

    def __init__(self) -> None:
        self._token = os.environ.get("RAILWAY_TOKEN", "")
        self._base  = "https://backboard.railway.app/graphql/v2"

    def is_available(self) -> bool:
        return bool(self._token)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def _gql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                self._base,
                headers=self._headers(),
                json={"query": query, "variables": variables or {}},
            )
            r.raise_for_status()
            return r.json()

    async def list_projects(self) -> List[Dict[str, Any]]:
        result = await self._gql("{ projects { edges { node { id name } } } }")
        return [e["node"] for e in result.get("data", {}).get("projects", {}).get("edges", [])]

    async def trigger_deploy(self, service_id: str) -> Dict[str, Any]:
        query = """mutation($id: String!) { serviceInstanceDeploy(serviceId: $id) }"""
        return await self._gql(query, {"id": service_id})


# ─────────────────────────────────────────────────────────────────────────────
# Vercel connector
# ─────────────────────────────────────────────────────────────────────────────

class VercelConnector(ConnectorBase):
    name = "vercel"

    def __init__(self) -> None:
        self._token    = os.environ.get("VERCEL_TOKEN", "")
        self._team_id  = os.environ.get("VERCEL_TEAM_ID", "")
        self._base     = "https://api.vercel.com"

    def is_available(self) -> bool:
        return bool(self._token)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def _params(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        p = {}
        if self._team_id:
            p["teamId"] = self._team_id
        if extra:
            p.update(extra)
        return p

    async def list_projects(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self._base}/v9/projects", headers=self._headers(), params=self._params())
            r.raise_for_status()
            return r.json().get("projects", [])

    async def create_deployment(self, project_name: str, git_source: Optional[Dict] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": project_name}
        if git_source:
            payload["gitSource"] = git_source
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{self._base}/v13/deployments", headers=self._headers(),
                             params=self._params(), json=payload)
            r.raise_for_status()
            return r.json()

    async def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self._base}/v13/deployments/{deployment_id}",
                            headers=self._headers(), params=self._params())
            r.raise_for_status()
            return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Slack connector (webhook-based)
# ─────────────────────────────────────────────────────────────────────────────

class SlackConnector(ConnectorBase):
    name = "slack"

    def __init__(self) -> None:
        self._webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
        self._token   = os.environ.get("SLACK_BOT_TOKEN", "")

    def is_available(self) -> bool:
        return bool(self._webhook or self._token)

    async def post_message(self, text: str, channel: Optional[str] = None) -> bool:
        """Post a message via webhook (fast, no OAuth required)."""
        if not self._webhook:
            logger.warning("[Slack] SLACK_WEBHOOK_URL not set")
            return False
        async with httpx.AsyncClient(timeout=10) as c:
            payload: Dict[str, Any] = {"text": text}
            if channel:
                payload["channel"] = channel
            r = await c.post(self._webhook, json=payload)
            return r.status_code == 200

    async def post_blocks(self, blocks: List[Dict[str, Any]], channel: str) -> Dict[str, Any]:
        """Post rich blocks via Bot token."""
        if not self._token:
            raise ValueError("SLACK_BOT_TOKEN required for blocks API")
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"channel": channel, "blocks": blocks},
            )
            r.raise_for_status()
            return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Stripe connector (read-only)
# ─────────────────────────────────────────────────────────────────────────────

class StripeConnector(ConnectorBase):
    name = "stripe"

    def __init__(self) -> None:
        self._key = os.environ.get("STRIPE_SECRET_KEY", "")

    def is_available(self) -> bool:
        return bool(self._key)

    async def list_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.stripe.com/v1/customers",
                            auth=(self._key, ""),
                            params={"limit": limit})
            r.raise_for_status()
            return r.json().get("data", [])

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
                            auth=(self._key, ""))
            r.raise_for_status()
            return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# ConnectorManager
# ─────────────────────────────────────────────────────────────────────────────

class ConnectorManager:
    """Registry of all connectors.  Access via connector_manager.get(name)."""

    def __init__(self) -> None:
        self._registry: Dict[str, ConnectorBase] = {}
        for cls in [GitHubConnector, RailwayConnector, VercelConnector, SlackConnector, StripeConnector]:
            instance = cls()
            self._registry[instance.name] = instance

    def get(self, name: str) -> Optional[ConnectorBase]:
        return self._registry.get(name)

    def list_available(self) -> List[str]:
        return [name for name, c in self._registry.items() if c.is_available()]

    def status(self) -> Dict[str, bool]:
        return {name: c.is_available() for name, c in self._registry.items()}

    def register(self, connector: ConnectorBase) -> None:
        self._registry[connector.name] = connector


# Module-level singleton
connector_manager = ConnectorManager()
