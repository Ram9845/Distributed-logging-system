"""
Logging configuration module.

Provides a single entry point to initialize the application's
structured logging subsystem, re-exporting from utils.logger.
"""

from api.utils.logger import setup_logging, get_logger

__all__ = ["setup_logging", "get_logger"]
