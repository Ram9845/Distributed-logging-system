"""
Alert service — threshold monitoring and alert generation.

Monitors log metrics against configurable thresholds and triggers
alerts when violations are detected. Integrates with Prometheus
for metric-based alerting.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from prometheus_client import Counter, Gauge

from api.utils.constants import (
    ALERT_ERROR_THRESHOLD,
    ALERT_LATENCY_THRESHOLD_MS,
    ALERT_CPU_THRESHOLD_PCT,
)

logger = structlog.get_logger(__name__)

# =============================================================================
# Prometheus Metrics for Alerts
# =============================================================================

ALERTS_TRIGGERED = Counter(
    "alerts_triggered_total",
    "Total alerts triggered",
    ["alert_type", "severity"],
)

ACTIVE_ALERTS = Gauge(
    "active_alerts_count",
    "Current number of active (unresolved) alerts",
)

ERROR_RATE_GAUGE = Gauge(
    "error_rate_per_minute",
    "Current error count per minute",
    ["service"],
)


class AlertService:
    """
    Monitors metrics and generates alerts when thresholds are exceeded.

    Thresholds:
    - ERROR logs > 20 per minute → alert
    - Response latency > 500ms → alert
    - CPU usage > 80% → alert
    """

    def __init__(self) -> None:
        self._active_alerts: list[dict[str, Any]] = []

    async def check_error_rate(
        self,
        error_count: int,
        service: str = "all",
        window_minutes: int = 1,
    ) -> dict[str, Any] | None:
        """
        Check if the error rate exceeds the threshold.

        Args:
            error_count: Number of errors in the time window.
            service: Service name (or 'all' for global).
            window_minutes: Time window in minutes.

        Returns:
            Alert dict if threshold exceeded, None otherwise.
        """
        ERROR_RATE_GAUGE.labels(service=service).set(error_count)

        if error_count > ALERT_ERROR_THRESHOLD:
            alert = self._create_alert(
                alert_type="high_error_rate",
                severity="CRITICAL",
                service=service,
                message=(
                    f"Error rate exceeded threshold: {error_count} errors "
                    f"in the last {window_minutes} minute(s) "
                    f"(threshold: {ALERT_ERROR_THRESHOLD})"
                ),
                metric_value=float(error_count),
                threshold=float(ALERT_ERROR_THRESHOLD),
            )

            ALERTS_TRIGGERED.labels(
                alert_type="high_error_rate", severity="CRITICAL"
            ).inc()

            logger.critical(
                "HIGH ERROR RATE ALERT",
                error_count=error_count,
                threshold=ALERT_ERROR_THRESHOLD,
                service=service,
            )

            return alert

        return None

    async def check_latency(
        self,
        latency_ms: float,
        endpoint: str = "unknown",
        service: str = "unknown",
    ) -> dict[str, Any] | None:
        """
        Check if response latency exceeds the threshold.

        Args:
            latency_ms: Observed latency in milliseconds.
            endpoint: The endpoint that exhibited high latency.
            service: Service name.

        Returns:
            Alert dict if threshold exceeded, None otherwise.
        """
        if latency_ms > ALERT_LATENCY_THRESHOLD_MS:
            alert = self._create_alert(
                alert_type="high_latency",
                severity="WARNING",
                service=service,
                message=(
                    f"Response latency {latency_ms:.1f}ms exceeds threshold "
                    f"of {ALERT_LATENCY_THRESHOLD_MS}ms on {endpoint}"
                ),
                metric_value=latency_ms,
                threshold=ALERT_LATENCY_THRESHOLD_MS,
            )

            ALERTS_TRIGGERED.labels(
                alert_type="high_latency", severity="WARNING"
            ).inc()

            logger.warning(
                "HIGH LATENCY ALERT",
                latency_ms=latency_ms,
                threshold=ALERT_LATENCY_THRESHOLD_MS,
                endpoint=endpoint,
                service=service,
            )

            return alert

        return None

    async def check_cpu_usage(
        self, cpu_percent: float
    ) -> dict[str, Any] | None:
        """
        Check if CPU usage exceeds the threshold.

        Args:
            cpu_percent: Current CPU usage percentage.

        Returns:
            Alert dict if threshold exceeded, None otherwise.
        """
        if cpu_percent > ALERT_CPU_THRESHOLD_PCT:
            alert = self._create_alert(
                alert_type="high_cpu",
                severity="WARNING",
                service="system",
                message=(
                    f"CPU usage at {cpu_percent:.1f}% exceeds threshold "
                    f"of {ALERT_CPU_THRESHOLD_PCT}%"
                ),
                metric_value=cpu_percent,
                threshold=ALERT_CPU_THRESHOLD_PCT,
            )

            ALERTS_TRIGGERED.labels(
                alert_type="high_cpu", severity="WARNING"
            ).inc()

            logger.warning(
                "HIGH CPU ALERT",
                cpu_percent=cpu_percent,
                threshold=ALERT_CPU_THRESHOLD_PCT,
            )

            return alert

        return None

    async def get_active_alerts(self) -> list[dict[str, Any]]:
        """Return all currently active (unresolved) alerts."""
        return [a for a in self._active_alerts if not a.get("resolved")]

    async def resolve_alert(self, alert_type: str) -> int:
        """
        Mark all alerts of a given type as resolved.

        Returns the number of alerts resolved.
        """
        resolved_count = 0
        for alert in self._active_alerts:
            if (
                alert["alert_type"] == alert_type
                and not alert.get("resolved")
            ):
                alert["resolved"] = True
                alert["resolved_at"] = datetime.now(timezone.utc).isoformat()
                resolved_count += 1

        ACTIVE_ALERTS.set(
            len([a for a in self._active_alerts if not a.get("resolved")])
        )

        return resolved_count

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        service: str,
        message: str,
        metric_value: float,
        threshold: float,
    ) -> dict[str, Any]:
        """Create an alert dict and add it to the active alerts list."""
        alert = {
            "alert_type": alert_type,
            "severity": severity,
            "service": service,
            "message": message,
            "metric_value": metric_value,
            "threshold": threshold,
            "resolved": False,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
        }

        self._active_alerts.append(alert)
        ACTIVE_ALERTS.set(
            len([a for a in self._active_alerts if not a.get("resolved")])
        )

        return alert
