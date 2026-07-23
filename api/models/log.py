"""
SQLAlchemy ORM models for the logging system.

Defines the Log and Alert models that map to PostgreSQL tables.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    Boolean,
    DateTime,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from api.models.database import Base


class Log(Base):
    """
    ORM model for the 'logs' table.

    Stores structured log entries from all microservices, including
    trace/request IDs for distributed tracing and JSONB metadata
    for extensible context.
    """

    __tablename__ = "logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique log entry identifier",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the log event occurred",
    )
    service = Column(
        String(64),
        nullable=False,
        index=True,
        comment="Originating microservice name",
    )
    level = Column(
        String(16),
        nullable=False,
        index=True,
        comment="Log severity level",
    )
    endpoint = Column(
        String(256),
        nullable=True,
        comment="HTTP endpoint that generated the log",
    )
    latency_ms = Column(
        Float,
        nullable=True,
        comment="Request latency in milliseconds",
    )
    status_code = Column(
        Integer,
        nullable=True,
        comment="HTTP response status code",
    )
    trace_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="Distributed trace identifier",
    )
    request_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="Unique request identifier",
    )
    message = Column(
        Text,
        nullable=False,
        comment="Human-readable log message",
    )
    metadata_ = Column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Extensible metadata as JSON",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Record creation timestamp",
    )

    __table_args__ = (
        CheckConstraint(
            "level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="valid_log_level",
        ),
        Index("idx_logs_service_timestamp", "service", timestamp.desc()),
        Index("idx_logs_timestamp", timestamp.desc()),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<Log(id={self.id}, service={self.service}, "
            f"level={self.level}, message={self.message[:50]})>"
        )


class Alert(Base):
    """
    ORM model for the 'alerts' table.

    Stores alert records triggered by threshold violations
    (error rate, latency, CPU usage).
    """

    __tablename__ = "alerts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default="WARNING")
    service = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    resolved = Column(Boolean, default=False)
    triggered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict, server_default="{}")

    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'CRITICAL')",
            name="valid_alert_severity",
        ),
        Index("idx_alerts_type_triggered", "alert_type", triggered_at.desc()),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, type={self.alert_type}, "
            f"severity={self.severity})>"
        )
