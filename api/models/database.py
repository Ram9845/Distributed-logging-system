"""
Async SQLAlchemy database engine and session management.

Provides the async engine, session factory, and Base class for ORM models.
Uses connection pooling optimized for high-throughput log ingestion.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from api.config import get_settings


settings = get_settings()

# Async engine with connection pooling tuned for write-heavy workloads
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,         # Detect stale connections
    pool_recycle=3600,          # Recycle connections every hour
    connect_args={
        "server_settings": {
            "application_name": "distributed-logging-system",
        }
    },
)

# Session factory — each call produces a new AsyncSession
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db_session() -> AsyncSession:
    """
    Yield an async database session.

    Used as a FastAPI dependency. The session is automatically
    closed when the request completes.
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


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    Called during application startup. In production, prefer
    Alembic migrations over auto-creation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine and close all connections."""
    await engine.dispose()
