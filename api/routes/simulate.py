"""
Simulation routes — generate test logs and errors.

Provides endpoints to simulate log generation from multiple
microservices and to trigger error bursts for alert testing.
"""

import random
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_kafka_service
from api.repository.log_repository import LogRepository
from api.services.log_service import LogService
from api.services.kafka_service import KafkaService
from api.services.metrics_service import record_log_metric
from api.schemas.log_schema import SimulateRequest, GenerateErrorsRequest
from api.schemas.response_schema import APIResponse
from api.utils.constants import (
    SERVICES,
    LOG_LEVELS,
    LOG_LEVEL_WEIGHTS,
    SERVICE_ENDPOINTS,
    STATUS_CODES_BY_LEVEL,
    ERROR_MESSAGES,
)
from api.utils.helpers import generate_trace_id, generate_request_id

router = APIRouter(tags=["Simulation"])


def _generate_single_log(
    service: str | None = None,
    force_level: str | None = None,
    error_rate: float = 0.15,
) -> dict:
    """
    Generate a single realistic log entry.

    Args:
        service: Force a specific service (random if None).
        force_level: Force a specific level (weighted random if None).
        error_rate: Probability of generating an error log.
    """
    svc = service or random.choice(SERVICES)

    # Determine log level based on weights or forced value
    if force_level:
        level = force_level
    else:
        # Adjust weights based on error_rate
        weights = dict(LOG_LEVEL_WEIGHTS)
        weights["ERROR"] = error_rate * 0.75
        weights["CRITICAL"] = error_rate * 0.25
        remaining = 1.0 - error_rate
        weights["INFO"] = remaining * 0.6
        weights["WARNING"] = remaining * 0.25
        weights["DEBUG"] = remaining * 0.15

        level = random.choices(
            LOG_LEVELS, weights=[weights[l] for l in LOG_LEVELS], k=1
        )[0]

    endpoint = random.choice(SERVICE_ENDPOINTS.get(svc, ["/unknown"]))
    status_code = random.choice(STATUS_CODES_BY_LEVEL.get(level, [200]))

    # Generate realistic latency (higher for errors)
    if level in ("ERROR", "CRITICAL"):
        latency = random.uniform(200, 1500)
    elif level == "WARNING":
        latency = random.uniform(100, 600)
    else:
        latency = random.uniform(5, 150)

    # Pick an appropriate message
    level_messages = ERROR_MESSAGES.get(svc, {}).get(level, [])
    if not level_messages:
        level_messages = ERROR_MESSAGES.get(svc, {}).get("INFO", ["Request processed"])
    message = random.choice(level_messages)

    # Random timestamp within the last 5 minutes for realism
    offset_seconds = random.uniform(0, 300)
    timestamp = datetime.now(timezone.utc) - timedelta(seconds=offset_seconds)

    return {
        "timestamp": timestamp.isoformat(),
        "service": svc,
        "level": level,
        "endpoint": endpoint,
        "latency_ms": round(latency, 2),
        "status_code": status_code,
        "trace_id": generate_trace_id(),
        "request_id": generate_request_id(),
        "message": message,
        "metadata": {
            "environment": "production",
            "region": random.choice(["us-east-1", "eu-west-1", "ap-south-1"]),
            "host": f"{svc.replace('-service', '')}-{random.randint(1, 5)}",
        },
    }


# =============================================================================
# POST /simulate — Generate simulated logs
# =============================================================================

@router.post(
    "/simulate",
    response_model=APIResponse,
    summary="Simulate log generation",
    description="Generate realistic log entries from simulated microservices "
    "and publish them to Kafka. Optionally store directly in the database.",
)
async def simulate_logs(
    request: SimulateRequest = SimulateRequest(),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Generate simulated log entries.

    Produces realistic logs with varied levels, latencies, and messages,
    publishes them to Kafka, and stores them in PostgreSQL.
    """
    log_service = LogService(LogRepository(session))

    # Try to get Kafka service, but don't fail if unavailable
    kafka = None
    try:
        kafka = await get_kafka_service()
    except Exception:
        pass

    services = request.services or SERVICES
    logs_generated = []

    for _ in range(request.count):
        service = random.choice(services)
        log_entry = _generate_single_log(
            service=service,
            error_rate=request.error_rate,
        )
        logs_generated.append(log_entry)

        # Record Prometheus metric
        record_log_metric(log_entry["service"], log_entry["level"])

    # Publish to Kafka in batch
    kafka_count = 0
    if kafka:
        try:
            from api.config import get_settings
            settings = get_settings()
            kafka_count = await kafka.produce_batch(
                settings.kafka_topic_logs, logs_generated
            )
        except Exception:
            pass

    # Store in database
    db_count = await log_service.bulk_create_logs(logs_generated)

    # Summary stats
    level_counts = {}
    service_counts = {}
    for log in logs_generated:
        level_counts[log["level"]] = level_counts.get(log["level"], 0) + 1
        service_counts[log["service"]] = service_counts.get(log["service"], 0) + 1

    return APIResponse(
        data={
            "total_generated": len(logs_generated),
            "stored_in_db": db_count,
            "published_to_kafka": kafka_count,
            "by_level": level_counts,
            "by_service": service_counts,
        },
        message=f"Successfully generated {len(logs_generated)} log entries",
    )


# =============================================================================
# POST /generate-errors — Burst error generation for alert testing
# =============================================================================

@router.post(
    "/generate-errors",
    response_model=APIResponse,
    summary="Generate error logs",
    description="Generate a burst of error/critical logs to trigger alert rules. "
    "Useful for testing Grafana alerts and the alert engine.",
)
async def generate_errors(
    request: GenerateErrorsRequest = GenerateErrorsRequest(),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    Generate a burst of error logs to trigger alerts.

    Creates ERROR/CRITICAL logs with high latency values,
    designed to exceed alert thresholds.
    """
    log_service = LogService(LogRepository(session))

    kafka = None
    try:
        kafka = await get_kafka_service()
    except Exception:
        pass

    error_logs = []
    for _ in range(request.count):
        log_entry = _generate_single_log(
            service=request.service,
            force_level=request.severity,
            error_rate=1.0,
        )
        # Ensure high latency to trigger latency alerts too
        log_entry["latency_ms"] = round(random.uniform(500, 2000), 2)
        error_logs.append(log_entry)

        record_log_metric(log_entry["service"], log_entry["level"])

    # Publish to Kafka
    kafka_count = 0
    if kafka:
        try:
            from api.config import get_settings
            settings = get_settings()
            kafka_count = await kafka.produce_batch(
                settings.kafka_topic_logs, error_logs
            )
        except Exception:
            pass

    # Store in database
    db_count = await log_service.bulk_create_logs(error_logs)

    return APIResponse(
        data={
            "total_errors_generated": len(error_logs),
            "stored_in_db": db_count,
            "published_to_kafka": kafka_count,
            "severity": request.severity,
            "target_service": request.service or "random",
        },
        message=f"Generated {len(error_logs)} {request.severity} logs to trigger alerts",
    )
