"""
Monitoring and metrics router.
Exposes Prometheus /api/metrics and health-style endpoints.
"""
from fastapi import APIRouter
from starlette.responses import Response, PlainTextResponse

router = APIRouter(prefix="/api", tags=["monitoring"])

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    _metrics_available = True
except ImportError:
    _metrics_available = False


@router.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics for Grafana scraping."""
    if not _metrics_available:
        return PlainTextResponse("# metrics not available\n", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
