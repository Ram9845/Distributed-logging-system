"""
Producer tests.

Tests for the log generator and producer service, including
log entry generation, batch creation, and error bursts.
"""

import pytest
import json
from datetime import datetime
from producer.generator import LogGenerator
from producer.services import SERVICES


class TestLogGenerator:
    """Tests for the LogGenerator class."""

    def setup_method(self):
        """Set up a LogGenerator instance for each test."""
        self.generator = LogGenerator()

    def test_generate_returns_valid_log(self):
        """generate() should return a dict with all required fields."""
        log = self.generator.generate()

        assert isinstance(log, dict)
        assert "timestamp" in log
        assert "service" in log
        assert "level" in log
        assert "endpoint" in log
        assert "latency_ms" in log
        assert "status_code" in log
        assert "trace_id" in log
        assert "request_id" in log
        assert "message" in log
        assert "metadata" in log

    def test_generate_valid_service(self):
        """Generated log should have a valid service name."""
        log = self.generator.generate()
        assert log["service"] in SERVICES

    def test_generate_valid_level(self):
        """Generated log should have a valid log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        log = self.generator.generate()
        assert log["level"] in valid_levels

    def test_generate_positive_latency(self):
        """Generated latency should be a positive number."""
        log = self.generator.generate()
        assert isinstance(log["latency_ms"], float)
        assert log["latency_ms"] > 0

    def test_generate_valid_status_code(self):
        """Generated status code should be a valid HTTP status."""
        log = self.generator.generate()
        assert 100 <= log["status_code"] <= 599

    def test_generate_with_specific_service(self):
        """generate() with service_name should use that service."""
        log = self.generator.generate(service_name="auth-service")
        assert log["service"] == "auth-service"

    def test_generate_with_forced_level(self):
        """generate() with force_level should use that level."""
        log = self.generator.generate(force_level="ERROR")
        assert log["level"] == "ERROR"

    def test_generate_trace_id_format(self):
        """trace_id should follow the trace-<hex> format."""
        log = self.generator.generate()
        assert log["trace_id"].startswith("trace-")
        assert len(log["trace_id"]) == 18  # "trace-" + 12 hex chars

    def test_generate_request_id_format(self):
        """request_id should follow the req-<hex> format."""
        log = self.generator.generate()
        assert log["request_id"].startswith("req-")
        assert len(log["request_id"]) == 16  # "req-" + 12 hex chars

    def test_generate_valid_timestamp(self):
        """Generated timestamp should be a valid ISO 8601 string."""
        log = self.generator.generate()
        # Should not raise
        dt = datetime.fromisoformat(log["timestamp"])
        assert dt is not None

    def test_generate_metadata_is_dict(self):
        """Generated metadata should be a dictionary."""
        log = self.generator.generate()
        assert isinstance(log["metadata"], dict)
        assert "environment" in log["metadata"]
        assert "region" in log["metadata"]

    def test_generate_message_not_empty(self):
        """Generated message should be a non-empty string."""
        log = self.generator.generate()
        assert isinstance(log["message"], str)
        assert len(log["message"]) > 0

    def test_generate_json_serializable(self):
        """Generated log should be JSON-serializable."""
        log = self.generator.generate()
        serialized = json.dumps(log, default=str)
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized["service"] == log["service"]


class TestLogGeneratorBatch:
    """Tests for batch generation."""

    def setup_method(self):
        self.generator = LogGenerator()

    def test_generate_batch_correct_count(self):
        """generate_batch() should produce the requested number of entries."""
        batch = self.generator.generate_batch(count=25)
        assert len(batch) == 25

    def test_generate_batch_all_valid(self):
        """Every entry in a batch should have required fields."""
        batch = self.generator.generate_batch(count=10)
        for entry in batch:
            assert "service" in entry
            assert "level" in entry
            assert "message" in entry

    def test_generate_batch_with_service_filter(self):
        """Batch with service_name should only contain that service."""
        batch = self.generator.generate_batch(
            count=20, service_name="payment-service"
        )
        for entry in batch:
            assert entry["service"] == "payment-service"

    def test_generate_error_burst(self):
        """generate_error_burst() should produce only ERROR/CRITICAL entries."""
        burst = self.generator.generate_error_burst(count=15)
        assert len(burst) == 15
        for entry in burst:
            assert entry["level"] in ("ERROR", "CRITICAL")

    def test_generate_error_burst_high_latency(self):
        """Error burst entries should have high latency (>=500ms)."""
        burst = self.generator.generate_error_burst(count=10)
        for entry in burst:
            assert entry["latency_ms"] >= 500


class TestServiceConfig:
    """Tests for service configuration."""

    def test_all_services_exist(self):
        """All expected services should be defined."""
        expected = {
            "auth-service",
            "payment-service",
            "order-service",
            "notification-service",
            "inventory-service",
        }
        assert set(SERVICES.keys()) == expected

    def test_services_have_endpoints(self):
        """Every service should have at least one endpoint."""
        for name, config in SERVICES.items():
            assert len(config.endpoints) > 0, f"{name} has no endpoints"

    def test_services_have_messages(self):
        """Every service should have messages for all levels."""
        for name, config in SERVICES.items():
            assert len(config.info_messages) > 0, f"{name} missing info messages"
            assert len(config.error_messages) > 0, f"{name} missing error messages"
            assert len(config.warning_messages) > 0, f"{name} missing warning messages"
