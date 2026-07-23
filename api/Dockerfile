# =============================================================================
# FastAPI Application — Dockerfile
# =============================================================================
# Multi-stage optimized build for the FastAPI REST API service.
# Uses Python 3.12-slim for minimal image size.
# =============================================================================

FROM python:3.12-slim AS base

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by asyncpg and confluent-kafka
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        librdkafka-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Dependencies (cached layer) ----
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Application code ----
COPY api/ ./api/

# Create logs directory
RUN mkdir -p /app/logs

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
