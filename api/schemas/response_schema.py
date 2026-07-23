"""
Generic API response schemas.

Provides standardized response wrappers for consistent API output
format, pagination metadata, and statistics responses.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.

    Every API endpoint returns responses in this format for
    consistency and predictable client-side parsing.
    """

    success: bool = Field(True, description="Whether the request succeeded")
    message: str = Field("OK", description="Human-readable status message")
    data: T | None = Field(None, description="Response payload")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )
    request_id: str | None = Field(None, description="Request correlation ID")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with metadata for list endpoints."""

    success: bool = True
    message: str = "OK"
    data: list[T] = Field(default_factory=list, description="List of items")
    pagination: "PaginationMeta" = Field(
        ..., description="Pagination metadata"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata returned with list responses."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of matching items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_previous: bool = Field(..., description="Whether a previous page exists")


class StatsResponse(BaseModel):
    """Aggregate statistics response."""

    total_logs: int = Field(0, description="Total log count")
    logs_by_level: dict[str, int] = Field(
        default_factory=dict, description="Log count by severity level"
    )
    logs_by_service: dict[str, int] = Field(
        default_factory=dict, description="Log count by service"
    )
    avg_latency_ms: float = Field(0.0, description="Average latency in ms")
    p95_latency_ms: float = Field(0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(0.0, description="99th percentile latency")
    error_rate: float = Field(0.0, description="Error rate (0.0 - 1.0)")
    logs_per_minute: float = Field(0.0, description="Current logs per minute rate")
    top_endpoints: list[dict[str, Any]] = Field(
        default_factory=list, description="Most active endpoints"
    )
    top_error_messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Most frequent error messages"
    )
    active_alerts: int = Field(0, description="Number of unresolved alerts")
    time_range: dict[str, datetime | None] = Field(
        default_factory=dict, description="Time range of data"
    )


class HealthResponse(BaseModel):
    """Health check response with component statuses."""

    status: str = Field("healthy", description="Overall health status")
    components: dict[str, "ComponentHealth"] = Field(
        default_factory=dict, description="Individual component health"
    )
    version: str = Field("1.0.0", description="Application version")
    uptime_seconds: float = Field(0.0, description="Application uptime")


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    status: str = Field(..., description="Component health status")
    latency_ms: float | None = Field(None, description="Check latency in ms")
    message: str | None = Field(None, description="Additional details")


class ErrorResponse(BaseModel):
    """Error response returned when an API call fails."""

    success: bool = False
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error description")
    detail: Any | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None
