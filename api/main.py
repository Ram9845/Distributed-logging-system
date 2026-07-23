"""
FastAPI application entry point.

Configures the application with:
- Lifespan events for startup/shutdown of Kafka, Redis, and DB
- CORS middleware
- Request tracking middleware
- All route registrations
- Swagger / OpenAPI documentation
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from api.config import get_settings
from api.logging_config import setup_logging
from api.middleware import RequestTrackingMiddleware
from api.models.database import init_db, close_db
from api.dependencies import (
    init_kafka_service,
    close_kafka_service,
    init_redis,
    close_redis,
)

# Import routers
from api.routes import logs, metrics, simulate, health, stats

logger = structlog.get_logger(__name__)
settings = get_settings()


# =============================================================================
# Application Lifespan — Startup & Shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.

    Startup:
    - Initialize structured logging
    - Connect to PostgreSQL and ensure tables exist
    - Initialize Kafka producer
    - Initialize Redis connection

    Shutdown:
    - Close Kafka producer (flush pending messages)
    - Close Redis connection
    - Close database connection pool
    """
    # ---- Startup ----
    setup_logging()
    logger.info("Starting application", app_name=settings.app_name)

    # Database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))

    # Kafka
    try:
        await init_kafka_service()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning("Kafka initialization failed (non-critical)", error=str(e))

    # Redis
    try:
        await init_redis()
        logger.info("Redis initialized")
    except Exception as e:
        logger.warning("Redis initialization failed (non-critical)", error=str(e))

    logger.info("Application startup complete")

    yield

    # ---- Shutdown ----
    logger.info("Shutting down application")
    await close_kafka_service()
    await close_redis()
    await close_db()
    logger.info("Application shutdown complete")


# =============================================================================
# FastAPI Application Instance
# =============================================================================

app = FastAPI(
    title="Distributed Logging & Monitoring System",
    description=(
        "A production-ready distributed logging system that collects, "
        "processes, and visualizes logs from multiple microservices. "
        "Built with FastAPI, Apache Kafka, PostgreSQL, Prometheus, and Grafana.\n\n"
        "## Features\n"
        "- **Real-time log ingestion** via Apache Kafka\n"
        "- **Structured JSON logging** with correlation IDs\n"
        "- **RESTful API** for log querying and filtering\n"
        "- **Prometheus metrics** for observability\n"
        "- **Alert engine** for error rate and latency monitoring\n"
        "- **Grafana dashboards** for visualization\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    contact={
        "name": "API Support",
        "email": "support@distributed-logging.dev",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)


# =============================================================================
# Middleware
# =============================================================================

# CORS — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request tracking — adds request IDs, timing, and structured logging
app.add_middleware(RequestTrackingMiddleware)


# =============================================================================
# Route Registration
# =============================================================================

app.include_router(logs.router, prefix="/api/v1")
app.include_router(metrics.router)
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with API information and navigation links."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "metrics": "/metrics",
        "openapi": "/openapi.json",
    }
