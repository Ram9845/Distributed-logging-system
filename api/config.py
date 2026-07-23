"""
Application configuration using Pydantic BaseSettings.

Loads configuration from environment variables with sensible defaults.
Supports .env file loading for local development.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for all application components."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "Distributed Logging & Monitoring System"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ---- PostgreSQL ----
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "logging_db"
    postgres_user: str = "loguser"
    postgres_password: str = "logpassword123"
    database_url: str = "postgresql+asyncpg://loguser:logpassword123@postgres:5432/logging_db"

    # ---- Apache Kafka ----
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_topic_logs: str = "service-logs"
    kafka_topic_alerts: str = "alerts"
    kafka_topic_dlq: str = "dead-letter-logs"
    kafka_group_id: str = "log-consumer-group"
    kafka_auto_offset_reset: str = "earliest"
    kafka_batch_size: int = 16384
    kafka_linger_ms: int = 10
    kafka_compression_type: str = "gzip"
    kafka_max_retries: int = 3

    # ---- Redis ----
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_ttl: int = 300

    # ---- Monitoring ----
    prometheus_port: int = 9090
    loki_host: str = "loki"
    loki_port: int = 3100

    # ---- Producer ----
    producer_interval_ms: int = 500
    producer_batch_size: int = 10
    producer_metrics_port: int = 8002

    # ---- Consumer ----
    consumer_batch_size: int = 50
    consumer_metrics_port: int = 8001
    consumer_poll_timeout_ms: int = 1000

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database URL (for Alembic, scripts, etc.)."""
        return self.database_url.replace(
            "postgresql+asyncpg", "postgresql+psycopg2"
        )

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Uses lru_cache to avoid re-reading .env on every call.
    """
    return Settings()
