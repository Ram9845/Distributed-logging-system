"""
Kafka log producer — standalone service.

Continuously generates realistic log entries from simulated
microservices and publishes them to Kafka with batching,
compression, and retry logic. Exposes Prometheus metrics.
"""

import json
import os
import sys
import time
import signal
import logging
from typing import Any

from confluent_kafka import Producer, KafkaError
from prometheus_client import (
    Counter, Histogram, Gauge, start_http_server,
)

from producer.generator import LogGenerator

# =============================================================================
# Configuration from environment
# =============================================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_LOGS", "service-logs")
PRODUCER_INTERVAL_MS = int(os.getenv("PRODUCER_INTERVAL_MS", "500"))
PRODUCER_BATCH_SIZE = int(os.getenv("PRODUCER_BATCH_SIZE", "10"))
PRODUCER_METRICS_PORT = int(os.getenv("PRODUCER_METRICS_PORT", "8002"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("producer")

# =============================================================================
# Prometheus Metrics
# =============================================================================

MESSAGES_PRODUCED = Counter(
    "producer_messages_produced_total",
    "Total messages produced",
    ["topic", "service", "level"],
)

PRODUCE_LATENCY = Histogram(
    "producer_produce_latency_seconds",
    "Time to produce a message",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)

PRODUCE_ERRORS = Counter(
    "producer_errors_total",
    "Total produce errors",
)

BATCH_SIZE_HIST = Histogram(
    "producer_batch_size",
    "Size of produced batches",
    buckets=[1, 5, 10, 25, 50, 100],
)

PRODUCER_UPTIME = Gauge(
    "producer_uptime_seconds",
    "Producer uptime in seconds",
)


# =============================================================================
# Kafka Producer
# =============================================================================

class LogProducer:
    """
    Standalone Kafka producer that continuously generates and
    publishes log entries to the configured Kafka topic.
    """

    def __init__(self) -> None:
        self._running = False
        self._producer: Producer | None = None
        self._generator = LogGenerator()
        self._start_time = time.time()
        self._total_produced = 0

    def start(self) -> None:
        """Initialize the Kafka producer and start the produce loop."""
        logger.info(
            f"Starting producer | bootstrap={KAFKA_BOOTSTRAP_SERVERS} | "
            f"topic={KAFKA_TOPIC} | batch_size={PRODUCER_BATCH_SIZE} | "
            f"interval={PRODUCER_INTERVAL_MS}ms"
        )

        # Start Prometheus metrics server
        start_http_server(PRODUCER_METRICS_PORT)
        logger.info(f"Prometheus metrics exposed on port {PRODUCER_METRICS_PORT}")

        # Initialize Kafka producer with production settings
        config = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "log-producer",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 200,
            "batch.size": 16384,
            "linger.ms": 10,
            "compression.type": "gzip",
            "enable.idempotence": True,
            "max.in.flight.requests.per.connection": 5,
            "queue.buffering.max.messages": 100000,
        }

        self._producer = Producer(config)
        self._running = True

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Producer connected to Kafka, starting produce loop")
        self._produce_loop()

    def _produce_loop(self) -> None:
        """Main produce loop — generates and sends log batches."""
        while self._running:
            try:
                # Generate a batch of log entries
                batch = self._generator.generate_batch(count=PRODUCER_BATCH_SIZE)
                BATCH_SIZE_HIST.observe(len(batch))

                # Produce each message in the batch
                for log_entry in batch:
                    self._produce_message(log_entry)

                # Trigger delivery callbacks
                self._producer.poll(0)

                self._total_produced += len(batch)
                PRODUCER_UPTIME.set(time.time() - self._start_time)

                if self._total_produced % 100 == 0:
                    logger.info(
                        f"Produced {self._total_produced} messages total"
                    )

                # Wait before next batch
                time.sleep(PRODUCER_INTERVAL_MS / 1000.0)

            except Exception as e:
                PRODUCE_ERRORS.inc()
                logger.error(f"Error in produce loop: {e}")
                time.sleep(1)  # Backoff on error

        self._shutdown()

    def _produce_message(self, log_entry: dict[str, Any]) -> None:
        """Produce a single message to Kafka."""
        try:
            value = json.dumps(log_entry, default=str).encode("utf-8")
            key = log_entry.get("service", "unknown").encode("utf-8")

            start = time.perf_counter()

            self._producer.produce(
                topic=KAFKA_TOPIC,
                value=value,
                key=key,
                callback=self._delivery_callback,
            )

            PRODUCE_LATENCY.observe(time.perf_counter() - start)

        except BufferError:
            logger.warning("Producer buffer full, flushing...")
            self._producer.flush(timeout=5)
            # Retry
            self._producer.produce(
                topic=KAFKA_TOPIC,
                value=value,
                key=key,
                callback=self._delivery_callback,
            )
        except Exception as e:
            PRODUCE_ERRORS.inc()
            logger.error(f"Failed to produce message: {e}")

    def _delivery_callback(
        self, err: KafkaError | None, msg: Any
    ) -> None:
        """Callback for message delivery confirmation."""
        if err is not None:
            PRODUCE_ERRORS.inc()
            logger.error(f"Message delivery failed: {err}")
        else:
            # Deserialize to get service and level for metrics
            try:
                data = json.loads(msg.value())
                MESSAGES_PRODUCED.labels(
                    topic=msg.topic(),
                    service=data.get("service", "unknown"),
                    level=data.get("level", "unknown"),
                ).inc()
            except Exception:
                MESSAGES_PRODUCED.labels(
                    topic=msg.topic(),
                    service="unknown",
                    level="unknown",
                ).inc()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._running = False

    def _shutdown(self) -> None:
        """Flush remaining messages and shut down."""
        if self._producer:
            logger.info("Flushing remaining messages...")
            remaining = self._producer.flush(timeout=30)
            if remaining > 0:
                logger.warning(f"Shutdown with {remaining} unflushed messages")
            else:
                logger.info("All messages flushed successfully")

        logger.info(
            f"Producer shutdown complete | "
            f"total_produced={self._total_produced} | "
            f"uptime={time.time() - self._start_time:.1f}s"
        )


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    producer = LogProducer()
    producer.start()
