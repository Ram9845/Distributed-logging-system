"""
Log routes — CRUD endpoints for log entries.

Provides REST API endpoints for querying, filtering, and retrieving
log entries stored in PostgreSQL.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.repository.log_repository import LogRepository
from api.services.log_service import LogService
from api.schemas.log_schema import LogFilter, LogResponse
from api.schemas.response_schema import (
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/logs", tags=["Logs"])


def _build_service(session: AsyncSession) -> LogService:
    """Wire up the log service with its repository dependency."""
    return LogService(LogRepository(session))


# =============================================================================
# GET /logs — List all logs with filtering & pagination
# =============================================================================

@router.get(
    "",
    response_model=PaginatedResponse[LogResponse],
    summary="List logs",
    description="Retrieve log entries with optional filtering by service, level, "
    "time range, latency, and full-text search. Supports pagination.",
)
async def get_logs(
    service: str | None = Query(None, description="Filter by service name"),
    level: str | None = Query(None, description="Filter by log level"),
    trace_id: str | None = Query(None, description="Filter by trace ID"),
    endpoint: str | None = Query(None, description="Filter by endpoint"),
    min_latency_ms: float | None = Query(None, ge=0, description="Min latency"),
    max_latency_ms: float | None = Query(None, ge=0, description="Max latency"),
    status_code: int | None = Query(None, description="Filter by status code"),
    search: str | None = Query(None, description="Search in log messages"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Results per page"),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """Retrieve paginated log entries with optional filters."""
    log_service = _build_service(session)

    filters = LogFilter(
        service=service,
        level=level,
        trace_id=trace_id,
        endpoint=endpoint,
        min_latency_ms=min_latency_ms,
        max_latency_ms=max_latency_ms,
        status_code=status_code,
        search=search,
        page=page,
        page_size=page_size,
    )

    return await log_service.get_logs(filters)


# =============================================================================
# GET /logs/{id} — Get a single log by ID
# =============================================================================

@router.get(
    "/{log_id}",
    response_model=APIResponse[LogResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get log by ID",
    description="Retrieve a single log entry by its UUID.",
)
async def get_log_by_id(
    log_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Retrieve a specific log entry by its unique identifier."""
    log_service = _build_service(session)
    log = await log_service.get_log_by_id(log_id)

    if log is None:
        raise HTTPException(
            status_code=404,
            detail=f"Log entry with ID '{log_id}' not found",
        )

    return APIResponse(data=log, message="Log entry retrieved")


# =============================================================================
# GET /logs/service/{service} — Get logs by service
# =============================================================================

@router.get(
    "/service/{service}",
    response_model=PaginatedResponse[LogResponse],
    summary="Get logs by service",
    description="Retrieve log entries for a specific microservice.",
)
async def get_logs_by_service(
    service: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """Retrieve logs filtered by service name."""
    log_service = _build_service(session)
    return await log_service.get_logs_by_service(service, page, page_size)


# =============================================================================
# GET /logs/level/{level} — Get logs by severity level
# =============================================================================

@router.get(
    "/level/{level}",
    response_model=PaginatedResponse[LogResponse],
    summary="Get logs by level",
    description="Retrieve log entries at a specific severity level.",
)
async def get_logs_by_level(
    level: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """Retrieve logs filtered by severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
    log_service = _build_service(session)
    return await log_service.get_logs_by_level(level, page, page_size)
