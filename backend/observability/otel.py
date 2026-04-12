"""
OpenTelemetry integration for distributed tracing, metrics, and logs.

Implements:
- Distributed tracing with trace context propagation
- Metrics collection (counters, histograms, gauges)
- Automatic instrumentation
- Span creation and management
- Context propagation across services
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3Format
from opentelemetry.propagators.jaeger.jaeger import JaegerPropagator
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class OpenTelemetrySetup:
    """Setup and manage OpenTelemetry instrumentation."""

    def __init__(
        self,
        service_name: str = "crucibai",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        enable_prometheus: bool = True,
    ):
        """
        Initialize OpenTelemetry setup.

        Args:
            service_name: Service name for traces
            jaeger_host: Jaeger collector host
            jaeger_port: Jaeger collector port
            enable_prometheus: Enable Prometheus metrics export
        """
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.enable_prometheus = enable_prometheus

        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None

    def setup_tracing(self) -> TracerProvider:
        """
        Setup distributed tracing with Jaeger.

        Returns:
            Configured TracerProvider
        """
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.jaeger_host,
            agent_port=self.jaeger_port,
        )

        # Create tracer provider
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Setup propagators (Jaeger + B3 for compatibility)
        set_global_textmap(JaegerPropagator())

        self.tracer = trace.get_tracer(__name__)

        logger.info(
            "OpenTelemetry tracing setup complete",
            extra={
                "service": self.service_name,
                "jaeger_host": self.jaeger_host,
                "jaeger_port": self.jaeger_port,
            },
        )

        return self.tracer_provider

    def setup_metrics(self) -> MeterProvider:
        """
        Setup metrics collection.

        Returns:
            Configured MeterProvider
        """
        if self.enable_prometheus:
            # Use Prometheus exporter
            reader = PrometheusMetricReader()
        else:
            # Use periodic exporter
            reader = PeriodicExportingMetricReader(
                exporter=None,  # Would be set to actual exporter
            )

        self.meter_provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(self.meter_provider)

        self.meter = metrics.get_meter(__name__)

        logger.info(
            "OpenTelemetry metrics setup complete",
            extra={"prometheus_enabled": self.enable_prometheus},
        )

        return self.meter_provider

    def setup_instrumentation(self, app=None):
        """
        Setup automatic instrumentation for common libraries.

        Args:
            app: Flask app instance (optional)
        """
        # Instrument Flask
        if app:
            FlaskInstrumentor().instrument_app(app)
            logger.info("Flask instrumented")

        # Instrument requests library
        RequestsInstrumentor().instrument()
        logger.info("Requests library instrumented")

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumented")

        # Instrument psycopg2 (PostgreSQL driver)
        Psycopg2Instrumentor().instrument()
        logger.info("psycopg2 instrumented")

    def create_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a new span.

        Args:
            name: Span name
            attributes: Span attributes

        Returns:
            Span context manager
        """
        if not self.tracer:
            raise RuntimeError("Tracing not initialized")

        span = self.tracer.start_span(name)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        return span

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            unit: Metric unit
            attributes: Metric attributes
        """
        if not self.meter:
            raise RuntimeError("Metrics not initialized")

        # Create counter
        counter = self.meter.create_counter(
            name=name,
            unit=unit,
            description=f"Metric: {name}",
        )

        counter.add(value, attributes or {})


# Global OpenTelemetry instance
otel = None


def init_otel(
    service_name: str = "crucibai",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    app=None,
) -> OpenTelemetrySetup:
    """
    Initialize OpenTelemetry globally.

    Args:
        service_name: Service name
        jaeger_host: Jaeger host
        jaeger_port: Jaeger port
        app: Flask app (optional)

    Returns:
        Configured OpenTelemetrySetup instance
    """
    global otel

    otel = OpenTelemetrySetup(
        service_name=service_name,
        jaeger_host=jaeger_host,
        jaeger_port=jaeger_port,
    )

    otel.setup_tracing()
    otel.setup_metrics()
    otel.setup_instrumentation(app)

    logger.info(f"OpenTelemetry initialized for {service_name}")

    return otel


def trace_function(
    span_name: Optional[str] = None,
    record_args: bool = False,
    record_result: bool = False,
):
    """
    Decorator to trace function execution.

    Args:
        span_name: Custom span name
        record_args: Record function arguments
        record_result: Record function result

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not otel or not otel.tracer:
                return func(*args, **kwargs)

            # Use custom span name or function name
            name = span_name or func.__name__

            with otel.tracer.start_as_current_span(name) as span:
                # Record arguments if requested
                if record_args:
                    span.set_attribute("args", str(args)[:100])
                    span.set_attribute("kwargs", str(kwargs)[:100])

                # Execute function
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)

                    # Record result if requested
                    if record_result:
                        span.set_attribute("result", str(result)[:100])

                    # Record execution time
                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)

                    return result

                except Exception as e:
                    span.set_attribute("error", True)
                    span.set_attribute("error_type", type(e).__name__)
                    span.set_attribute("error_message", str(e)[:100])
                    raise

        return wrapper

    return decorator


def record_metric(
    name: str,
    value: float,
    unit: str = "",
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Record a metric value globally.

    Args:
        name: Metric name
        value: Metric value
        unit: Metric unit
        attributes: Metric attributes
    """
    if otel:
        otel.record_metric(name, value, unit, attributes)


def get_tracer():
    """Get global tracer instance."""
    if otel:
        return otel.tracer
    return None


def get_meter():
    """Get global meter instance."""
    if otel:
        return otel.meter
    return None
