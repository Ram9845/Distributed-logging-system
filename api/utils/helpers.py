"""
Utility helper functions.

Provides common utilities for ID generation, timestamp formatting,
and other cross-cutting concerns used throughout the application.
"""

import uuid
import time
from datetime import datetime, timezone


def generate_trace_id() -> str:
    """
    Generate a unique trace ID for distributed tracing.

    Format: 'trace-<short_uuid>' for readability in logs.
    """
    return f"trace-{uuid.uuid4().hex[:12]}"


def generate_request_id() -> str:
    """
    Generate a unique request ID for request correlation.

    Format: 'req-<short_uuid>' for readability.
    """
    return f"req-{uuid.uuid4().hex[:12]}"


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def timestamp_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return utc_now().isoformat()


def timestamp_epoch_ms() -> int:
    """Return the current time as epoch milliseconds."""
    return int(time.time() * 1000)


def format_duration_ms(duration_seconds: float) -> float:
    """Convert seconds to milliseconds, rounded to 2 decimal places."""
    return round(duration_seconds * 1000, 2)


def truncate_string(value: str, max_length: int = 500) -> str:
    """Truncate a string to a maximum length, appending '...' if truncated."""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def sanitize_service_name(name: str) -> str:
    """
    Sanitize a service name for use in metrics labels.

    Replaces hyphens with underscores and converts to lowercase.
    """
    return name.lower().replace("-", "_")


def parse_bool(value: str | bool) -> bool:
    """Parse a boolean from a string value (e.g., env vars)."""
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes", "on")
