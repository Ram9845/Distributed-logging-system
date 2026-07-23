"""
Realistic log entry generator.

Generates structured JSON log entries that simulate realistic
microservice behavior with appropriate latency distributions,
error patterns, and correlated trace/request IDs.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Any

from producer.services import SERVICES, ServiceConfig


class LogGenerator:
    """
    Generates realistic structured log entries for simulated services.

    Produces logs with:
    - Weighted random log levels (more INFO, fewer CRITICALs)
    - Service-specific endpoints and messages
    - Realistic latency distributions (log-normal)
    - Correlated trace and request IDs
    - Varied HTTP status codes based on log level
    """

    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    STATUS_CODES = {
        "DEBUG": [200],
        "INFO": [200, 201, 204],
        "WARNING": [200, 301, 400, 408, 429],
        "ERROR": [400, 401, 403, 404, 500, 502, 503],
        "CRITICAL": [500, 502, 503, 504],
    }

    REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-south-1"]

    def __init__(self, services: dict[str, ServiceConfig] | None = None) -> None:
        self._services = services or SERVICES

    def generate(
        self,
        service_name: str | None = None,
        force_level: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a single log entry.

        Args:
            service_name: Specific service (random if None).
            force_level: Force a log level (weighted random if None).

        Returns:
            A structured log entry dict ready for Kafka serialization.
        """
        # Pick service
        if service_name and service_name in self._services:
            service = self._services[service_name]
        else:
            service = random.choice(list(self._services.values()))

        # Determine log level
        level = force_level or self._pick_level(service)

        # Pick endpoint and message
        endpoint = random.choice(service.endpoints)
        message = self._pick_message(service, level)

        # Generate latency using log-normal distribution
        latency = self._generate_latency(service, level)

        # Status code based on level
        status_code = random.choice(self.STATUS_CODES.get(level, [200]))

        # IDs for distributed tracing
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        request_id = f"req-{uuid.uuid4().hex[:12]}"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": service.name,
            "level": level,
            "endpoint": endpoint,
            "latency_ms": round(latency, 2),
            "status_code": status_code,
            "trace_id": trace_id,
            "request_id": request_id,
            "message": message,
            "metadata": {
                "environment": "production",
                "region": random.choice(self.REGIONS),
                "host": f"{service.name.replace('-service', '')}-{random.randint(1, 5)}",
                "pod": f"{service.name}-{uuid.uuid4().hex[:8]}",
                "version": f"1.{random.randint(0, 9)}.{random.randint(0, 20)}",
            },
        }

    def generate_batch(
        self,
        count: int = 10,
        service_name: str | None = None,
        force_level: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a batch of log entries."""
        return [
            self.generate(service_name=service_name, force_level=force_level)
            for _ in range(count)
        ]

    def generate_error_burst(
        self,
        count: int = 25,
        service_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate a burst of error logs for alert testing.

        All entries will be ERROR or CRITICAL level with high latency.
        """
        entries = []
        for _ in range(count):
            level = random.choice(["ERROR", "CRITICAL"])
            entry = self.generate(
                service_name=service_name,
                force_level=level,
            )
            # Force high latency for latency alert triggering
            entry["latency_ms"] = round(random.uniform(500, 3000), 2)
            entries.append(entry)
        return entries

    def _pick_level(self, service: ServiceConfig) -> str:
        """
        Pick a log level using weighted random selection.

        Weights are adjusted based on the service's error/warning rates.
        """
        error_weight = service.error_rate
        warning_weight = service.warning_rate
        remaining = 1.0 - error_weight - warning_weight

        weights = [
            remaining * 0.15,   # DEBUG
            remaining * 0.85,   # INFO
            warning_weight,     # WARNING
            error_weight * 0.8, # ERROR
            error_weight * 0.2, # CRITICAL
        ]

        return random.choices(self.LOG_LEVELS, weights=weights, k=1)[0]

    def _pick_message(self, service: ServiceConfig, level: str) -> str:
        """Pick an appropriate message for the given service and level."""
        message_map = {
            "DEBUG": service.debug_messages,
            "INFO": service.info_messages,
            "WARNING": service.warning_messages,
            "ERROR": service.error_messages,
            "CRITICAL": service.error_messages,  # Reuse error messages for CRITICAL
        }
        messages = message_map.get(level, service.info_messages)
        if not messages:
            return f"{level} event in {service.name}"
        return random.choice(messages)

    def _generate_latency(
        self, service: ServiceConfig, level: str
    ) -> float:
        """
        Generate realistic latency using a log-normal distribution.

        Error requests have higher latency, simulating timeouts and
        retries. The base latency varies by service.
        """
        base = service.base_latency_ms

        if level == "CRITICAL":
            # Critical errors: very high latency (timeouts)
            return random.lognormvariate(
                mu=6.5, sigma=0.5
            )  # ~660ms median
        elif level == "ERROR":
            # Errors: elevated latency
            return random.lognormvariate(
                mu=5.5, sigma=0.8
            )  # ~245ms median
        elif level == "WARNING":
            # Warnings: slightly elevated
            return base * random.uniform(1.5, 4.0)
        else:
            # Normal operations: tight distribution around base
            return max(1.0, random.gauss(base, base * 0.3))
