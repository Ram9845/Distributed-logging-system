"""
Database/Repository tests.

Tests for the LogRepository data access layer, Pydantic schemas,
and database model validation.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import ValidationError

from api.schemas.log_schema import (
    LogCreate,
    LogFilter,
    LogResponse,
    SimulateRequest,
    GenerateErrorsRequest,
)
from api.schemas.response_schema import (
    APIResponse,
    PaginationMeta,
    StatsResponse,
    HealthResponse,
    ComponentHealth,
)
from api.utils.helpers import (
    generate_trace_id,
    generate_request_id,
    utc_now,
    timestamp_iso,
    format_duration_ms,
    truncate_string,
    sanitize_service_name,
)
from api.utils.constants import SERVICES, LOG_LEVELS, SERVICE_ENDPOINTS


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestLogSchemas:
    """Tests for Pydantic log schemas."""

    def test_log_create_valid(self):
        """Valid LogCreate should pass validation."""
        log = LogCreate(
            service="auth-service",
            level="INFO",
            message="User login successful",
            endpoint="/login",
            latency_ms=42.5,
            status_code=200,
        )
        assert log.service == "auth-service"
        assert log.level == "INFO"

    def test_log_create_normalizes_level(self):
        """LogCreate should normalize level to uppercase."""
        log = LogCreate(
            service="auth-service",
            level="error",
            message="Something failed",
        )
        assert log.level == "ERROR"

    def test_log_create_invalid_level(self):
        """LogCreate with invalid level should raise ValidationError."""
        with pytest.raises(ValidationError):
            LogCreate(
                service="auth-service",
                level="INVALID",
                message="test",
            )

    def test_log_create_empty_service(self):
        """LogCreate with empty service should raise ValidationError."""
        with pytest.raises(ValidationError):
            LogCreate(
                service="",
                level="INFO",
                message="test",
            )

    def test_log_create_empty_message(self):
        """LogCreate with empty message should raise ValidationError."""
        with pytest.raises(ValidationError):
            LogCreate(
                service="auth-service",
                level="INFO",
                message="",
            )

    def test_log_create_status_code_range(self):
        """LogCreate status code must be between 100 and 599."""
        with pytest.raises(ValidationError):
            LogCreate(
                service="auth-service",
                level="INFO",
                message="test",
                status_code=999,
            )

    def test_log_create_negative_latency(self):
        """LogCreate latency must be non-negative."""
        with pytest.raises(ValidationError):
            LogCreate(
                service="auth-service",
                level="INFO",
                message="test",
                latency_ms=-10.0,
            )


class TestLogFilter:
    """Tests for the LogFilter query parameter schema."""

    def test_default_pagination(self):
        """Default filter should have page=1, page_size=50."""
        f = LogFilter()
        assert f.page == 1
        assert f.page_size == 50

    def test_custom_pagination(self):
        """Custom pagination values should be accepted."""
        f = LogFilter(page=3, page_size=100)
        assert f.page == 3
        assert f.page_size == 100

    def test_page_size_max(self):
        """Page size over 500 should raise ValidationError."""
        with pytest.raises(ValidationError):
            LogFilter(page_size=501)

    def test_page_min(self):
        """Page number below 1 should raise ValidationError."""
        with pytest.raises(ValidationError):
            LogFilter(page=0)

    def test_filter_level_normalization(self):
        """Level filter should be normalized to uppercase."""
        f = LogFilter(level="warning")
        assert f.level == "WARNING"


class TestSimulateRequest:
    """Tests for the SimulateRequest schema."""

    def test_defaults(self):
        """Default values should be sensible."""
        req = SimulateRequest()
        assert req.count == 100
        assert req.error_rate == 0.15
        assert req.services is None

    def test_custom_count(self):
        """Custom count should be accepted."""
        req = SimulateRequest(count=50)
        assert req.count == 50

    def test_count_max(self):
        """Count over 10000 should raise ValidationError."""
        with pytest.raises(ValidationError):
            SimulateRequest(count=10001)

    def test_invalid_service(self):
        """Invalid service name should raise ValidationError."""
        with pytest.raises(ValidationError):
            SimulateRequest(services=["nonexistent-service"])

    def test_error_rate_range(self):
        """Error rate must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            SimulateRequest(error_rate=1.5)


class TestGenerateErrorsRequest:
    """Tests for the GenerateErrorsRequest schema."""

    def test_defaults(self):
        """Default values should generate 50 ERROR logs."""
        req = GenerateErrorsRequest()
        assert req.count == 50
        assert req.severity == "ERROR"
        assert req.service is None


# =============================================================================
# Response Schema Tests
# =============================================================================


class TestResponseSchemas:
    """Tests for API response schemas."""

    def test_pagination_meta(self):
        """PaginationMeta should compute page navigation correctly."""
        meta = PaginationMeta(
            page=2,
            page_size=50,
            total_items=250,
            total_pages=5,
            has_next=True,
            has_previous=True,
        )
        assert meta.has_next is True
        assert meta.has_previous is True
        assert meta.total_pages == 5

    def test_stats_response_defaults(self):
        """StatsResponse should have sensible defaults."""
        stats = StatsResponse()
        assert stats.total_logs == 0
        assert stats.error_rate == 0.0
        assert stats.avg_latency_ms == 0.0

    def test_health_response(self):
        """HealthResponse should accept component health data."""
        health = HealthResponse(
            status="healthy",
            components={
                "postgresql": ComponentHealth(
                    status="healthy", latency_ms=5.2, message="OK"
                ),
            },
            version="1.0.0",
            uptime_seconds=120.5,
        )
        assert health.status == "healthy"
        assert health.components["postgresql"].status == "healthy"


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestHelpers:
    """Tests for utility helper functions."""

    def test_generate_trace_id_format(self):
        """trace_id should start with 'trace-' and be 18 chars."""
        tid = generate_trace_id()
        assert tid.startswith("trace-")
        assert len(tid) == 18

    def test_generate_trace_id_unique(self):
        """Each trace_id should be unique."""
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_request_id_format(self):
        """request_id should start with 'req-' and be 16 chars."""
        rid = generate_request_id()
        assert rid.startswith("req-")
        assert len(rid) == 16

    def test_utc_now_is_aware(self):
        """utc_now() should return a timezone-aware datetime."""
        now = utc_now()
        assert now.tzinfo is not None

    def test_timestamp_iso_format(self):
        """timestamp_iso() should return a valid ISO 8601 string."""
        ts = timestamp_iso()
        # Should not raise
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_format_duration_ms(self):
        """format_duration_ms should convert seconds to milliseconds."""
        assert format_duration_ms(0.5) == 500.0
        assert format_duration_ms(0.001) == 1.0
        assert format_duration_ms(1.2345) == 1234.5

    def test_truncate_string_short(self):
        """Short strings should not be truncated."""
        assert truncate_string("hello", 10) == "hello"

    def test_truncate_string_long(self):
        """Long strings should be truncated with '...'."""
        result = truncate_string("a" * 100, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_sanitize_service_name(self):
        """Service names should have hyphens replaced with underscores."""
        assert sanitize_service_name("auth-service") == "auth_service"
        assert sanitize_service_name("Payment-Service") == "payment_service"


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for application constants."""

    def test_five_services_defined(self):
        """Exactly 5 services should be defined."""
        assert len(SERVICES) == 5

    def test_all_services_have_endpoints(self):
        """Every service should have endpoint definitions."""
        for service in SERVICES:
            assert service in SERVICE_ENDPOINTS
            assert len(SERVICE_ENDPOINTS[service]) > 0

    def test_log_levels_defined(self):
        """5 log levels should be defined."""
        assert LOG_LEVELS == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
