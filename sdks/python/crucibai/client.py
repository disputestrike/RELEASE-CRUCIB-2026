"""CrucibAI Python SDK — synchronous + async client."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class _RunsNamespace:
    def __init__(self, client: "CrucibAI") -> None:
        self._c = client

    def create(
        self,
        prompt: str,
        thread_id: Optional[str] = None,
        mode: str = "build",
    ) -> Dict[str, Any]:
        """POST /api/runs/{thread_id}/preview-loop"""
        tid = thread_id or "default"
        return self._c._post(
            f"/api/runs/{tid}/preview-loop",
            json={"url": "https://localhost", "dry_run": True, "_prompt": prompt, "_mode": mode},
        )


class _BenchmarksNamespace:
    def __init__(self, client: "CrucibAI") -> None:
        self._c = client

    def latest(self) -> Dict[str, Any]:
        """GET /api/benchmarks/latest"""
        return self._c._get("/api/benchmarks/latest")


class _MarketplaceNamespace:
    def __init__(self, client: "CrucibAI") -> None:
        self._c = client

    def listings(self, kind: Optional[str] = None) -> Dict[str, Any]:
        """GET /api/marketplace/listings"""
        params = {}
        if kind:
            params["kind"] = kind
        return self._c._get("/api/marketplace/listings", params=params)


class CrucibAI:
    """CrucibAI API client.

    Parameters
    ----------
    api_key:
        Your ``crc_…`` API key from the Developer Portal.
    base_url:
        Override the default API base URL.
    timeout:
        Request timeout in seconds (default 30).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.crucibai.com",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        self.runs = _RunsNamespace(self)
        self.benchmarks = _BenchmarksNamespace(self)
        self.marketplace = _MarketplaceNamespace(self)

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        r = self._http.get(path, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        r = self._http.post(path, json=json or {})
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "CrucibAI":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
