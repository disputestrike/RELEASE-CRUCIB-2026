"""
Workspace artifacts for observability goals — stubs only, not a production stack.
Triggered when the goal mentions tracing, OpenTelemetry, Prometheus, Grafana, metrics, or structured logs.
"""
from __future__ import annotations

import re
from typing import Any, Dict


def _g(job_or_goal: Any) -> str:
    if isinstance(job_or_goal, str):
        return (job_or_goal or "").lower()
    return (job_or_goal.get("goal") or "").lower()


def observability_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    g = _g(job_or_goal)
    return bool(
        re.search(
            r"\b(opentelemetry|open telemetry|otel|distributed trace|tracing|jaeger|tempo|zipkin|"
            r"prometheus|grafana|loki|metrics|slo|sli|observability|structured log|json log|"
            r"datadog|new relic|honeycomb)\b",
            g,
        )
    )


def build_observability_pack_markdown(goal_excerpt: str) -> str:
    ex = ((goal_excerpt or "").strip()[:400] or "(no goal text)").replace("\n", " ")
    return f"""# Observability pack (stub)

**Auto-Runner** added this pack because your goal mentioned tracing, metrics, or dashboards.
These files are **starting points** — wire credentials, networks, and retention before production.

## Goal excerpt

> {ex}

## What was added

| Path | Purpose |
|------|---------|
| `deploy/observability/docker-compose.observability.stub.yml` | Local stack: OTel Collector + Prometheus + Grafana |
| `deploy/observability/otel-collector-config.stub.yaml` | Receiver / exporter skeleton |
| `deploy/observability/prometheus.stub.yml` | Scrape `api:8000/metrics` + OTLP targets (adjust labels) |
| `deploy/observability/grafana/provisioning/datasources/datasource.stub.yml` | Prometheus datasource for Grafana |

## Backend integration (your repo)

1. **Structured logs** — use JSON logs with `request_id` / `trace_id` fields; avoid PII in log lines.
2. **OpenTelemetry** — install SDK for your stack (Python: `opentelemetry-distro`, `opentelemetry-instrumentation-fastapi`);
   export traces to the collector (OTLP gRPC/HTTP).
3. **Prometheus** — expose `/metrics` (e.g. `prometheus_client` for FastAPI) and scrape from Prometheus config.
4. **Grafana** — import dashboards from grafana.com or build panels on the Prometheus datasource.

## CrucibAI host API

The main CrucibAI backend already exposes `/metrics` when `prometheus_client` is installed and can initialize OTel
via `observability/otel.py` when dependencies are present — **generated workspaces** need their own wiring.

_Schema: crucibai.observability_pack/v1_
"""


def docker_compose_observability_stub() -> str:
    return """# Stub: local observability — customize image tags and ports for your environment.
# Usage (from repo root): docker compose -f deploy/observability/docker-compose.observability.stub.yml up -d
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.96.0
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.stub.yaml:/etc/otel-collector-config.yaml:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8889:8889"   # Prometheus exporter (collector self-metrics)
    networks: [obs]

  prometheus:
    image: prom/prometheus:v2.49.1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --web.enable-lifecycle
    volumes:
      - ./prometheus.stub.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    networks: [obs]

  grafana:
    image: grafana/grafana:10.3.1
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "change-me"
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3001:3000"
    depends_on: [prometheus]
    networks: [obs]

networks:
  obs:
    driver: bridge
"""


def otel_collector_config_stub() -> str:
    return """# OpenTelemetry Collector — stub. Add processors (batch, memory_limiter) and real exporters.
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  batch: {}

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  debug:
    verbosity: basic
  # otlp:
  #   endpoint: jaeger:4317
  #   tls:
  #     insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, debug]
"""


def prometheus_config_stub() -> str:
    return """# Prometheus scrape config — stub. Point targets at your API and collector.
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: otel-collector
    static_configs:
      - targets: ["otel-collector:8889"]

  # Uncomment when your API exposes /metrics on the Docker network:
  # - job_name: api
  #   static_configs:
  #     - targets: ["api:8000"]
  #   metrics_path: /metrics
"""


def grafana_datasource_stub() -> str:
    return """# Grafana datasource provisioning — stub
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
"""


def fastapi_observability_snippet_py() -> str:
    return '''"""
Optional observability snippet for generated FastAPI apps — merge into main.py or routers as needed.
Requires: pip install prometheus-client opentelemetry-api opentelemetry-sdk (and instrumentation packages).
"""
# Example only — not executed automatically.
#
# from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
# from fastapi import Response
#
# REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path"])
#
# @app.get("/metrics")
# def metrics():
#     return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
#
# # OpenTelemetry: use opentelemetry-instrumentation-fastapi and OTLP exporter to collector.
'''
