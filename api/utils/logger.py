"""
Structured JSON logging with structlog.

Provides a pre-configured logger with JSON rendering, correlation ID
support, log rotation, and contextual binding for request tracing.
"""

import logging
import logging.handlers
import os
import structlog
from api.config import get_settings


def setup_logging() -> None:
    """
    Configure structlog with JSON output and stdlib integration.

    Sets up:
    - JSON rendering for machine-parseable logs
    - Log rotation via RotatingFileHandler (10MB per file, 5 backups)
    - Correlation ID and request ID in every log line
    - Timestamp in ISO 8601 format
    """
    settings = get_settings()

    # Ensure logs directory exists
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # ---- Configure stdlib logging ----
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler — human-readable in dev, JSON in production
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # File handler — rotating JSON logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # Error file handler — only ERROR and above
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # ---- Configure structlog ----
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Apply structlog formatter to all handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer()
            if settings.app_debug
            else structlog.processors.JSONRenderer(),
        ],
    )

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance bound to the given name.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        A bound structlog logger with JSON rendering and context support.
    """
    return structlog.get_logger(name or __name__)
