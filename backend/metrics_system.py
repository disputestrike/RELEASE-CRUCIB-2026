"""
Metrics collection system for CrucibAI.

Tracks performance metrics, error rates, and operational data.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram, Summary


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""

    timestamp: datetime
    build_count: int
    successful_builds: int
    failed_builds: int
    average_build_time_ms: float
    error_rate_percent: float
    agent_executions: int
    average_agent_time_ms: float
    active_agents: int
    queue_depth: int
    memory_usage_mb: float
    cpu_usage_percent: float
    database_connections: int
    cache_hit_rate_percent: float


class MetricsCollector:
    """Collects and tracks metrics for CrucibAI."""

    def __init__(self):
        """Initialize metrics collector."""
        # Build metrics
        self.builds_total = Counter(
            "crucibai_builds_total",
            "Total number of builds",
            ["status"],
        )
        self.build_duration_seconds = Histogram(
            "crucibai_build_duration_seconds",
            "Build duration in seconds",
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
        )
        self.build_queue_depth = Gauge(
            "crucibai_build_queue_depth",
            "Number of builds in queue",
        )

        # Agent metrics
        self.agent_executions_total = Counter(
            "crucibai_agent_executions_total",
            "Total agent executions",
            ["agent_name", "status"],
        )
        self.agent_duration_seconds = Histogram(
            "crucibai_agent_duration_seconds",
            "Agent execution duration in seconds",
            ["agent_name"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1, 5),
        )
        self.active_agents = Gauge(
            "crucibai_active_agents",
            "Number of currently active agents",
        )

        # Error metrics
        self.errors_total = Counter(
            "crucibai_errors_total",
            "Total errors",
            ["error_type"],
        )
        self.verification_runs_total = Counter(
            "crucibai_verification_runs_total",
            "Auto-Runner verify_step outcomes per step_key",
            ["step_key", "outcome"],
        )

        self.error_rate = Gauge(
            "crucibai_error_rate_percent",
            "Current error rate as percentage",
        )

        # Resource metrics
        self.memory_usage_bytes = Gauge(
            "crucibai_memory_usage_bytes",
            "Memory usage in bytes",
        )
        self.cpu_usage_percent = Gauge(
            "crucibai_cpu_usage_percent",
            "CPU usage as percentage",
        )

        # Database metrics
        self.database_connections = Gauge(
            "crucibai_database_connections",
            "Number of database connections",
        )
        self.database_query_duration_seconds = Histogram(
            "crucibai_database_query_duration_seconds",
            "Database query duration in seconds",
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1),
        )

        # API metrics
        self.api_requests_total = Counter(
            "crucibai_api_requests_total",
            "Total API requests",
            ["method", "endpoint", "status"],
        )
        self.api_request_duration_seconds = Histogram(
            "crucibai_api_request_duration_seconds",
            "API request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1, 5),
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            "crucibai_cache_hits_total",
            "Total cache hits",
        )
        self.cache_misses_total = Counter(
            "crucibai_cache_misses_total",
            "Total cache misses",
        )

        # Cost metrics
        self.build_cost_dollars = Summary(
            "crucibai_build_cost_dollars",
            "Cost of each build in dollars",
        )
        self.total_cost_dollars = Gauge(
            "crucibai_total_cost_dollars",
            "Total cumulative cost in dollars",
        )

        # Historical data
        self.build_history: List[Dict] = []
        self.agent_history: List[Dict] = []
        self.error_history: List[Dict] = []

    def record_build_start(self, build_id: str):
        """Record start of a build."""
        self.build_queue_depth.inc()

    def record_build_complete(self, build_id: str, duration_seconds: float, status: str, cost_dollars: float = 0.0):
        """Record completion of a build."""
        self.builds_total.labels(status=status).inc()
        self.build_duration_seconds.observe(duration_seconds)
        self.build_queue_depth.dec()
        self.build_cost_dollars.observe(cost_dollars)

        self.build_history.append({
            "build_id": build_id,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": duration_seconds,
            "status": status,
            "cost_dollars": cost_dollars,
        })

    def record_agent_execution(self, agent_name: str, duration_seconds: float, status: str):
        """Record agent execution."""
        self.agent_executions_total.labels(agent_name=agent_name, status=status).inc()
        self.agent_duration_seconds.labels(agent_name=agent_name).observe(duration_seconds)

        self.agent_history.append({
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": duration_seconds,
            "status": status,
        })

    def record_error(self, error_type: str):
        """Record an error."""
        self.errors_total.labels(error_type=error_type).inc()
        self.error_history.append({
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def set_active_agents(self, count: int):
        """Set the number of active agents."""
        self.active_agents.set(count)

    def set_memory_usage(self, bytes_used: int):
        """Set memory usage in bytes."""
        self.memory_usage_bytes.set(bytes_used)

    def set_cpu_usage(self, percent: float):
        """Set CPU usage percentage."""
        self.cpu_usage_percent.set(percent)

    def set_database_connections(self, count: int):
        """Set number of database connections."""
        self.database_connections.set(count)

    def record_database_query(self, duration_seconds: float):
        """Record database query duration."""
        self.database_query_duration_seconds.observe(duration_seconds)

    def record_api_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record API request."""
        self.api_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
        self.api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration_seconds)

    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits_total.inc()

    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses_total.inc()

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate as percentage."""
        total_hits = self.cache_hits_total._value.get()
        total_misses = self.cache_misses_total._value.get()
        total = total_hits + total_misses
        if total == 0:
            return 0.0
        return (total_hits / total) * 100

    def get_error_rate(self) -> float:
        """Get error rate as percentage."""
        total_builds = self.builds_total.labels(status="success")._value.get() + \
                       self.builds_total.labels(status="failure")._value.get()
        if total_builds == 0:
            return 0.0
        failed_builds = self.builds_total.labels(status="failure")._value.get()
        return (failed_builds / total_builds) * 100

    def get_snapshot(self) -> MetricSnapshot:
        """Get a snapshot of current metrics."""
        successful_builds = self.builds_total.labels(status="success")._value.get()
        failed_builds = self.builds_total.labels(status="failure")._value.get()
        total_builds = successful_builds + failed_builds

        # Calculate average build time
        if self.build_history:
            avg_build_time = sum(b["duration_seconds"] for b in self.build_history) / len(self.build_history) * 1000
        else:
            avg_build_time = 0.0

        # Calculate average agent time
        if self.agent_history:
            avg_agent_time = sum(a["duration_seconds"] for a in self.agent_history) / len(self.agent_history) * 1000
        else:
            avg_agent_time = 0.0

        return MetricSnapshot(
            timestamp=datetime.utcnow(),
            build_count=total_builds,
            successful_builds=successful_builds,
            failed_builds=failed_builds,
            average_build_time_ms=avg_build_time,
            error_rate_percent=self.get_error_rate(),
            agent_executions=len(self.agent_history),
            average_agent_time_ms=avg_agent_time,
            active_agents=int(self.active_agents._value.get()),
            queue_depth=int(self.build_queue_depth._value.get()),
            memory_usage_mb=int(self.memory_usage_bytes._value.get()) / (1024 * 1024),
            cpu_usage_percent=float(self.cpu_usage_percent._value.get()),
            database_connections=int(self.database_connections._value.get()),
            cache_hit_rate_percent=self.get_cache_hit_rate(),
        )

    def get_build_history(self, limit: int = 100) -> List[Dict]:
        """Get recent build history."""
        return self.build_history[-limit:]

    def get_agent_history(self, limit: int = 100) -> List[Dict]:
        """Get recent agent history."""
        return self.agent_history[-limit:]

    def get_error_history(self, limit: int = 100) -> List[Dict]:
        """Get recent error history."""
        return self.error_history[-limit:]


# Global metrics collector
metrics = MetricsCollector()
