"""
Prometheus metrics service.

Defines and manages all application metrics exposed to Prometheus.
Covers log ingestion, HTTP requests, Kafka throughput, processing
times, and system resource gauges.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# =============================================================================
# Application Info
# =============================================================================

APP_INFO = Info(
    "app",
    "Application information",
)
APP_INFO.info({
    "name": "distributed-logging-system",
    "version": "1.0.0",
    "framework": "fastapi",
})

# =============================================================================
# Log Metrics
# =============================================================================

LOGS_TOTAL = Counter(
    "logs_total",
    "Total number of logs ingested",
    ["service", "level"],
)

LOGS_ERRORS_TOTAL = Counter(
    "logs_errors_total",
    "Total number of error logs",
    ["service"],
)

LOGS_WARNINGS_TOTAL = Counter(
    "logs_warnings_total",
    "Total number of warning logs",
    ["service"],
)

LOGS_PER_SECOND = Gauge(
    "logs_per_second",
    "Current log ingestion rate per second",
)

# =============================================================================
# HTTP Metrics
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUEST_SIZE = Summary(
    "http_request_size_bytes",
    "HTTP request body size in bytes",
    ["method", "endpoint"],
)

HTTP_RESPONSE_SIZE = Summary(
    "http_response_size_bytes",
    "HTTP response body size in bytes",
    ["method", "endpoint"],
)

# =============================================================================
# Kafka Metrics
# =============================================================================

KAFKA_THROUGHPUT = Gauge(
    "kafka_throughput_messages_per_second",
    "Kafka message throughput (messages/sec)",
    ["direction"],  # "produced" or "consumed"
)

KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag (messages behind)",
    ["topic", "partition"],
)

# =============================================================================
# Processing Metrics
# =============================================================================

LOG_PROCESSING_TIME = Histogram(
    "log_processing_time_seconds",
    "Time to process a single log entry",
    ["stage"],  # "deserialize", "validate", "store", "total"
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

BATCH_PROCESSING_TIME = Histogram(
    "batch_processing_time_seconds",
    "Time to process a batch of log entries",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# =============================================================================
# System Resource Metrics
# =============================================================================

SYSTEM_CPU_USAGE = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage",
)

SYSTEM_MEMORY_USAGE = Gauge(
    "system_memory_usage_percent",
    "System memory usage percentage",
)

SYSTEM_DISK_USAGE = Gauge(
    "system_disk_usage_percent",
    "System disk usage percentage",
)

# =============================================================================
# Database Metrics
# =============================================================================

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query execution time",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
)


# =============================================================================
# Helper Functions
# =============================================================================

def record_log_metric(service: str, level: str) -> None:
    """Record a log metric for a given service and level."""
    LOGS_TOTAL.labels(service=service, level=level).inc()
    if level in ("ERROR", "CRITICAL"):
        LOGS_ERRORS_TOTAL.labels(service=service).inc()
    elif level == "WARNING":
        LOGS_WARNINGS_TOTAL.labels(service=service).inc()


def get_metrics() -> bytes:
    """Generate Prometheus metrics in exposition format."""
    return generate_latest()


def get_content_type() -> str:
    """Return the correct content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
