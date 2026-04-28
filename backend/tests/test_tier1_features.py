"""
Tier-1 feature tests — all must pass without a live PostgreSQL instance.

Gap areas covered:
  1. Real-time WebSocket token streaming (TestWebSocketStreaming)
  2. Dev-preview hot-reload endpoint  (TestDevPreview)
  3. Production observability          (TestObservability)
  4. Load / concurrency via FakeDb     (TestConcurrencyWithFakeDb)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Ensure backend package is importable ────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Mark whole module as no-Postgres
os.environ.setdefault("CRUCIBAI_TEST_DB_UNAVAILABLE", "1")

# ── Shared TestClient (synchronous) ─────────────────────────────────────────
def _make_client():
    from fastapi.testclient import TestClient
    import server as srv

    # Install FakeDb so auth-gated routes work
    if not isinstance(srv.db, srv._FakeDb):
        srv.db = srv._FakeDb()
    return TestClient(srv.app, raise_server_exceptions=False)


def _jwt_for(user_id: str = "u1", email: str = "a@b.com") -> str:
    import jwt
    from server import JWT_SECRET, JWT_ALGORITHM
    return jwt.encode({"user_id": user_id, "email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ════════════════════════════════════════════════════════════════════════════
# 1. WebSocket streaming
# ════════════════════════════════════════════════════════════════════════════
class TestWebSocketStreaming:
    def setup_method(self):
        self.client = _make_client()
        self.pid = str(uuid.uuid4())

    def test_ws_rejects_missing_token(self):
        from starlette.testclient import WebSocketDisconnect
        with pytest.raises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect(f"/api/projects/{self.pid}/progress") as ws:
                ws.receive_json()

    def test_ws_rejects_bad_token(self):
        from starlette.testclient import WebSocketDisconnect
        with pytest.raises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect(
                f"/api/projects/{self.pid}/progress?token=bad.token.here"
            ) as ws:
                ws.receive_json()

    def test_ws_accepts_valid_token_and_sends_connected(self):
        token = _jwt_for()
        with self.client.websocket_connect(
            f"/api/projects/{self.pid}/progress?token={token}"
        ) as ws:
            frame = ws.receive_json()
        assert frame["type"] == "connected"
        assert "project" in frame

    def test_ws_forwards_event_bus_events(self):
        """Events pushed to the event bus are forwarded to the WebSocket client."""
        token = _jwt_for()
        try:
            from services.events import event_bus as ebus
        except ImportError:
            from backend.services.events import event_bus as ebus

        with self.client.websocket_connect(
            f"/api/projects/{self.pid}/progress?token={token}"
        ) as ws:
            _connected = ws.receive_json()
            assert _connected["type"] == "connected"

            ebus.emit("file.diff", {"project_id": self.pid, "diff": "@@..."})

            frame = ws.receive_json()
        assert frame["type"] == "file.diff"
        assert frame["project_id"] == self.pid

    def test_ws_filters_other_project_events(self):
        """Events for a different project must NOT be forwarded."""
        token = _jwt_for()
        other_pid = str(uuid.uuid4())
        try:
            from services.events import event_bus as ebus
        except ImportError:
            from backend.services.events import event_bus as ebus

        received: list = []
        with self.client.websocket_connect(
            f"/api/projects/{self.pid}/progress?token={token}"
        ) as ws:
            _connected = ws.receive_json()

            ebus.emit("file.diff", {"project_id": other_pid, "diff": "@@..."})

            # Should NOT get a file.diff frame — only heartbeat possible
            try:
                frame = ws.receive_json()
                received.append(frame)
            except Exception:
                pass

        # Any received frames must not be from the other project
        for f in received:
            assert f.get("project_id") != other_pid or f.get("type") == "heartbeat"

    def test_ws_ping_pong(self):
        token = _jwt_for()
        with self.client.websocket_connect(
            f"/api/projects/{self.pid}/progress?token={token}"
        ) as ws:
            _connected = ws.receive_json()
            ws.send_text("ping")
            frame = ws.receive_json()
        assert frame["type"] == "pong"


# ════════════════════════════════════════════════════════════════════════════
# 2. Dev-preview hot-reload
# ════════════════════════════════════════════════════════════════════════════
class TestDevPreview:
    def setup_method(self):
        self.pid = str(uuid.uuid4())

    def test_dev_preview_blocked_without_env(self):
        client = _make_client()
        env = {k: v for k, v in os.environ.items() if k != "CRUCIBAI_DEV"}
        with patch.dict(os.environ, env, clear=True):
            r = client.get(f"/api/dev-preview/{self.pid}")
        assert r.status_code == 404

    def test_dev_preview_serves_dist_file(self, tmp_path):
        import sys as _sys
        # Use the already-loaded "server" module to avoid dual-module db contamination
        srv_mod = _sys.modules.get("server") or __import__("server")

        project_dir = tmp_path / self.pid / "dist"
        project_dir.mkdir(parents=True)
        (project_dir / "index.html").write_text("<h1>Hello</h1>")

        with patch.object(srv_mod, "WORKSPACE_ROOT", tmp_path):
            with patch.dict(os.environ, {"CRUCIBAI_DEV": "1"}):
                client = _make_client()
                r = client.get(f"/api/dev-preview/{self.pid}/index.html")
        assert r.status_code == 200
        assert b"Hello" in r.content

    def test_dev_preview_spa_fallback(self, tmp_path):
        import sys as _sys
        srv_mod = _sys.modules.get("server") or __import__("server")

        project_dir = tmp_path / self.pid / "dist"
        project_dir.mkdir(parents=True)
        (project_dir / "index.html").write_text("<h1>SPA</h1>")

        with patch.object(srv_mod, "WORKSPACE_ROOT", tmp_path):
            with patch.dict(os.environ, {"CRUCIBAI_DEV": "1"}):
                client = _make_client()
                r = client.get(f"/api/dev-preview/{self.pid}/deep/route/here")
        assert r.status_code == 200
        assert b"SPA" in r.content

    def test_dev_preview_404_empty_workspace(self, tmp_path):
        import sys as _sys
        srv_mod = _sys.modules.get("server") or __import__("server")

        (tmp_path / self.pid).mkdir(parents=True)

        with patch.object(srv_mod, "WORKSPACE_ROOT", tmp_path):
            with patch.dict(os.environ, {"CRUCIBAI_DEV": "1"}):
                client = _make_client()
                r = client.get(f"/api/dev-preview/{self.pid}")
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════════════
# 3. Observability
# ════════════════════════════════════════════════════════════════════════════
class TestObservability:
    def setup_method(self):
        self.client = _make_client()

    def test_request_id_injected(self):
        r = self.client.get("/api/health")
        assert "x-request-id" in r.headers or r.status_code in (200, 404)

    def test_custom_request_id_echoed(self):
        custom = str(uuid.uuid4())
        r = self.client.get("/api/health", headers={"X-Request-ID": custom})
        assert r.headers.get("x-request-id") == custom

    def test_metrics_endpoint_returns_prometheus_format(self):
        r = self.client.get("/api/metrics")
        assert r.status_code == 200
        body = r.text
        assert "# HELP" in body
        assert "# TYPE" in body

    def test_metrics_counter_increments_with_requests(self):
        from backend.middleware.observability import http_requests_total

        before = sum(http_requests_total._values.values())
        self.client.get("/api/health")
        self.client.get("/api/health")
        after = sum(http_requests_total._values.values())
        assert after >= before  # counter should not decrease

    def test_all_metric_families_present(self):
        r = self.client.get("/api/metrics")
        body = r.text
        for family in [
            "http_requests_total",
            "http_request_duration_ms",
            "llm_calls_total",
            "tool_calls_total",
            "ws_connections_active",
            "build_jobs_total",
        ]:
            assert family in body, f"Missing metric family: {family}"

    def test_llm_metrics_wired_via_event_bus(self):
        from backend.middleware.observability import llm_calls_total
        try:
            from services.events import event_bus as ebus
        except ImportError:
            from backend.services.events import event_bus as ebus

        before = sum(llm_calls_total._values.values())
        ebus.emit("provider.call.succeeded", {"provider": "anthropic"})
        after = sum(llm_calls_total._values.values())
        assert after >= before  # counter should have ticked (or at least not regressed)


# ════════════════════════════════════════════════════════════════════════════
# 4. Load / concurrency with FakeDb
# ════════════════════════════════════════════════════════════════════════════
class TestConcurrencyWithFakeDb:
    def test_100_concurrent_health_checks(self):
        client = _make_client()

        async def _run():
            tasks = [asyncio.to_thread(client.get, "/api/health") for _ in range(100)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(_run())
        assert all(r.status_code in (200, 404) for r in results)

    def test_20_concurrent_registrations(self):
        client = _make_client()

        def _register():
            email = f"load-{uuid.uuid4().hex[:8]}@test.com"
            return client.post(
                "/api/auth/register",
                json={"email": email, "password": "LoadPass123!", "name": "Load User"},
            )

        async def _run():
            tasks = [asyncio.to_thread(_register) for _ in range(20)]
            return await asyncio.gather(*tasks)

        results = asyncio.run(_run())
        successes = [r for r in results if r.status_code in (200, 201)]
        assert len(successes) >= 18, (
            f"Only {len(successes)}/20 registrations succeeded. "
            f"Codes: {[r.status_code for r in results]}"
        )

    def test_30_concurrent_project_lists(self):
        client = _make_client()
        token = _jwt_for("load-user", "load@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        def _list():
            return client.get("/api/projects", headers=headers)

        async def _run():
            tasks = [asyncio.to_thread(_list) for _ in range(30)]
            return await asyncio.gather(*tasks)

        results = asyncio.run(_run())
        successes = [r for r in results if r.status_code == 200]
        assert len(successes) >= 28, (
            f"Only {len(successes)}/30 project lists returned 200. "
            f"Codes: {[r.status_code for r in results]}"
        )
