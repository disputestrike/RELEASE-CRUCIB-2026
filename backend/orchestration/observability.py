"""
Request-scoped context (trace_id, tenant_id, request_id), optional OpenTelemetry, Prometheus HTTP counter.

Enable JSON request lines: CRUCIBAI_STRUCTURED_LOGS=1
Enable OTel tracer (console exporter): CRUCIBAI_OTEL=1
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from contextvars import ContextVar
from typing import Any, Optional

logger = logging.getLogger(__name__)

request_id_cv: ContextVar[str] = ContextVar("crucibai_request_id", default="")
trace_id_cv: ContextVar[str] = ContextVar("crucibai_trace_id", default="")
tenant_id_cv: ContextVar[str] = ContextVar("crucibai_tenant_id", default="")

_http_requests = None


def _http_counter():
    global _http_requests
    if _http_requests is None:
        from prometheus_client import Counter

        _http_requests = Counter(
            "crucibai_http_requests_total",
            "HTTP requests served",
            ["method", "status_class"],
        )
    return _http_requests


def bind_http_request_context(
    *,
    request_id: str,
    trace_id: Optional[str] = None,
    tenant_id: str = "",
) -> None:
    request_id_cv.set(request_id or "")
    trace_id_cv.set(trace_id or str(uuid.uuid4()))
    tenant_id_cv.set((tenant_id or "").strip())


def clear_http_request_context() -> None:
    request_id_cv.set("")
    trace_id_cv.set("")
    tenant_id_cv.set("")


def observe_http_request(method: str, status_code: int) -> None:
    try:
        cls = f"{int(status_code) // 100}xx"
        _http_counter().labels(method=(method or "GET").upper(), status_class=cls).inc()
    except Exception:
        pass


def structured_logs_enabled() -> bool:
    return os.environ.get("CRUCIBAI_STRUCTURED_LOGS", "").strip().lower() in ("1", "true", "yes")


def log_request_event(log: logging.Logger, event: str, **fields: Any) -> None:
    if not structured_logs_enabled():
        return
    payload = {
        "event": event,
        "request_id": request_id_cv.get() or None,
        "trace_id": trace_id_cv.get() or None,
        "tenant_id": tenant_id_cv.get() or None,
        **fields,
    }
    log.info(json.dumps(payload, default=str))


def init_opentelemetry():  # noqa: ANN201
    if os.environ.get("CRUCIBAI_OTEL", "").strip().lower() not in ("1", "true", "yes"):
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        t = trace.get_tracer("crucibai")
        logger.info("OpenTelemetry tracer initialized (console exporter)")
        return t
    except Exception as e:
        logger.warning("OpenTelemetry init skipped: %s", e)
        return None
