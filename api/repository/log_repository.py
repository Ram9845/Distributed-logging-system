"""
Log repository — data access layer.

Implements the Repository pattern for database operations on logs.
All SQL queries are encapsulated here, keeping business logic in
the service layer clean and testable.
"""

from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Any
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.log import Log, Alert
from api.schemas.log_schema import LogFilter


class LogRepository:
    """
    Repository for Log and Alert CRUD operations.

    Encapsulates all database queries, providing a clean interface
    for the service layer. Supports filtering, pagination, and
    aggregate queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # =========================================================================
    # Log CRUD
    # =========================================================================

    async def create(self, log_data: dict[str, Any]) -> Log:
        """Insert a single log entry and return the created record."""
        log = Log(**log_data)
        self._session.add(log)
        await self._session.flush()
        await self._session.refresh(log)
        return log

    async def bulk_create(self, log_entries: list[dict[str, Any]]) -> int:
        """
        Insert multiple log entries in a single batch.

        Returns the number of records inserted.
        """
        logs = [Log(**entry) for entry in log_entries]
        self._session.add_all(logs)
        await self._session.flush()
        return len(logs)

    async def get_by_id(self, log_id: UUID) -> Log | None:
        """Retrieve a single log entry by its UUID."""
        result = await self._session.execute(
            select(Log).where(Log.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, filters: LogFilter | None = None
    ) -> tuple[list[Log], int]:
        """
        Retrieve logs with optional filtering and pagination.

        Returns a tuple of (logs, total_count) for pagination metadata.
        """
        query = select(Log)
        count_query = select(func.count(Log.id))

        if filters:
            conditions = self._build_filter_conditions(filters)
            for condition in conditions:
                query = query.where(condition)
                count_query = count_query.where(condition)

            # Pagination
            offset = (filters.page - 1) * filters.page_size
            query = query.order_by(desc(Log.timestamp))
            query = query.offset(offset).limit(filters.page_size)
        else:
            query = query.order_by(desc(Log.timestamp)).limit(50)

        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        return logs, total

    async def get_by_service(
        self, service: str, page: int = 1, page_size: int = 50
    ) -> tuple[list[Log], int]:
        """Retrieve logs filtered by service name."""
        offset = (page - 1) * page_size

        query = (
            select(Log)
            .where(Log.service == service)
            .order_by(desc(Log.timestamp))
            .offset(offset)
            .limit(page_size)
        )
        count_query = (
            select(func.count(Log.id)).where(Log.service == service)
        )

        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        return logs, total

    async def get_by_level(
        self, level: str, page: int = 1, page_size: int = 50
    ) -> tuple[list[Log], int]:
        """Retrieve logs filtered by severity level."""
        offset = (page - 1) * page_size

        query = (
            select(Log)
            .where(Log.level == level.upper())
            .order_by(desc(Log.timestamp))
            .offset(offset)
            .limit(page_size)
        )
        count_query = (
            select(func.count(Log.id)).where(Log.level == level.upper())
        )

        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        return logs, total

    # =========================================================================
    # Aggregate Queries
    # =========================================================================

    async def count_total(self) -> int:
        """Return the total number of log entries."""
        result = await self._session.execute(select(func.count(Log.id)))
        return result.scalar() or 0

    async def count_by_level(self) -> dict[str, int]:
        """Return log counts grouped by severity level."""
        query = (
            select(Log.level, func.count(Log.id))
            .group_by(Log.level)
        )
        result = await self._session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_service(self) -> dict[str, int]:
        """Return log counts grouped by service."""
        query = (
            select(Log.service, func.count(Log.id))
            .group_by(Log.service)
        )
        result = await self._session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def get_avg_latency(self) -> float:
        """Return the average latency across all log entries."""
        result = await self._session.execute(
            select(func.avg(Log.latency_ms)).where(Log.latency_ms.isnot(None))
        )
        return round(result.scalar() or 0.0, 2)

    async def get_latency_percentiles(self) -> dict[str, float]:
        """Return p50, p95, and p99 latency values."""
        query = text("""
            SELECT
                COALESCE(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms), 0) AS p50,
                COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms), 0) AS p95,
                COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms), 0) AS p99
            FROM logs
            WHERE latency_ms IS NOT NULL
        """)
        result = await self._session.execute(query)
        row = result.one()
        return {
            "p50": round(float(row[0]), 2),
            "p95": round(float(row[1]), 2),
            "p99": round(float(row[2]), 2),
        }

    async def get_error_rate(self) -> float:
        """Return the fraction of logs that are ERROR or CRITICAL."""
        total = await self.count_total()
        if total == 0:
            return 0.0

        error_count_result = await self._session.execute(
            select(func.count(Log.id)).where(
                Log.level.in_(["ERROR", "CRITICAL"])
            )
        )
        error_count = error_count_result.scalar() or 0
        return round(error_count / total, 4)

    async def get_logs_per_minute(self) -> float:
        """
        Calculate the current log ingestion rate (logs/minute).

        Based on logs received in the last 5 minutes.
        """
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await self._session.execute(
            select(func.count(Log.id)).where(Log.timestamp >= five_min_ago)
        )
        count = result.scalar() or 0
        return round(count / 5.0, 2)

    async def get_top_endpoints(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most frequently logged endpoints."""
        query = (
            select(
                Log.endpoint,
                func.count(Log.id).label("count"),
                func.avg(Log.latency_ms).label("avg_latency"),
            )
            .where(Log.endpoint.isnot(None))
            .group_by(Log.endpoint)
            .order_by(desc("count"))
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "endpoint": row[0],
                "count": row[1],
                "avg_latency_ms": round(float(row[2] or 0), 2),
            }
            for row in result.all()
        ]

    async def get_top_error_messages(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return the most frequent error messages."""
        query = (
            select(Log.message, Log.service, func.count(Log.id).label("count"))
            .where(Log.level.in_(["ERROR", "CRITICAL"]))
            .group_by(Log.message, Log.service)
            .order_by(desc("count"))
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [
            {
                "message": row[0],
                "service": row[1],
                "count": row[2],
            }
            for row in result.all()
        ]

    async def get_time_range(self) -> dict[str, datetime | None]:
        """Return the earliest and latest log timestamps."""
        result = await self._session.execute(
            select(func.min(Log.timestamp), func.max(Log.timestamp))
        )
        row = result.one()
        return {"earliest": row[0], "latest": row[1]}

    async def get_recent_error_count(self, minutes: int = 1) -> int:
        """Count errors in the last N minutes (for alerting)."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = await self._session.execute(
            select(func.count(Log.id)).where(
                Log.level.in_(["ERROR", "CRITICAL"]),
                Log.timestamp >= cutoff,
            )
        )
        return result.scalar() or 0

    # =========================================================================
    # Alert Operations
    # =========================================================================

    async def create_alert(self, alert_data: dict[str, Any]) -> Alert:
        """Create a new alert record."""
        alert = Alert(**alert_data)
        self._session.add(alert)
        await self._session.flush()
        return alert

    async def get_active_alerts_count(self) -> int:
        """Return the count of unresolved alerts."""
        result = await self._session.execute(
            select(func.count(Alert.id)).where(Alert.resolved == False)  # noqa: E712
        )
        return result.scalar() or 0

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _build_filter_conditions(self, filters: LogFilter) -> list:
        """Build SQLAlchemy filter conditions from a LogFilter schema."""
        conditions = []

        if filters.service:
            conditions.append(Log.service == filters.service)
        if filters.level:
            conditions.append(Log.level == filters.level.upper())
        if filters.start_time:
            conditions.append(Log.timestamp >= filters.start_time)
        if filters.end_time:
            conditions.append(Log.timestamp <= filters.end_time)
        if filters.trace_id:
            conditions.append(Log.trace_id == filters.trace_id)
        if filters.endpoint:
            conditions.append(Log.endpoint == filters.endpoint)
        if filters.min_latency_ms is not None:
            conditions.append(Log.latency_ms >= filters.min_latency_ms)
        if filters.max_latency_ms is not None:
            conditions.append(Log.latency_ms <= filters.max_latency_ms)
        if filters.status_code is not None:
            conditions.append(Log.status_code == filters.status_code)
        if filters.search:
            conditions.append(Log.message.ilike(f"%{filters.search}%"))

        return conditions
