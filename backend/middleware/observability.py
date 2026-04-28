"""
Production observability middleware for CrucibAI.
Provides:
  - Structured JSON request logging (CRUCIBAI_JSON_LOGS=1)
  - Prometheus-format metrics at /api/metrics
  - X-Request-ID / X-Correlation-ID headers
  - Event-bus wiring for LLM/tool/build counters
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ── ContextVars for per-request tracing ──────────────────────────────────────
current_request_id: ContextVar[str] = ContextVar("request_id", default="")
current_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


# ── Tiny Prometheus-compatible metric primitives ──────────────────────────────

class _Counter:
    def __init__(self, name: str, help_text: str, label_names: tuple = ()):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names
        self._values: Dict[tuple, float] = {}

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0):
        key = tuple((labels or {}).get(n, "") for n in self.label_names)
        self._values[key] = self._values.get(key, 0.0) + amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} counter"]
        for key, val in self._values.items():
            if key:
                labels = ",".join(f'{n}="{v}"' for n, v in zip(self.label_names, key))
                lines.append(f"{self.name}{{{labels}}} {val}")
            else:
                lines.append(f"{self.name} {val}")
        return "\n".join(lines)


class _Histogram:
    def __init__(self, name: str, help_text: str, label_names: tuple = ()):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names
        self._sum: Dict[tuple, float] = {}
        self._count: Dict[tuple, int] = {}

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        key = tuple((labels or {}).get(n, "") for n in self.label_names)
        self._sum[key] = self._sum.get(key, 0.0) + value
        self._count[key] = self._count.get(key, 0) + 1

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} histogram"]
        for key in set(list(self._sum.keys()) + list(self._count.keys())):
            if key:
                labels = ",".join(f'{n}="{v}"' for n, v in zip(self.label_names, key))
                lines.append(f"{self.name}_sum{{{labels}}} {self._sum.get(key, 0.0)}")
                lines.append(f"{self.name}_count{{{labels}}} {self._count.get(key, 0)}")
            else:
                lines.append(f"{self.name}_sum {self._sum.get(key, 0.0)}")
                lines.append(f"{self.name}_count {self._count.get(key, 0)}")
        return "\n".join(lines)


class _Gauge:
    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help_text = help_text
        self._value: float = 0.0

    def inc(self, amount: float = 1.0):
        self._value += amount

    def dec(self, amount: float = 1.0):
        self._value -= amount

    def set(self, value: float):
        self._value = value

    def render(self) -> str:
        return "\n".join([
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} gauge",
            f"{self.name} {self._value}",
        ])


# ── Global metric instances ───────────────────────────────────────────────────
http_requests_total = _Counter(
    "http_requests_total",
    "Total HTTP requests",
    label_names=("method", "path", "status"),
)
http_request_duration_ms = _Histogram(
    "http_request_duration_ms",
    "HTTP request duration in milliseconds",
    label_names=("method", "path"),
)
llm_calls_total = _Counter(
    "llm_calls_total",
    "Total LLM provider calls",
    label_names=("provider", "status"),
)
tool_calls_total = _Counter(
    "tool_calls_total",
    "Total agent tool calls",
    label_names=("tool",),
)
ws_connections_active = _Gauge(
    "ws_connections_active",
    "Currently active WebSocket connections",
)
build_jobs_total = _Counter(
    "build_jobs_total",
    "Total build jobs started",
    label_names=("status",),
)

_ALL_METRICS = [
    http_requests_total,
    http_request_duration_ms,
    llm_calls_total,
    tool_calls_total,
    ws_connections_active,
    build_jobs_total,
]


def render_metrics() -> str:
    """Render all metrics in Prometheus text exposition format."""
    parts = []
    for m in _ALL_METRICS:
        rendered = m.render()
        if rendered:
            parts.append(rendered)
    return "\n".join(parts) + "\n"


# ── Path normalisation (cardinality control) ──────────────────────────────────
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_LONG_NUM_RE = re.compile(r"/\d{4,}")


def _normalise_path(path: str) -> str:
    path = _UUID_RE.sub("{id}", path)
    path = _LONG_NUM_RE.sub("/{id}", path)
    return path


# ── Middleware ────────────────────────────────────────────────────────────────
import os as _os


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID") or req_id
        token_rid = current_request_id.set(req_id)
        token_cid = current_correlation_id.set(corr_id)

        t0 = time.monotonic()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            response = Response(content="Internal Server Error", status_code=500)
            raise exc
        finally:
            elapsed_ms = (time.monotonic() - t0) * 1000
            path = _normalise_path(request.url.path)
            method = request.method
            status = getattr(response, "status_code", 0)

            http_requests_total.inc({"method": method, "path": path, "status": str(status)})
            http_request_duration_ms.observe(elapsed_ms, {"method": method, "path": path})

            skip_log = request.url.path in ("/api/health", "/api/healthz", "/api/metrics", "/__routes")
            if not skip_log and _os.environ.get("CRUCIBAI_JSON_LOGS") == "1":
                log_record = {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "method": method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": round(elapsed_ms, 2),
                    "request_id": req_id,
                    "correlation_id": corr_id,
                }
                logger.info(json.dumps(log_record))

            current_request_id.reset(token_rid)
            current_correlation_id.reset(token_cid)

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Correlation-ID"] = corr_id
        return response


# ── Wire event bus → metric counters ─────────────────────────────────────────
def _wire_event_bus_metrics() -> None:
    """Subscribe to event bus and increment counters for LLM/tool/build events."""
    try:
        try:
            from services.events import event_bus as _ebus
        except ImportError:
            from backend.services.events import event_bus as _ebus

        def _handle(record: Any) -> None:
            try:
                ev = record.event_type if hasattr(record, "event_type") else str(record)
                payload = record.payload if hasattr(record, "payload") else {}
                if ev in ("provider.call.succeeded", "provider.call.failed"):
                    provider = payload.get("provider", "unknown")
                    status = "ok" if ev.endswith("succeeded") else "error"
                    llm_calls_total.inc({"provider": provider, "status": status})
                elif ev == "tool.end":
                    tool = payload.get("tool", "unknown")
                    tool_calls_total.inc({"tool": tool})
                elif ev in ("build.started", "build.completed", "build.failed"):
                    status = ev.split(".")[-1]
                    build_jobs_total.inc({"status": status})
            except Exception:
                pass

        _ebus.subscribe("*", _handle)
    except Exception:
        pass


try:
    _wire_event_bus_metrics()
except Exception:
    pass
