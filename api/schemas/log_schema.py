"""
Pydantic schemas for log entries.

Defines request/response models for the API layer with validation,
serialization, and OpenAPI documentation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from api.utils.constants import LOG_LEVELS, SERVICES


class LogBase(BaseModel):
    """Base schema with common log fields."""

    service: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Originating microservice name",
        examples=["auth-service"],
    )
    level: str = Field(
        ...,
        description="Log severity level",
        examples=["ERROR"],
    )
    endpoint: str | None = Field(
        None,
        max_length=256,
        description="HTTP endpoint",
        examples=["/login"],
    )
    latency_ms: float | None = Field(
        None,
        ge=0,
        description="Request latency in milliseconds",
        examples=[42.5],
    )
    status_code: int | None = Field(
        None,
        ge=100,
        le=599,
        description="HTTP response status code",
        examples=[200],
    )
    trace_id: str | None = Field(
        None,
        max_length=64,
        description="Distributed trace identifier",
        examples=["trace-abc123def456"],
    )
    request_id: str | None = Field(
        None,
        max_length=64,
        description="Unique request identifier",
        examples=["req-abc123def456"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable log message",
        examples=["User login successful"],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Ensure the log level is valid."""
        upper = v.upper()
        if upper not in LOG_LEVELS:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {LOG_LEVELS}"
            )
        return upper


class LogCreate(LogBase):
    """Schema for creating a new log entry via the API."""

    timestamp: datetime | None = Field(
        None,
        description="Event timestamp (defaults to now if omitted)",
    )


class LogResponse(LogBase):
    """Schema for log entries returned by the API."""

    id: UUID
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LogFilter(BaseModel):
    """Query parameters for filtering logs."""

    service: str | None = Field(None, description="Filter by service name")
    level: str | None = Field(None, description="Filter by log level")
    start_time: datetime | None = Field(None, description="Start of time range")
    end_time: datetime | None = Field(None, description="End of time range")
    trace_id: str | None = Field(None, description="Filter by trace ID")
    endpoint: str | None = Field(None, description="Filter by endpoint")
    min_latency_ms: float | None = Field(None, ge=0, description="Minimum latency")
    max_latency_ms: float | None = Field(None, ge=0, description="Maximum latency")
    status_code: int | None = Field(None, description="Filter by status code")
    search: str | None = Field(None, description="Full-text search in message")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=500, description="Results per page")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str | None) -> str | None:
        if v is not None:
            upper = v.upper()
            if upper not in LOG_LEVELS:
                raise ValueError(f"Invalid level '{v}'. Must be one of: {LOG_LEVELS}")
            return upper
        return v


class SimulateRequest(BaseModel):
    """Request body for the /simulate endpoint."""

    count: int = Field(
        100,
        ge=1,
        le=10000,
        description="Number of log entries to generate",
    )
    services: list[str] | None = Field(
        None,
        description="Specific services to simulate (all if omitted)",
    )
    error_rate: float = Field(
        0.15,
        ge=0.0,
        le=1.0,
        description="Fraction of logs that should be errors",
    )

    @field_validator("services")
    @classmethod
    def validate_services(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            invalid = [s for s in v if s not in SERVICES]
            if invalid:
                raise ValueError(
                    f"Invalid services: {invalid}. Must be one of: {SERVICES}"
                )
        return v


class GenerateErrorsRequest(BaseModel):
    """Request body for the /generate-errors endpoint."""

    count: int = Field(
        50,
        ge=1,
        le=5000,
        description="Number of error logs to generate",
    )
    service: str | None = Field(
        None,
        description="Target service (random if omitted)",
    )
    severity: str = Field(
        "ERROR",
        description="Error severity",
    )
