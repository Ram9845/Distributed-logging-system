-- =============================================================================
-- Distributed Logging & Monitoring System — Database Schema
-- =============================================================================
-- PostgreSQL schema for storing structured log entries from microservices.
-- Designed for high-throughput writes and efficient querying by service,
-- level, timestamp, and trace_id.
-- =============================================================================

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- Main logs table
-- =============================================================================
CREATE TABLE IF NOT EXISTS logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service         VARCHAR(64) NOT NULL,
    level           VARCHAR(16) NOT NULL,
    endpoint        VARCHAR(256),
    latency_ms      FLOAT,
    status_code     INTEGER,
    trace_id        VARCHAR(64),
    request_id      VARCHAR(64),
    message         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraint to validate log levels
    CONSTRAINT valid_log_level CHECK (
        level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    )
);

-- =============================================================================
-- Indexes for efficient querying
-- =============================================================================

-- Composite index for time-range queries filtered by service
CREATE INDEX IF NOT EXISTS idx_logs_service_timestamp
    ON logs (service, timestamp DESC);

-- Index for filtering by log level
CREATE INDEX IF NOT EXISTS idx_logs_level
    ON logs (level);

-- Index for timestamp-based queries (most common)
CREATE INDEX IF NOT EXISTS idx_logs_timestamp
    ON logs (timestamp DESC);

-- Index for trace ID lookups (distributed tracing)
CREATE INDEX IF NOT EXISTS idx_logs_trace_id
    ON logs (trace_id)
    WHERE trace_id IS NOT NULL;

-- Index for request ID lookups
CREATE INDEX IF NOT EXISTS idx_logs_request_id
    ON logs (request_id)
    WHERE request_id IS NOT NULL;

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_logs_metadata
    ON logs USING GIN (metadata);

-- Index for status code filtering
CREATE INDEX IF NOT EXISTS idx_logs_status_code
    ON logs (status_code)
    WHERE status_code IS NOT NULL;

-- =============================================================================
-- Alerts table — stores triggered alert records
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type      VARCHAR(64) NOT NULL,
    severity        VARCHAR(16) NOT NULL DEFAULT 'WARNING',
    service         VARCHAR(64),
    message         TEXT NOT NULL,
    metric_value    FLOAT,
    threshold       FLOAT,
    resolved        BOOLEAN DEFAULT FALSE,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',

    CONSTRAINT valid_alert_severity CHECK (
        severity IN ('INFO', 'WARNING', 'CRITICAL')
    )
);

CREATE INDEX IF NOT EXISTS idx_alerts_type_triggered
    ON alerts (alert_type, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_resolved
    ON alerts (resolved, triggered_at DESC);

-- =============================================================================
-- Materialized view for per-service stats (refreshed periodically)
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS service_log_stats AS
SELECT
    service,
    level,
    COUNT(*)                                    AS total_count,
    AVG(latency_ms)                             AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms,
    MIN(timestamp)                              AS first_seen,
    MAX(timestamp)                              AS last_seen
FROM logs
GROUP BY service, level;

CREATE UNIQUE INDEX IF NOT EXISTS idx_service_log_stats_service_level
    ON service_log_stats (service, level);
