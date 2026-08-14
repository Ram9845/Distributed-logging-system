"""
FastAPI middleware for request tracking, timing, and metrics.

Adds request IDs, correlation IDs, and timing headers to every
response, and records Prometheus metrics for HTTP requests.
"""

import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from api.utils.helpers import generate_request_id
from api.services.metrics_service import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
)


logger = structlog.get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique request ID and correlation ID
    to each incoming request, measures request duration, and binds
    contextual fields to structlog for the request lifecycle.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate or extract request/correlation IDs
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        correlation_id = request.headers.get(
            "X-Correlation-ID", request_id
        )

        # Bind IDs to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed with unhandled exception",
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Attach tracking headers to the response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))

            # Record Prometheus Metrics
            endpoint = request.url.path
            method = request.method
            status_code = str(response.status_code)
            
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=method, endpoint=endpoint
            ).observe(duration_ms / 1000.0)

            # Log the completed request
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            return response
