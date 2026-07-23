"""
Consumer database module — PostgreSQL operations.

Handles database connections, batch inserts, and duplicate
detection for the log consumer service. Uses psycopg2 for
synchronous operations within the consumer process.
"""

import os
import logging
import time
from typing import Any
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger("consumer.database")

# =============================================================================
# Configuration
# =============================================================================

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "logging_db"),
    "user": os.getenv("POSTGRES_USER", "loguser"),
    "password": os.getenv("POSTGRES_PASSWORD", "logpassword123"),
    "application_name": "log-consumer",
}

# =============================================================================
# Prometheus Metrics
# =============================================================================

DB_INSERTS_TOTAL = Counter(
    "consumer_db_inserts_total",
    "Total log entries inserted into the database",
)

DB_INSERT_ERRORS = Counter(
    "consumer_db_insert_errors_total",
    "Total database insert errors",
)

DB_INSERT_DURATION = Histogram(
    "consumer_db_insert_duration_seconds",
    "Time to insert a batch into the database",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

DB_DUPLICATES_SKIPPED = Counter(
    "consumer_db_duplicates_skipped_total",
    "Total duplicate messages skipped",
)

DB_CONNECTION_STATUS = Gauge(
    "consumer_db_connection_status",
    "Database connection status (1=connected, 0=disconnected)",
)


class DatabaseManager:
    """
    Manages PostgreSQL connections and batch insert operations.

    Handles:
    - Connection pooling via psycopg2
    - Batch inserts with ON CONFLICT deduplication
    - Automatic retry on connection failures
    - Prometheus metrics for monitoring
    """

    def __init__(self) -> None:
        self._conn = None
        self._connect()

    def _connect(self) -> None:
        """Establish a database connection with retry logic."""
        max_retries = 10
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self._conn = psycopg2.connect(**DB_CONFIG)
                self._conn.autocommit = False
                DB_CONNECTION_STATUS.set(1)
                logger.info("Connected to PostgreSQL")
                return
            except psycopg2.OperationalError as e:
                logger.warning(
                    f"Database connection attempt {attempt + 1}/{max_retries} "
                    f"failed: {e}"
                )
                DB_CONNECTION_STATUS.set(0)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff

        raise ConnectionError(
            f"Failed to connect to PostgreSQL after {max_retries} attempts"
        )

    def _ensure_connection(self) -> None:
        """Reconnect if the connection has been lost."""
        try:
            if self._conn is None or self._conn.closed:
                self._connect()
            else:
                # Test the connection
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            logger.warning("Database connection lost, reconnecting...")
            DB_CONNECTION_STATUS.set(0)
            self._connect()

    def insert_batch(self, log_entries: list[dict[str, Any]]) -> int:
        """
        Insert a batch of log entries into PostgreSQL.

        Uses INSERT ... ON CONFLICT DO NOTHING to handle duplicates
        gracefully. Returns the number of rows actually inserted.

        Args:
            log_entries: List of log dicts to insert.

        Returns:
            Number of rows inserted (excluding duplicates).
        """
        if not log_entries:
            return 0

        self._ensure_connection()

        insert_sql = """
            INSERT INTO logs (
                timestamp, service, level, endpoint, latency_ms,
                status_code, trace_id, request_id, message, metadata
            ) VALUES (
                %(timestamp)s, %(service)s, %(level)s, %(endpoint)s,
                %(latency_ms)s, %(status_code)s, %(trace_id)s,
                %(request_id)s, %(message)s, %(metadata)s::jsonb
            )
            ON CONFLICT DO NOTHING
        """

        start = time.perf_counter()

        try:
            with self._conn.cursor() as cur:
                # Prepare entries for insertion
                prepared = []
                for entry in log_entries:
                    prepared.append({
                        "timestamp": entry.get("timestamp"),
                        "service": entry.get("service"),
                        "level": entry.get("level"),
                        "endpoint": entry.get("endpoint"),
                        "latency_ms": entry.get("latency_ms"),
                        "status_code": entry.get("status_code"),
                        "trace_id": entry.get("trace_id"),
                        "request_id": entry.get("request_id"),
                        "message": entry.get("message", ""),
                        "metadata": psycopg2.extras.Json(
                            entry.get("metadata", {})
                        ),
                    })

                psycopg2.extras.execute_batch(cur, insert_sql, prepared)
                inserted = cur.rowcount
                self._conn.commit()

            duration = time.perf_counter() - start
            DB_INSERT_DURATION.observe(duration)
            DB_INSERTS_TOTAL.inc(inserted)

            skipped = len(log_entries) - max(inserted, 0)
            if skipped > 0:
                DB_DUPLICATES_SKIPPED.inc(skipped)

            logger.debug(
                f"Inserted {inserted}/{len(log_entries)} entries "
                f"in {duration:.3f}s ({skipped} duplicates skipped)"
            )

            return max(inserted, 0)

        except psycopg2.Error as e:
            DB_INSERT_ERRORS.inc()
            self._conn.rollback()
            logger.error(f"Batch insert failed: {e}")

            # Attempt to reconnect for next batch
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

            return 0

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            self._ensure_connection()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            DB_CONNECTION_STATUS.set(0)
            logger.info("Database connection closed")
