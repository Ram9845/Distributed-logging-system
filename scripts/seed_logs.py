"""
Seed script — populate PostgreSQL with sample log data.

Generates a diverse set of log entries across all simulated
microservices and inserts them directly into the database.
Useful for initial dashboard testing without needing Kafka running.

Usage:
    python -m scripts.seed_logs [--count 500]
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras

# Inline constants (no dependency on api package)
SERVICES = [
    "auth-service",
    "payment-service",
    "order-service",
    "notification-service",
    "inventory-service",
]

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

ENDPOINTS = {
    "auth-service": ["/login", "/register", "/logout", "/token/refresh", "/password/reset"],
    "payment-service": ["/checkout", "/refund", "/payment/status", "/webhook/stripe", "/invoices"],
    "order-service": ["/orders", "/orders/cancel", "/orders/status", "/orders/history", "/cart"],
    "notification-service": ["/send-email", "/send-sms", "/send-push", "/templates", "/preferences"],
    "inventory-service": ["/stock/check", "/stock/update", "/stock/reserve", "/products", "/warehouses"],
}

MESSAGES = {
    "DEBUG": ["Cache hit", "Query executed", "Middleware processed", "Serialization complete"],
    "INFO": ["Request processed successfully", "User authenticated", "Order created", "Email sent", "Stock updated"],
    "WARNING": ["High latency detected", "Rate limit approaching", "Deprecated endpoint", "Queue backlog growing"],
    "ERROR": ["Database timeout", "Service unavailable", "Authentication failed", "Transaction rolled back"],
    "CRITICAL": ["All brokers down", "Data corruption detected", "Out of memory", "Disk full"],
}

STATUS_CODES = {
    "DEBUG": [200],
    "INFO": [200, 201, 204],
    "WARNING": [200, 301, 400, 408, 429],
    "ERROR": [400, 401, 403, 404, 500, 502, 503],
    "CRITICAL": [500, 502, 503, 504],
}


def generate_log_entry(time_offset_minutes: float = 0) -> dict:
    """Generate a single random log entry."""
    service = random.choice(SERVICES)
    level = random.choices(
        LOG_LEVELS, weights=[0.10, 0.50, 0.20, 0.15, 0.05], k=1
    )[0]
    endpoint = random.choice(ENDPOINTS[service])
    status_code = random.choice(STATUS_CODES[level])
    message = random.choice(MESSAGES[level])

    if level in ("ERROR", "CRITICAL"):
        latency = random.uniform(200, 2000)
    elif level == "WARNING":
        latency = random.uniform(100, 500)
    else:
        latency = random.uniform(5, 150)

    timestamp = datetime.now(timezone.utc) - timedelta(minutes=time_offset_minutes)

    return {
        "timestamp": timestamp.isoformat(),
        "service": service,
        "level": level,
        "endpoint": endpoint,
        "latency_ms": round(latency, 2),
        "status_code": status_code,
        "trace_id": f"trace-{random.randint(100000, 999999):06x}",
        "request_id": f"req-{random.randint(100000, 999999):06x}",
        "message": message,
        "metadata": json.dumps({
            "environment": "production",
            "region": random.choice(["us-east-1", "eu-west-1", "ap-south-1"]),
            "host": f"{service.split('-')[0]}-{random.randint(1, 5)}",
        }),
    }


def seed_database(count: int, db_url: str) -> None:
    """Insert seed log entries into PostgreSQL."""
    print(f"Generating {count} log entries...")

    entries = []
    for i in range(count):
        # Spread entries across the last 60 minutes
        time_offset = random.uniform(0, 60)
        entries.append(generate_log_entry(time_offset))

    print(f"Connecting to database...")
    conn = psycopg2.connect(db_url)

    insert_sql = """
        INSERT INTO logs (timestamp, service, level, endpoint, latency_ms,
                         status_code, trace_id, request_id, message, metadata)
        VALUES (%(timestamp)s, %(service)s, %(level)s, %(endpoint)s,
                %(latency_ms)s, %(status_code)s, %(trace_id)s,
                %(request_id)s, %(message)s, %(metadata)s::jsonb)
    """

    start = time.time()

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, insert_sql, entries, page_size=100)
        conn.commit()

    duration = time.time() - start

    # Print summary
    level_counts = {}
    service_counts = {}
    for e in entries:
        level_counts[e["level"]] = level_counts.get(e["level"], 0) + 1
        service_counts[e["service"]] = service_counts.get(e["service"], 0) + 1

    print(f"\n{'='*50}")
    print(f"  Seeded {count} log entries in {duration:.2f}s")
    print(f"{'='*50}")
    print(f"\n  By Level:")
    for level, cnt in sorted(level_counts.items()):
        print(f"    {level:10s}: {cnt}")
    print(f"\n  By Service:")
    for svc, cnt in sorted(service_counts.items()):
        print(f"    {svc:25s}: {cnt}")

    conn.close()
    print(f"\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed PostgreSQL with sample log data")
    parser.add_argument("--count", type=int, default=500, help="Number of logs to generate")
    parser.add_argument(
        "--db-url",
        type=str,
        default="postgresql://loguser:logpassword123@localhost:5432/logging_db",
        help="PostgreSQL connection URL",
    )
    args = parser.parse_args()

    seed_database(args.count, args.db_url)
