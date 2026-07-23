"""
Log processor — message deserialization and validation.

Processes raw Kafka messages into validated log entries,
handles malformed messages, and performs alert detection
on incoming log data.
"""

import json
import logging
from typing import Any

from prometheus_client import Counter, Histogram

logger = logging.getLogger("consumer.processor")

# =============================================================================
# Prometheus Metrics
# =============================================================================

MESSAGES_PROCESSED = Counter(
    "consumer_messages_processed_total",
    "Total messages processed",
    ["status"],  # "success", "error", "invalid"
)

PROCESSING_DURATION = Histogram(
    "consumer_processing_duration_seconds",
    "Time to process a single message",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05],
)

ERROR_LOGS_DETECTED = Counter(
    "consumer_error_logs_detected_total",
    "Total error/critical logs detected by the consumer",
    ["service"],
)

HIGH_LATENCY_DETECTED = Counter(
    "consumer_high_latency_detected_total",
    "Total high-latency log entries detected",
    ["service", "endpoint"],
)

# Required fields in a valid log entry
REQUIRED_FIELDS = {"service", "level", "message"}
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
LATENCY_ALERT_THRESHOLD_MS = 500.0


class LogProcessor:
    """
    Processes Kafka messages into validated, enriched log entries.

    Responsibilities:
    - Deserialize JSON messages
    - Validate required fields and data types
    - Detect error patterns for alerting
    - Track processing metrics
    """

    def __init__(self) -> None:
        self._processed_count = 0
        self._error_count = 0

    def process_message(self, raw_message: bytes) -> dict[str, Any] | None:
        """
        Process a single Kafka message.

        Args:
            raw_message: Raw bytes from Kafka.

        Returns:
            Validated log dict, or None if the message is invalid.
        """
        import time
        start = time.perf_counter()

        try:
            # ---- Deserialization ----
            try:
                log_entry = json.loads(raw_message.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                MESSAGES_PROCESSED.labels(status="invalid").inc()
                logger.warning(f"Failed to deserialize message: {e}")
                return None

            # ---- Validation ----
            if not self._validate(log_entry):
                MESSAGES_PROCESSED.labels(status="invalid").inc()
                return None

            # ---- Normalize ----
            log_entry = self._normalize(log_entry)

            # ---- Alert Detection ----
            self._detect_alerts(log_entry)

            self._processed_count += 1
            MESSAGES_PROCESSED.labels(status="success").inc()

            duration = time.perf_counter() - start
            PROCESSING_DURATION.observe(duration)

            return log_entry

        except Exception as e:
            MESSAGES_PROCESSED.labels(status="error").inc()
            logger.error(f"Unexpected error processing message: {e}")
            return None

    def process_batch(
        self, raw_messages: list[bytes]
    ) -> list[dict[str, Any]]:
        """
        Process a batch of Kafka messages.

        Returns only the successfully validated entries.
        """
        results = []
        for msg in raw_messages:
            entry = self.process_message(msg)
            if entry is not None:
                results.append(entry)
        return results

    def _validate(self, entry: dict[str, Any]) -> bool:
        """Validate that a log entry has all required fields."""
        # Check required fields
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            logger.warning(
                f"Log entry missing required fields: {missing}"
            )
            return False

        # Validate log level
        level = entry.get("level", "").upper()
        if level not in VALID_LEVELS:
            logger.warning(f"Invalid log level: {entry.get('level')}")
            return False

        # Validate service name is non-empty
        if not entry.get("service", "").strip():
            logger.warning("Empty service name in log entry")
            return False

        return True

    def _normalize(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Normalize field values and ensure consistent types."""
        entry["level"] = entry["level"].upper()
        entry["service"] = entry["service"].strip().lower()

        # Ensure metadata is a dict
        if not isinstance(entry.get("metadata"), dict):
            entry["metadata"] = {}

        # Ensure latency is a float
        if entry.get("latency_ms") is not None:
            try:
                entry["latency_ms"] = float(entry["latency_ms"])
            except (ValueError, TypeError):
                entry["latency_ms"] = None

        # Ensure status_code is an int
        if entry.get("status_code") is not None:
            try:
                entry["status_code"] = int(entry["status_code"])
            except (ValueError, TypeError):
                entry["status_code"] = None

        # Convert metadata dict to JSON string for psycopg2
        # (handled in database layer, keep as dict here)

        return entry

    def _detect_alerts(self, entry: dict[str, Any]) -> None:
        """
        Detect alert-worthy patterns in a log entry.

        Checks for:
        - ERROR / CRITICAL level logs
        - High latency (>500ms)
        """
        level = entry.get("level", "")
        service = entry.get("service", "unknown")

        # Track error logs
        if level in ("ERROR", "CRITICAL"):
            self._error_count += 1
            ERROR_LOGS_DETECTED.labels(service=service).inc()

        # Track high-latency entries
        latency = entry.get("latency_ms")
        if latency and latency > LATENCY_ALERT_THRESHOLD_MS:
            endpoint = entry.get("endpoint", "unknown")
            HIGH_LATENCY_DETECTED.labels(
                service=service, endpoint=endpoint
            ).inc()
            logger.warning(
                f"High latency detected: {latency:.1f}ms on "
                f"{service}{endpoint}"
            )

    @property
    def stats(self) -> dict[str, int]:
        """Return processing statistics."""
        return {
            "processed": self._processed_count,
            "errors_detected": self._error_count,
        }
