# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication is required for the development environment.

---

## Endpoints

### Root

#### `GET /`

Returns application metadata and navigation links.

**Response:**
```json
{
  "name": "Distributed Logging & Monitoring System",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/api/v1/health",
  "metrics": "/metrics"
}
```

---

### Logs

#### `GET /api/v1/logs`

Retrieve paginated log entries with optional filtering.

**Query Parameters:**

| Parameter       | Type    | Default | Description                    |
|----------------|---------|---------|--------------------------------|
| `service`      | string  | null    | Filter by service name         |
| `level`        | string  | null    | Filter by log level            |
| `trace_id`     | string  | null    | Filter by trace ID             |
| `endpoint`     | string  | null    | Filter by endpoint             |
| `min_latency_ms` | float | null    | Minimum latency in ms          |
| `max_latency_ms` | float | null    | Maximum latency in ms          |
| `status_code`  | int     | null    | Filter by HTTP status code     |
| `search`       | string  | null    | Full-text search in messages   |
| `page`         | int     | 1       | Page number (min: 1)           |
| `page_size`    | int     | 50      | Results per page (max: 500)    |

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/logs?service=auth-service&level=ERROR&page=1&page_size=10"
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 10 of 42 logs",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-15T10:30:00Z",
      "service": "auth-service",
      "level": "ERROR",
      "endpoint": "/login",
      "latency_ms": 420.5,
      "status_code": 500,
      "trace_id": "trace-abc123def456",
      "request_id": "req-xyz789abc012",
      "message": "Invalid credentials provided",
      "metadata": {},
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 42,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

---

#### `GET /api/v1/logs/{log_id}`

Retrieve a single log entry by UUID.

**Example:**
```bash
curl "http://localhost:8000/api/v1/logs/550e8400-e29b-41d4-a716-446655440000"
```

**404 Response:**
```json
{
  "detail": "Log entry with ID '...' not found"
}
```

---

#### `GET /api/v1/logs/service/{service}`

Retrieve logs for a specific microservice.

**Example:**
```bash
curl "http://localhost:8000/api/v1/logs/service/payment-service?page=1&page_size=20"
```

---

#### `GET /api/v1/logs/level/{level}`

Retrieve logs at a specific severity level.

**Example:**
```bash
curl "http://localhost:8000/api/v1/logs/level/WARNING"
```

---

### Simulation

#### `POST /api/v1/simulate`

Generate simulated log entries from multiple microservices.

**Request Body:**
```json
{
  "count": 100,
  "services": ["auth-service", "payment-service"],
  "error_rate": 0.15
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully generated 100 log entries",
  "data": {
    "total_generated": 100,
    "stored_in_db": 100,
    "published_to_kafka": 100,
    "by_level": { "INFO": 50, "WARNING": 20, "ERROR": 15, "DEBUG": 10, "CRITICAL": 5 },
    "by_service": { "auth-service": 52, "payment-service": 48 }
  }
}
```

---

#### `POST /api/v1/generate-errors`

Generate a burst of error logs to trigger alerting rules.

**Request Body:**
```json
{
  "count": 50,
  "service": "payment-service",
  "severity": "ERROR"
}
```

---

### Health

#### `GET /api/v1/health`

Deep health check verifying all dependent services.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "postgresql": { "status": "healthy", "latency_ms": 5.2, "message": "Connection OK" },
    "kafka": { "status": "healthy", "latency_ms": 12.8, "message": "Broker connectivity OK" },
    "redis": { "status": "healthy", "latency_ms": 1.1, "message": "Connection OK" }
  },
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

---

### Statistics

#### `GET /api/v1/stats`

Returns aggregate statistics across all log entries.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_logs": 15000,
    "logs_by_level": { "INFO": 7500, "WARNING": 3000, "ERROR": 2250, "DEBUG": 1500, "CRITICAL": 750 },
    "logs_by_service": { "auth-service": 3000, "payment-service": 3000, "...": "..." },
    "avg_latency_ms": 125.5,
    "p95_latency_ms": 450.0,
    "p99_latency_ms": 890.0,
    "error_rate": 0.15,
    "logs_per_minute": 42.5,
    "top_endpoints": [{ "endpoint": "/login", "count": 500, "avg_latency_ms": 45.0 }],
    "top_error_messages": [{ "message": "Database timeout", "service": "payment-service", "count": 120 }],
    "active_alerts": 2
  }
}
```

---

### Metrics

#### `GET /metrics`

Prometheus metrics in exposition format.

**Example:**
```bash
curl http://localhost:8000/metrics
```

Returns text/plain with all registered Prometheus counters, histograms, and gauges.

---

## OpenAPI / Swagger

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
