"""
FastAPI dependency injection.

Provides reusable dependencies for database sessions, Kafka producer,
Redis client, and service instances. Follows the Dependency Injection
pattern for testability and clean separation of concerns.
"""

from typing import AsyncGenerator
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from api.config import get_settings
from api.models.database import async_session_factory
from api.repository.log_repository import LogRepository
from api.services.log_service import LogService
from api.services.kafka_service import KafkaService
from api.services.alert_service import AlertService

settings = get_settings()

# ---- Singleton-like service holders (initialized at startup) ----
_kafka_service: KafkaService | None = None
_redis_client: aioredis.Redis | None = None
_alert_service: AlertService | None = None


# =============================================================================
# Database Session
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session scoped to a single request.

    Commits on success, rolls back on exception, and always closes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Repository
# =============================================================================

async def get_log_repository(
    session: AsyncSession = None,
) -> LogRepository:
    """Return a LogRepository bound to the given session."""
    return LogRepository(session)


# =============================================================================
# Kafka
# =============================================================================

async def get_kafka_service() -> KafkaService:
    """Return the shared Kafka producer service instance."""
    global _kafka_service
    if _kafka_service is None:
        _kafka_service = KafkaService(settings)
        await _kafka_service.start()
    return _kafka_service


async def init_kafka_service() -> None:
    """Initialize the Kafka service at application startup."""
    global _kafka_service
    _kafka_service = KafkaService(settings)
    await _kafka_service.start()


async def close_kafka_service() -> None:
    """Shut down the Kafka service at application shutdown."""
    global _kafka_service
    if _kafka_service is not None:
        await _kafka_service.stop()
        _kafka_service = None


# =============================================================================
# Redis
# =============================================================================

async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client


async def init_redis() -> None:
    """Initialize the Redis connection at application startup."""
    global _redis_client
    try:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        await _redis_client.ping()
    except Exception:
        # Redis is optional — log warning but don't crash
        _redis_client = None


async def close_redis() -> None:
    """Close the Redis connection at application shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


# =============================================================================
# Alert Service
# =============================================================================

async def get_alert_service() -> AlertService:
    """Return the shared AlertService instance."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service


# =============================================================================
# Composite Dependencies (for route handlers)
# =============================================================================

async def get_log_service(
    session: AsyncSession = None,
) -> LogService:
    """
    Return a LogService wired with its dependencies.

    This is the primary dependency for log-related route handlers.
    """
    repository = LogRepository(session)
    return LogService(repository)
