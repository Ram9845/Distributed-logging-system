"""
Consumer tests.

Tests for the log processor: message deserialization, validation,
normalization, and alert detection.
"""

import json
import pytest
from consumer.processor import LogProcessor


class TestLogProcessor:
    """Tests for the LogProcessor class."""

    def setup_method(self):
        """Set up a LogProcessor instance for each test."""
        self.processor = LogProcessor()

    def _make_message(self, data: dict) -> bytes:
        """Helper: create a raw Kafka message from a dict."""
        return json.dumps(data).encode("utf-8")

    def _valid_log(self, **overrides) -> dict:
        """Helper: create a valid log entry dict."""
        entry = {
            "timestamp": "2024-01-15T10:30:00+00:00",
            "service": "auth-service",
            "level": "INFO",
            "endpoint": "/login",
            "latency_ms": 45.0,
            "status_code": 200,
            "trace_id": "trace-abc123",
            "request_id": "req-xyz789",
            "message": "User login successful",
            "metadata": {"environment": "production"},
        }
        entry.update(overrides)
        return entry

    # =========================================================================
    # Successful Processing
    # =========================================================================

    def test_process_valid_message(self):
        """Valid messages should be processed successfully."""
        raw = self._make_message(self._valid_log())
        result = self.processor.process_message(raw)

        assert result is not None
        assert result["service"] == "auth-service"
        assert result["level"] == "INFO"
        assert result["message"] == "User login successful"

    def test_process_normalizes_level_case(self):
        """Log level should be normalized to uppercase."""
        raw = self._make_message(self._valid_log(level="warning"))
        result = self.processor.process_message(raw)

        assert result is not None
        assert result["level"] == "WARNING"

    def test_process_normalizes_service_case(self):
        """Service name should be normalized to lowercase."""
        raw = self._make_message(self._valid_log(service="Auth-Service"))
        result = self.processor.process_message(raw)

        assert result is not None
        assert result["service"] == "auth-service"

    def test_process_preserves_all_fields(self):
        """All fields should be preserved in the output."""
        log = self._valid_log()
        raw = self._make_message(log)
        result = self.processor.process_message(raw)

        assert result is not None
        assert result["endpoint"] == "/login"
        assert result["latency_ms"] == 45.0
        assert result["status_code"] == 200
        assert result["trace_id"] == "trace-abc123"

    # =========================================================================
    # Invalid Messages
    # =========================================================================

    def test_reject_invalid_json(self):
        """Non-JSON messages should return None."""
        result = self.processor.process_message(b"not json")
        assert result is None

    def test_reject_missing_service(self):
        """Messages without 'service' field should be rejected."""
        raw = self._make_message({"level": "INFO", "message": "test"})
        result = self.processor.process_message(raw)
        assert result is None

    def test_reject_missing_level(self):
        """Messages without 'level' field should be rejected."""
        raw = self._make_message({"service": "auth-service", "message": "test"})
        result = self.processor.process_message(raw)
        assert result is None

    def test_reject_missing_message(self):
        """Messages without 'message' field should be rejected."""
        raw = self._make_message({"service": "auth-service", "level": "INFO"})
        result = self.processor.process_message(raw)
        assert result is None

    def test_reject_invalid_level(self):
        """Messages with invalid log level should be rejected."""
        raw = self._make_message(
            self._valid_log(level="INVALID_LEVEL")
        )
        result = self.processor.process_message(raw)
        assert result is None

    def test_reject_empty_service(self):
        """Messages with empty service name should be rejected."""
        raw = self._make_message(self._valid_log(service=""))
        result = self.processor.process_message(raw)
        assert result is None

    def test_reject_whitespace_service(self):
        """Messages with whitespace-only service should be rejected."""
        raw = self._make_message(self._valid_log(service="   "))
        result = self.processor.process_message(raw)
        assert result is None

    # =========================================================================
    # Batch Processing
    # =========================================================================

    def test_process_batch(self):
        """process_batch() should return only valid entries."""
        messages = [
            self._make_message(self._valid_log(message="msg1")),
            b"invalid json",
            self._make_message(self._valid_log(message="msg2")),
            self._make_message({"bad": "entry"}),
            self._make_message(self._valid_log(message="msg3")),
        ]

        results = self.processor.process_batch(messages)
        assert len(results) == 3
        assert results[0]["message"] == "msg1"
        assert results[1]["message"] == "msg2"
        assert results[2]["message"] == "msg3"

    def test_process_empty_batch(self):
        """Empty batch should return empty list."""
        results = self.processor.process_batch([])
        assert results == []

    # =========================================================================
    # Data Normalization
    # =========================================================================

    def test_normalize_metadata_non_dict(self):
        """Non-dict metadata should be replaced with empty dict."""
        raw = self._make_message(self._valid_log(metadata="not a dict"))
        result = self.processor.process_message(raw)
        assert result is not None
        assert result["metadata"] == {}

    def test_normalize_latency_to_float(self):
        """Latency should be converted to float."""
        raw = self._make_message(self._valid_log(latency_ms="123"))
        result = self.processor.process_message(raw)
        assert result is not None
        assert result["latency_ms"] == 123.0

    def test_normalize_invalid_latency(self):
        """Invalid latency should become None."""
        raw = self._make_message(self._valid_log(latency_ms="not_a_number"))
        result = self.processor.process_message(raw)
        assert result is not None
        assert result["latency_ms"] is None

    def test_normalize_status_code_to_int(self):
        """Status code should be converted to int."""
        raw = self._make_message(self._valid_log(status_code="500"))
        result = self.processor.process_message(raw)
        assert result is not None
        assert result["status_code"] == 500

    # =========================================================================
    # Alert Detection
    # =========================================================================

    def test_error_log_increments_counter(self):
        """Processing ERROR logs should increment the error counter."""
        raw = self._make_message(self._valid_log(level="ERROR"))
        self.processor.process_message(raw)
        assert self.processor.stats["errors_detected"] == 1

    def test_critical_log_increments_counter(self):
        """Processing CRITICAL logs should increment the error counter."""
        raw = self._make_message(self._valid_log(level="CRITICAL"))
        self.processor.process_message(raw)
        assert self.processor.stats["errors_detected"] == 1

    def test_info_log_does_not_increment_error(self):
        """Processing INFO logs should NOT increment the error counter."""
        raw = self._make_message(self._valid_log(level="INFO"))
        self.processor.process_message(raw)
        assert self.processor.stats["errors_detected"] == 0

    def test_stats_tracking(self):
        """Processor should track total processed and errors."""
        for level in ["INFO", "ERROR", "WARNING", "ERROR", "INFO"]:
            raw = self._make_message(self._valid_log(level=level))
            self.processor.process_message(raw)

        assert self.processor.stats["processed"] == 5
        assert self.processor.stats["errors_detected"] == 2
