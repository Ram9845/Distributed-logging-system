# 🔍 Distributed Logging & Monitoring System

A **production-ready** distributed logging system that collects, processes, stores, and visualizes structured logs from multiple microservices in real time. Built with modern Python backend technologies, Apache Kafka for event streaming, PostgreSQL for persistence, and a full observability stack with Prometheus, Grafana, and Loki.

---

## 🚀 Quick Start & How to Run

### Prerequisites
Make sure you have installed:
- **Docker Desktop** (or Docker Engine with Docker Compose v2)
- At least 4 GB RAM available for containers
- Ports 3000(grafana), 5432(postgres), 6379, 8000(fastapi), 8080(kafka), 9090(prometheus), 9092, 9100(Loki), 9308 available

### 1. Configure the Environment
Before starting, create your environment variables file:
```bash
cp .env.example .env
```
*(You can leave the defaults in `.env` as they are perfect for local development).*

### 2. Start the Project
Use Docker Compose to build and start all 14 services in the background:
```bash
docker compose up --build -d
```
> **Note:** The first run will take a few minutes as it downloads all the necessary images (Kafka, Postgres, Grafana, etc.) and builds the Python containers.

### 3. Verify it's Running
To check the status of all containers:
```bash
docker compose ps
```
*(Wait until you see the `kafka` and `fastapi` containers marked as "Healthy" or "Up").*

### 4. Open the Dashboards

Once everything is running, you can access the system through your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| **FastAPI Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | — |
| **Grafana Dashboards** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin123` |
| **Kafka UI** | [http://localhost:8080](http://localhost:8080) | — |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | — |

---

## 🎮 Interacting with the System (No `make` required)

If you don't have `make` installed (e.g., you are on Windows Git Bash), you can use these direct commands to interact with the API and database.

### 1. Simulate Traffic
To see data appear in Grafana, generate 100 random log entries across 5 simulated microservices:
```bash
curl -s -X POST http://localhost:8000/api/v1/simulate -H "Content-Type: application/json" -d "{\"count\": 100}"
```

### 2. Trigger Alerts
Generate a sudden burst of 50 errors. This will trigger the Prometheus Alerting rules, which you can see in the Grafana "Logging Dashboard":
```bash
curl -s -X POST http://localhost:8000/api/v1/generate-errors -H "Content-Type: application/json" -d "{\"count\": 50, \"severity\": \"ERROR\"}"
```

### 3. Check System Health & Stats
**System Health:**
```bash
curl -s http://localhost:8000/api/v1/health
```
**Aggregate Stats:**
```bash
curl -s http://localhost:8000/api/v1/stats
```

### 4. Explore the Database
To open an interactive PostgreSQL shell and query the logs manually:
```bash
docker compose exec postgres psql -U loguser -d logging_db
```
*(Once inside, try: `SELECT timestamp, service, level, message FROM logs ORDER BY timestamp DESC LIMIT 10;`. Type `\q` to exit).*

### 5. Stop the Project
When you are done, shut everything down gracefully:
```bash
docker compose down
```
If you ever want to wipe all data (reset the database, wipe Kafka topics, etc.) and start completely fresh:
```bash
docker compose down -v --remove-orphans
```

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

- **🚀 FastAPI REST API:** Full CRUD for log entries, pagination, and Swagger UI.
- **📡 Apache Kafka:** Producer (batching, gzip, retries) and Consumer (manual offset commits, dead letter queue).
- **📊 Observability:** 3 Grafana Dashboards (Logging, Kafka, System), Prometheus metrics, Loki container logs, and Alert rules.
- **🗄️ Data Layer:** PostgreSQL with optimized indexes, JSONB metadata, and async SQLAlchemy 2.0.
- **🐳 Docker:** 14 orchestrated services with health checks and dependency ordering.

---

## 📝 Bullets

- **Designed and built** a distributed logging system processing 1000+ logs/minute from 5 microservices using FastAPI, Apache Kafka, and PostgreSQL
- **Implemented** real-time log ingestion pipeline with Kafka producer (batching, gzip compression, idempotent delivery) and consumer (manual offset management, dead letter queue, batch DB inserts)
- **Built** comprehensive observability stack with Prometheus (20+ custom metrics), Grafana (3 auto-provisioned dashboards with heatmaps, gauges, pie charts), Loki, and Promtail
- **Configured** alerting rules for error rate (>20/min), p95 latency (>500ms), CPU (>80%), and Kafka consumer lag with Prometheus alert rules
- **Architected** the API using Clean Architecture (SOLID principles, Repository Pattern, Dependency Injection) with async SQLAlchemy, Pydantic v2 validation, and structured JSON logging
- **Containerized** 14 services with Docker Compose including health checks, dependency ordering, and named volumes for persistence

---

## 📄 License
MIT License
