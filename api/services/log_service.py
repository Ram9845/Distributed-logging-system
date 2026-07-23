"""
Log service — business logic layer.

Orchestrates log operations by coordinating between the repository
(data access) and other services (Kafka, alerts). Implements the
service layer of the clean architecture.
"""

import math
from uuid import UUID
from typing import Any

import structlog

from api.repository.log_repository import LogRepository
from api.schemas.log_schema import LogFilter
from api.schemas.response_schema import (
    PaginatedResponse,
    PaginationMeta,
    StatsResponse,
)

logger = structlog.get_logger(__name__)


class LogService:
    """
    Service layer for log-related business logic.

    Delegates data access to LogRepository and constructs
    API-ready response objects with pagination metadata.
    """

    def __init__(self, repository: LogRepository) -> None:
        self._repo = repository

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_logs(
        self, filters: LogFilter | None = None
    ) -> PaginatedResponse:
        """
        Retrieve logs with optional filtering and pagination.

        Returns a PaginatedResponse with logs and metadata.
        """
        logs, total = await self._repo.get_all(filters)

        page = filters.page if filters else 1
        page_size = filters.page_size if filters else 50
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        logger.info(
            "Logs retrieved",
            total=total,
            page=page,
            page_size=page_size,
        )

        return PaginatedResponse(
            data=logs,
            pagination=pagination,
            message=f"Retrieved {len(logs)} of {total} logs",
        )

    async def get_log_by_id(self, log_id: UUID) -> Any:
        """Retrieve a single log by ID, or None if not found."""
        log = await self._repo.get_by_id(log_id)
        if log is None:
            logger.warning("Log not found", log_id=str(log_id))
        return log

    async def get_logs_by_service(
        self, service: str, page: int = 1, page_size: int = 50
    ) -> PaginatedResponse:
        """Retrieve logs filtered by service name."""
        logs, total = await self._repo.get_by_service(service, page, page_size)
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        return PaginatedResponse(
            data=logs,
            pagination=pagination,
            message=f"Retrieved {len(logs)} logs for service '{service}'",
        )

    async def get_logs_by_level(
        self, level: str, page: int = 1, page_size: int = 50
    ) -> PaginatedResponse:
        """Retrieve logs filtered by severity level."""
        logs, total = await self._repo.get_by_level(level, page, page_size)
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        return PaginatedResponse(
            data=logs,
            pagination=pagination,
            message=f"Retrieved {len(logs)} {level.upper()} logs",
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> StatsResponse:
        """
        Compute aggregate statistics across all log entries.

        Combines multiple repository queries into a single
        StatsResponse with counts, latency percentiles, error
        rate, throughput, and top endpoints/errors.
        """
        total = await self._repo.count_total()
        by_level = await self._repo.count_by_level()
        by_service = await self._repo.count_by_service()
        avg_latency = await self._repo.get_avg_latency()
        percentiles = await self._repo.get_latency_percentiles()
        error_rate = await self._repo.get_error_rate()
        logs_per_min = await self._repo.get_logs_per_minute()
        top_endpoints = await self._repo.get_top_endpoints()
        top_errors = await self._repo.get_top_error_messages()
        active_alerts = await self._repo.get_active_alerts_count()
        time_range = await self._repo.get_time_range()

        logger.info("Stats computed", total_logs=total)

        return StatsResponse(
            total_logs=total,
            logs_by_level=by_level,
            logs_by_service=by_service,
            avg_latency_ms=avg_latency,
            p95_latency_ms=percentiles.get("p95", 0.0),
            p99_latency_ms=percentiles.get("p99", 0.0),
            error_rate=error_rate,
            logs_per_minute=logs_per_min,
            top_endpoints=top_endpoints,
            top_error_messages=top_errors,
            active_alerts=active_alerts,
            time_range=time_range,
        )

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def create_log(self, log_data: dict[str, Any]) -> Any:
        """Create a single log entry in the database."""
        return await self._repo.create(log_data)

    async def bulk_create_logs(
        self, log_entries: list[dict[str, Any]]
    ) -> int:
        """Insert multiple log entries in a single batch."""
        count = await self._repo.bulk_create(log_entries)
        logger.info("Bulk log insert completed", count=count)
        return count
