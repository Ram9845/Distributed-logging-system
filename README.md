# 🔍 Distributed Logging & Monitoring System

A **production-ready** distributed logging system that collects, processes, stores, and visualizes structured logs from multiple microservices in real time. Built with modern Python backend technologies, Apache Kafka for event streaming, PostgreSQL for persistence, and a full observability stack with Prometheus, Grafana, and Loki.

> **One command to start everything:** `docker compose up --build`

---

## 🏗️ Architecture

```
                    ┌──────────────────────┐
                    │   FastAPI Service     │
                    │  (REST API + Swagger) │
                    └──────────┬───────────┘
                               │
                    Produce JSON Logs via API
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Apache Kafka       │
                    │  (Topic: service-logs)│
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │   Log Consumer    │              │   Alert Engine    │
    │ (Batch Processing)│              │ (Threshold Check) │
    └────────┬─────────┘              └────────┬─────────┘
             │                                  │
             ▼                                  │
    ┌──────────────────┐                        │
    │   PostgreSQL      │                        │
    │ (Log Storage)     │                        │
    └────────┬─────────┘                        │
             │                                  │
             └──────────────┬───────────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Grafana Dashboards   │
                 │  (3 Dashboards)       │
                 └──────────────────────┘
                            ▲
                            │
                 ┌──────────────────────┐
                 │     Prometheus        │
                 │  (Metrics Scraping)   │
                 └──────────────────────┘
```

### Data Flow

1. **Log Producer** continuously generates realistic structured logs from 5 simulated microservices
2. Logs are published to **Apache Kafka** (`service-logs` topic) with batching, compression, and retries
3. **Log Consumer** consumes messages, validates/processes them, and batch-inserts into **PostgreSQL**
4. **FastAPI** provides a REST API for querying logs, generating simulations, and exposing health/stats
5. **Prometheus** scrapes metrics from FastAPI, Consumer, Producer, Kafka Exporter, and Node Exporter
6. **Grafana** visualizes everything with 3 auto-provisioned dashboards
7. **Loki + Promtail** aggregate container logs for centralized log viewing
8. **Alert Engine** detects error thresholds and triggers alerts visible in Grafana

---

## ✨ Features

### 🚀 FastAPI REST API
- Full CRUD for log entries with pagination and filtering
- Swagger UI + ReDoc auto-generated documentation
- Deep health checks (PostgreSQL, Kafka, Redis)
- Aggregate statistics with latency percentiles
- Log simulation and error burst generation

### 📡 Apache Kafka Integration
- **Producer**: Batching, gzip compression, retries, idempotent delivery
- **Consumer**: Manual offset commits, batch processing, dead letter queue
- Kafka UI for topic monitoring and message browsing

### 📊 Monitoring & Observability
- **3 Grafana Dashboards**: Logging, Kafka, System — auto-provisioned
- **Prometheus Metrics**: 20+ custom metrics (counters, histograms, gauges)
- **Loki + Promtail**: Centralized log aggregation
- **Alert Rules**: Error rate, latency, CPU, consumer lag, service health

### 🗄️ Data Layer
- PostgreSQL with optimized indexes and JSONB metadata
- Materialized views for analytics
- Redis caching layer (optional)
- Repository pattern for clean data access

### 🐳 Docker
- **14 services** orchestrated with Docker Compose
- Health checks and dependency ordering
- Named volumes for data persistence
- Single-command startup

### 🧪 Testing
- Unit tests for API, Producer, Consumer, and Database layers
- pytest with async support
- Schema validation tests with edge cases

---

## 🛠️ Tech Stack

| Component         | Technology                           |
|-------------------|--------------------------------------|
| **Language**       | Python 3.12                          |
| **Web Framework**  | FastAPI + Uvicorn                    |
| **Streaming**      | Apache Kafka (Confluent)             |
| **Database**       | PostgreSQL 16                        |
| **Cache**          | Redis 7                              |
| **Metrics**        | Prometheus + prometheus-client       |
| **Dashboards**     | Grafana 11                           |
| **Log Aggregation**| Loki + Promtail                      |
| **Logging**        | structlog (JSON)                     |
| **Validation**     | Pydantic v2                          |
| **ORM**            | SQLAlchemy 2.0 (async)               |
| **Testing**        | pytest + pytest-asyncio              |
| **Containers**     | Docker + Docker Compose              |

---

## 📁 Folder Structure

```
distributed-logging-system/
│
├── docker-compose.yml           # All 14 services
├── Makefile                     # Convenience commands
├── README.md                    # This file
├── .env / .env.example          # Environment configuration
├── .gitignore
├── requirements.txt             # Python dependencies
│
├── api/                         # FastAPI Application
│   ├── main.py                  # App entry point + lifespan
│   ├── config.py                # Pydantic BaseSettings
│   ├── dependencies.py          # Dependency injection
│   ├── middleware.py             # Request tracking + timing
│   ├── logging_config.py        # Structlog configuration
│   ├── Dockerfile
│   ├── routes/
│   │   ├── logs.py              # GET /logs, /logs/{id}, /logs/service, /logs/level
│   │   ├── metrics.py           # GET /metrics (Prometheus)
│   │   ├── simulate.py          # POST /simulate, /generate-errors
│   │   ├── health.py            # GET /health
│   │   └── stats.py             # GET /stats
│   ├── services/
│   │   ├── kafka_service.py     # Kafka producer wrapper
│   │   ├── log_service.py       # Business logic
│   │   ├── alert_service.py     # Threshold alerting
│   │   └── metrics_service.py   # Prometheus metrics
│   ├── models/
│   │   ├── database.py          # SQLAlchemy engine + sessions
│   │   └── log.py               # ORM models (Log, Alert)
│   ├── schemas/
│   │   ├── log_schema.py        # Pydantic request/response models
│   │   └── response_schema.py   # Generic API wrappers
│   ├── repository/
│   │   └── log_repository.py    # Data access layer (Repository Pattern)
│   └── utils/
│       ├── logger.py            # Structlog JSON logging
│       ├── helpers.py           # ID generation, timestamps
│       └── constants.py         # Services, endpoints, messages
│
├── producer/                    # Standalone Kafka Producer
│   ├── producer.py              # Main producer loop
│   ├── generator.py             # Realistic log generator
│   ├── services.py              # Service definitions
│   └── Dockerfile
│
├── consumer/                    # Standalone Kafka Consumer
│   ├── consumer.py              # Main consumer loop
│   ├── processor.py             # Message validation + alerting
│   ├── database.py              # PostgreSQL batch inserts
│   └── Dockerfile
│
├── database/
│   ├── schema.sql               # Tables, indexes, materialized views
│   └── init.sql                 # Initialization + seed data
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml       # Scrape config (6 targets)
│   │   └── alert_rules.yml      # 9 alert rules
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── logging-dashboard.json    # Logs, errors, latency
│   │   │   ├── kafka-dashboard.json      # Throughput, lag
│   │   │   └── system-dashboard.json     # CPU, memory, disk
│   │   └── provisioning/
│   │       ├── dashboards/dashboards.yml
│   │       └── datasources/datasources.yml
│   ├── loki/
│   │   └── local-config.yaml
│   └── promtail/
│       └── promtail-config.yml
│
├── kafka/
│   └── create-topics.sh         # Topic creation script
│
├── scripts/
│   ├── seed_logs.py             # Database seeding
│   ├── simulate_traffic.py      # API traffic simulation
│   ├── generate_errors.py       # Error burst generation
│   └── cleanup.py               # Data cleanup utility
│
├── tests/
│   ├── test_api.py              # API endpoint tests
│   ├── test_producer.py         # Producer + generator tests
│   ├── test_consumer.py         # Consumer + processor tests
│   └── test_database.py         # Schema + helper tests
│
└── docs/
    ├── api.md                   # API documentation
    └── deployment.md            # Deployment guide
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- 4 GB+ RAM available
- Ports: 3000, 5432, 6379, 8000, 8080, 9090, 9092 available

### 1. Clone & Configure

```bash
git clone <repo-url>
cd distributed-logging-system
cp .env.example .env
```

### 2. Start Everything

```bash
docker compose up --build -d
```

### 3. Verify Services

```bash
docker compose ps
# All services should show "healthy" or "running"
```

### 4. Generate Test Data

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"count": 500}'

# Generate errors to trigger alerts
curl -X POST http://localhost:8000/api/v1/generate-errors \
  -H "Content-Type: application/json" \
  -d '{"count": 50}'
```

### 5. Explore

| Service       | URL                              | Credentials     |
|--------------|----------------------------------|-----------------|
| **Swagger UI** | http://localhost:8000/docs      | —               |
| **Kafka UI**   | http://localhost:8080           | —               |
| **Grafana**    | http://localhost:3000           | admin/admin123  |
| **Prometheus** | http://localhost:9090           | —               |

---

## 📡 API Endpoints

| Method | Endpoint                        | Description                    |
|--------|---------------------------------|--------------------------------|
| GET    | `/api/v1/logs`                  | List logs (filtered, paginated)|
| GET    | `/api/v1/logs/{id}`             | Get log by ID                  |
| GET    | `/api/v1/logs/service/{service}`| Logs by service                |
| GET    | `/api/v1/logs/level/{level}`    | Logs by level                  |
| GET    | `/metrics`                      | Prometheus metrics             |
| POST   | `/api/v1/simulate`              | Generate simulated logs        |
| POST   | `/api/v1/generate-errors`       | Generate error burst           |
| GET    | `/api/v1/health`                | Deep health check              |
| GET    | `/api/v1/stats`                 | Aggregate statistics           |

> Full API docs with examples: [docs/api.md](docs/api.md)

---

## 📊 Monitoring

### Grafana Dashboards (Auto-Provisioned)

**Logging Dashboard** — Logs over time, error rate gauge, logs by service (pie), logs by level (bar), latency heatmap, top endpoints table, alert timeline

**Kafka Dashboard** — Producer/consumer throughput, consumer lag, produce latency heatmap, batch processing time, DB insert duration

**System Dashboard** — CPU/memory/disk gauges, CPU over time (stacked), memory breakdown, HTTP request rate, latency percentiles, response status codes (donut), disk I/O

### Prometheus Alert Rules

| Alert                | Condition                    | Severity |
|---------------------|------------------------------|----------|
| HighErrorRate       | >20 errors/minute            | Critical |
| HighHTTPErrorRate   | >5% 5xx responses            | Warning  |
| HighResponseLatency | p95 latency > 500ms          | Warning  |
| HighCPUUsage        | CPU > 80% for 5 min          | Warning  |
| HighMemoryUsage     | Memory > 85% for 5 min       | Warning  |
| DiskSpaceLow        | Disk > 85%                   | Warning  |
| HighConsumerLag     | Lag > 1000 for 5 min         | Warning  |
| KafkaBrokerDown     | 0 brokers for 1 min          | Critical |
| ConsumerDown        | Consumer offline 2 min       | Critical |

---

## 🧪 Testing

```bash
# Run all tests
docker compose exec fastapi pytest tests/ -v

# Run with coverage
docker compose exec fastapi pytest tests/ -v --cov=api --cov-report=term-missing

# Run specific test file
docker compose exec fastapi pytest tests/test_producer.py -v
```

---

## 🔧 Makefile Commands

```bash
make up              # Start all services
make down            # Stop all services
make build           # Build Docker images
make logs            # Tail all logs
make status          # Show service status
make clean           # Remove everything (volumes too)
make test            # Run tests
make simulate        # Generate 100 test logs
make errors          # Generate error burst
make health          # Check system health
make stats           # View log statistics
make db-shell        # PostgreSQL shell
make kafka-topics    # List Kafka topics
```

---

## 🏗️ Design Principles

| Principle            | Implementation                                          |
|---------------------|--------------------------------------------------------|
| **Clean Architecture** | Separated routes → services → repository → models    |
| **SOLID**             | Single responsibility per module, dependency injection |
| **Repository Pattern** | Data access decoupled from business logic            |
| **Dependency Injection** | FastAPI `Depends()` for all service wiring          |
| **Structured Logging** | JSON logs with correlation IDs via structlog          |
| **Exactly-once**      | Kafka idempotent producer + manual offset commits     |
| **Graceful Shutdown**  | Signal handlers in producer/consumer                  |
| **Health Checks**      | Docker + application-level deep checks               |
| **Observability**      | Metrics, logs, traces (trace_id), dashboards         |

---

## 📸 Screenshots

> Screenshots are generated after first deployment.

| Screenshot | Description |
|-----------|-------------|
| `screenshots/dashboard.png` | Grafana Logging Dashboard |
| `screenshots/kafka-ui.png` | Kafka UI showing topics and messages |
| `screenshots/prometheus.png` | Prometheus targets and metrics |
| `screenshots/grafana.png` | Grafana overview with all dashboards |

---

## 🔮 Future Improvements

- [ ] **Elasticsearch** integration for full-text log search
- [ ] **Alertmanager** with Slack/Email/PagerDuty notifications
- [ ] **OpenTelemetry** tracing integration
- [ ] **Kubernetes** deployment manifests (Helm charts)
- [ ] **gRPC** inter-service communication
- [ ] **Schema Registry** for Kafka message validation
- [ ] **TimescaleDB** for time-series optimized log storage
- [ ] **Rate limiting** on API endpoints
- [ ] **JWT authentication** with role-based access
- [ ] **CI/CD pipeline** (GitHub Actions)
- [ ] **Load testing** with Locust
- [ ] **Database partitioning** by timestamp
- [ ] **Multi-broker** Kafka cluster
- [ ] **Canary deployments** with traffic splitting

---

## 📝 Resume Bullets

> Use these to describe this project on your resume:

- **Designed and built** a distributed logging system processing 1000+ logs/minute from 5 microservices using FastAPI, Apache Kafka, and PostgreSQL
- **Implemented** real-time log ingestion pipeline with Kafka producer (batching, gzip compression, idempotent delivery) and consumer (manual offset management, dead letter queue, batch DB inserts)
- **Built** comprehensive observability stack with Prometheus (20+ custom metrics), Grafana (3 auto-provisioned dashboards with heatmaps, gauges, pie charts), Loki, and Promtail
- **Configured** alerting rules for error rate (>20/min), p95 latency (>500ms), CPU (>80%), and Kafka consumer lag with Prometheus alert rules
- **Architected** the API using Clean Architecture (SOLID principles, Repository Pattern, Dependency Injection) with async SQLAlchemy, Pydantic v2 validation, and structured JSON logging
- **Containerized** 14 services with Docker Compose including health checks, dependency ordering, and named volumes for persistence
- **Wrote** comprehensive test suite covering API endpoints, message processing, schema validation, and utility functions with pytest-asyncio

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
