"""
Metrics route — Prometheus exposition endpoint.

Exposes application metrics in Prometheus text format for scraping.
"""

from fastapi import APIRouter
from starlette.responses import Response

from api.services.metrics_service import get_metrics, get_content_type

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Returns application metrics in Prometheus exposition format. "
    "Scrape this endpoint with Prometheus.",
    response_class=Response,
)
async def metrics() -> Response:
    """
    Expose Prometheus metrics.

    Returns all registered metrics (counters, histograms, gauges)
    in Prometheus text exposition format.
    """
    return Response(
        content=get_metrics(),
        media_type=get_content_type(),
    )
