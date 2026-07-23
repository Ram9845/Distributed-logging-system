"""
Health check route — deep component health verification.

Checks connectivity to PostgreSQL, Kafka, and Redis, reporting
individual component status and overall system health.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_kafka_service, get_redis
from api.schemas.response_schema import HealthResponse, ComponentHealth

router = APIRouter(tags=["Health"])

# Track application start time for uptime calculation
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Deep health check that verifies connectivity to all "
    "dependent services: PostgreSQL, Kafka, and Redis.",
)
async def health_check(
    session: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """
    Perform a deep health check.

    Individually checks each component (database, Kafka, Redis)
    and returns their status along with overall system health.
    """
    components: dict[str, ComponentHealth] = {}
    overall_healthy = True

    # ---- PostgreSQL ----
    try:
        start = time.perf_counter()
        await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        components["postgresql"] = ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
            message="Connection OK",
        )
    except Exception as e:
        overall_healthy = False
        components["postgresql"] = ComponentHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:200]}",
        )

    # ---- Kafka ----
    try:
        start = time.perf_counter()
        kafka = await get_kafka_service()
        healthy = await kafka.health_check()
        latency = (time.perf_counter() - start) * 1000
        if healthy:
            components["kafka"] = ComponentHealth(
                status="healthy",
                latency_ms=round(latency, 2),
                message="Broker connectivity OK",
            )
        else:
            overall_healthy = False
            components["kafka"] = ComponentHealth(
                status="unhealthy",
                message="Broker unreachable",
            )
    except Exception as e:
        overall_healthy = False
        components["kafka"] = ComponentHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:200]}",
        )

    # ---- Redis ----
    try:
        start = time.perf_counter()
        redis = await get_redis()
        if redis:
            await redis.ping()
            latency = (time.perf_counter() - start) * 1000
            components["redis"] = ComponentHealth(
                status="healthy",
                latency_ms=round(latency, 2),
                message="Connection OK",
            )
        else:
            components["redis"] = ComponentHealth(
                status="degraded",
                message="Redis client not initialized (optional)",
            )
    except Exception as e:
        # Redis is optional, so degraded rather than unhealthy
        components["redis"] = ComponentHealth(
            status="degraded",
            message=f"Connection failed (optional): {str(e)[:200]}",
        )

    uptime = time.time() - _start_time

    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        components=components,
        version="1.0.0",
        uptime_seconds=round(uptime, 2),
    )
