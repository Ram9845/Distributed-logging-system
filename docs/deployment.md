# Deployment Guide

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- At least 4 GB RAM available for containers
- Ports 3000, 5432, 6379, 8000, 8080, 9090, 9092, 9100, 9308 available

---

## Local Development

### Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd distributed-logging-system

# Copy environment file
cp .env.example .env

# Start everything
docker compose up --build -d

# Verify services
docker compose ps
```

### Access Points

| Service       | URL                          | Credentials       |
|--------------|------------------------------|--------------------|
| FastAPI Docs | http://localhost:8000/docs   | —                  |
| Kafka UI     | http://localhost:8080        | —                  |
| Grafana      | http://localhost:3000        | admin / admin123   |
| Prometheus   | http://localhost:9090        | —                  |
| PostgreSQL   | localhost:5432               | loguser / logpassword123 |

### Generate Test Data

```bash
# Generate 500 simulated logs
make simulate

# Generate error burst (triggers alerts)
make errors

# Seed database directly
python -m scripts.seed_logs --count 1000
```

---

## Service Architecture

### Startup Order

Docker Compose health checks ensure correct startup ordering:

1. **Zookeeper** → (healthy)
2. **Kafka** → (depends on Zookeeper)
3. **PostgreSQL** → (healthy)
4. **Redis** → (healthy)
5. **Kafka Init** → creates topics, then exits
6. **FastAPI** → (depends on Kafka, PG, Redis)
7. **Producer** → (depends on Kafka)
8. **Consumer** → (depends on Kafka, PG)
9. **Prometheus** → scrapes all targets
10. **Grafana** → (depends on Prometheus)
11. **Loki + Promtail** → log aggregation
12. **Kafka Exporter + Node Exporter** → metrics exporters

---

## Production Considerations

### Security

- [ ] Change all default passwords in `.env`
- [ ] Enable Kafka authentication (SASL/SSL)
- [ ] Configure Grafana HTTPS and proper admin credentials
- [ ] Use PostgreSQL connection pooling (PgBouncer)
- [ ] Add API authentication (JWT/OAuth2)
- [ ] Network segmentation between services

### Scaling

- [ ] Increase Kafka partitions for `service-logs` topic
- [ ] Run multiple consumer instances (same group ID)
- [ ] Add PostgreSQL read replicas
- [ ] Deploy FastAPI with multiple workers behind a load balancer
- [ ] Use Redis cluster for high availability

### Monitoring

- [ ] Configure Alertmanager for Slack/Email notifications
- [ ] Set up Grafana alerting rules with notification channels
- [ ] Add uptime monitoring (e.g., UptimeRobot)
- [ ] Configure log retention policies

### Data Management

- [ ] Set up PostgreSQL partitioning by timestamp
- [ ] Configure Kafka log retention (default: 7 days)
- [ ] Implement automated cleanup (see `scripts/cleanup.py`)
- [ ] Set up database backups

---

## Troubleshooting

### Kafka not starting
```bash
# Check Zookeeper health
docker compose logs zookeeper

# Restart Kafka
docker compose restart kafka
```

### Consumer lag increasing
```bash
# Check consumer logs
docker compose logs consumer

# Check Kafka UI for lag
# http://localhost:8080
```

### Database connection errors
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Connect directly
docker compose exec postgres psql -U loguser -d logging_db
```

### Clean restart
```bash
# Remove all volumes and rebuild
make clean
make up
```

---

## Environment Variables

See [.env.example](../.env.example) for all available configuration options.

Key variables to customize for production:

| Variable                | Description                    | Default             |
|------------------------|--------------------------------|---------------------|
| `POSTGRES_PASSWORD`    | Database password              | logpassword123      |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password   | admin123            |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address        | kafka:29092         |
| `LOG_LEVEL`            | Application log level          | INFO                |
| `PRODUCER_INTERVAL_MS` | Log generation interval        | 500                 |
| `PRODUCER_BATCH_SIZE`  | Logs per batch                 | 10                  |
