# =============================================================================
# Distributed Logging & Monitoring System — Makefile
# =============================================================================
# Convenience targets for building, running, testing, and managing
# the distributed logging system.
# =============================================================================

.PHONY: help up down build logs clean test lint seed status restart \
        simulate errors health stats api-docs kafka-ui grafana prometheus

# Default target
help: ## Show this help message
	@echo ""
	@echo "  Distributed Logging & Monitoring System"
	@echo "  ========================================"
	@echo ""
	@echo "  Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Docker Compose
# =============================================================================

up: ## Start all services (docker compose up --build)
	docker compose up --build -d
	@echo ""
	@echo "Services starting up..."
	@echo "  FastAPI:     http://localhost:8000/docs"
	@echo "  Kafka UI:    http://localhost:8080"
	@echo "  Grafana:     http://localhost:3000  (admin/admin123)"
	@echo "  Prometheus:  http://localhost:9090"
	@echo ""

down: ## Stop all services
	docker compose down

build: ## Build all Docker images without starting
	docker compose build

restart: ## Restart all services
	docker compose down
	docker compose up --build -d

logs: ## Tail logs from all services
	docker compose logs -f --tail=100

logs-api: ## Tail FastAPI logs
	docker compose logs -f --tail=100 fastapi

logs-producer: ## Tail producer logs
	docker compose logs -f --tail=100 producer

logs-consumer: ## Tail consumer logs
	docker compose logs -f --tail=100 consumer

logs-kafka: ## Tail Kafka broker logs
	docker compose logs -f --tail=100 kafka

status: ## Show status of all services
	docker compose ps

clean: ## Stop services and remove all volumes/data
	docker compose down -v --remove-orphans
	docker system prune -f
	@echo "Cleaned up all containers, volumes, and orphans."

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	docker compose exec fastapi pytest tests/ -v --tb=short

test-api: ## Run API tests only
	docker compose exec fastapi pytest tests/test_api.py -v

test-producer: ## Run producer tests only
	docker compose exec fastapi pytest tests/test_producer.py -v

test-consumer: ## Run consumer tests only
	docker compose exec fastapi pytest tests/test_consumer.py -v

test-coverage: ## Run tests with coverage report
	docker compose exec fastapi pytest tests/ -v --cov=api --cov-report=term-missing

# =============================================================================
# Development Utilities
# =============================================================================

simulate: ## Generate 100 simulated log entries
	curl -s -X POST http://localhost:8000/api/v1/simulate \
		-H "Content-Type: application/json" \
		-d '{"count": 100}' | python -m json.tool

errors: ## Generate 50 error logs to trigger alerts
	curl -s -X POST http://localhost:8000/api/v1/generate-errors \
		-H "Content-Type: application/json" \
		-d '{"count": 50, "severity": "ERROR"}' | python -m json.tool

health: ## Check health of all components
	curl -s http://localhost:8000/api/v1/health | python -m json.tool

stats: ## Get log statistics
	curl -s http://localhost:8000/api/v1/stats | python -m json.tool

seed: ## Seed database with sample logs via simulation
	curl -s -X POST http://localhost:8000/api/v1/simulate \
		-H "Content-Type: application/json" \
		-d '{"count": 500}' | python -m json.tool
	@echo "Seeded 500 log entries."

# =============================================================================
# Service URLs
# =============================================================================

api-docs: ## Open FastAPI Swagger docs
	@echo "Opening http://localhost:8000/docs"
	@start http://localhost:8000/docs 2>/dev/null || open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null

kafka-ui: ## Open Kafka UI
	@echo "Opening http://localhost:8080"
	@start http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || xdg-open http://localhost:8080 2>/dev/null

grafana: ## Open Grafana dashboard
	@echo "Opening http://localhost:3000 (admin/admin123)"
	@start http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null

prometheus: ## Open Prometheus UI
	@echo "Opening http://localhost:9090"
	@start http://localhost:9090 2>/dev/null || open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null

# =============================================================================
# Database
# =============================================================================

db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U loguser -d logging_db

db-logs: ## Query recent logs from database
	docker compose exec postgres psql -U loguser -d logging_db \
		-c "SELECT id, timestamp, service, level, message FROM logs ORDER BY timestamp DESC LIMIT 20;"

db-stats: ## Query log statistics from database
	docker compose exec postgres psql -U loguser -d logging_db \
		-c "SELECT service, level, COUNT(*) as count FROM logs GROUP BY service, level ORDER BY service, level;"

# =============================================================================
# Kafka
# =============================================================================

kafka-topics: ## List Kafka topics
	docker compose exec kafka kafka-topics --list --bootstrap-server kafka:29092

kafka-consume: ## Consume messages from service-logs topic
	docker compose exec kafka kafka-console-consumer \
		--bootstrap-server kafka:29092 \
		--topic service-logs \
		--from-beginning \
		--max-messages 10
