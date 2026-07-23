"""
Kafka log consumer — standalone service.

Consumes log entries from Kafka, validates and processes them,
and stores them in PostgreSQL. Handles offset management,
batch processing, dead letter queuing, and graceful shutdown.
Exposes Prometheus metrics for monitoring.
"""

import json
import os
import sys
import time
import signal
import logging
from typing import Any

from confluent_kafka import (
    Consumer,
    Producer,
    KafkaError,
    KafkaException,
    TopicPartition,
)
from prometheus_client import (
    Counter, Histogram, Gauge, start_http_server,
)

from consumer.processor import LogProcessor
from consumer.database import DatabaseManager

# =============================================================================
# Configuration
# =============================================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_LOGS", "service-logs")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "log-consumer-group")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_TOPIC_DLQ", "dead-letter-logs")
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
CONSUMER_BATCH_SIZE = int(os.getenv("CONSUMER_BATCH_SIZE", "50"))
CONSUMER_POLL_TIMEOUT_MS = int(os.getenv("CONSUMER_POLL_TIMEOUT_MS", "1000"))
CONSUMER_METRICS_PORT = int(os.getenv("CONSUMER_METRICS_PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("consumer")

# =============================================================================
# Prometheus Metrics
# =============================================================================

MESSAGES_CONSUMED = Counter(
    "consumer_messages_consumed_total",
    "Total messages consumed from Kafka",
    ["topic"],
)

MESSAGES_STORED = Counter(
    "consumer_messages_stored_total",
    "Total messages stored in database",
)

MESSAGES_DLQ = Counter(
    "consumer_messages_dlq_total",
    "Total messages sent to dead letter queue",
)

CONSUMER_LAG = Gauge(
    "consumer_lag",
    "Consumer lag (messages behind)",
    ["topic", "partition"],
)

BATCH_PROCESSING_TIME = Histogram(
    "consumer_batch_processing_seconds",
    "Time to process a batch of messages",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

CONSUMER_UPTIME = Gauge(
    "consumer_uptime_seconds",
    "Consumer uptime in seconds",
)

CONSUMER_STATUS = Gauge(
    "consumer_status",
    "Consumer running status (1=running, 0=stopped)",
)


class LogConsumer:
    """
    Kafka consumer that reads log entries, processes them,
    and stores them in PostgreSQL.

    Features:
    - Manual offset commits (after successful DB write)
    - Batch processing for throughput
    - Dead letter queue for unprocessable messages
    - Graceful shutdown with final offset commit
    - Prometheus metrics
    """

    def __init__(self) -> None:
        self._running = False
        self._consumer: Consumer | None = None
        self._dlq_producer: Producer | None = None
        self._processor = LogProcessor()
        self._db = DatabaseManager()
        self._start_time = time.time()
        self._total_consumed = 0
        self._total_stored = 0

    def start(self) -> None:
        """Initialize and start the consumer loop."""
        logger.info(
            f"Starting consumer | bootstrap={KAFKA_BOOTSTRAP_SERVERS} | "
            f"topic={KAFKA_TOPIC} | group={KAFKA_GROUP_ID} | "
            f"batch_size={CONSUMER_BATCH_SIZE}"
        )

        # Start Prometheus metrics server
        start_http_server(CONSUMER_METRICS_PORT)
        logger.info(f"Prometheus metrics exposed on port {CONSUMER_METRICS_PORT}")

        # Initialize Kafka consumer
        consumer_config = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": KAFKA_GROUP_ID,
            "auto.offset.reset": KAFKA_AUTO_OFFSET_RESET,
            "enable.auto.commit": False,  # Manual commits
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 30000,
            "heartbeat.interval.ms": 10000,
            "fetch.min.bytes": 1,
            "fetch.max.wait.ms": 500,
        }

        self._consumer = Consumer(consumer_config)
        self._consumer.subscribe(
            [KAFKA_TOPIC],
            on_assign=self._on_assign,
            on_revoke=self._on_revoke,
        )

        # Initialize DLQ producer
        self._dlq_producer = Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "consumer-dlq-producer",
        })

        self._running = True
        CONSUMER_STATUS.set(1)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Consumer started, entering consume loop")
        self._consume_loop()

    def _consume_loop(self) -> None:
        """Main consume loop — polls Kafka and processes messages."""
        while self._running:
            try:
                batch: list[Any] = []

                # Poll for messages up to batch size
                while len(batch) < CONSUMER_BATCH_SIZE:
                    msg = self._consumer.poll(
                        timeout=CONSUMER_POLL_TIMEOUT_MS / 1000.0
                    )
                    if msg is None:
                        break
                    if msg.error():
                        self._handle_kafka_error(msg.error())
                        continue
                    batch.append(msg)

                if not batch:
                    CONSUMER_UPTIME.set(time.time() - self._start_time)
                    continue

                # Process the batch
                start = time.perf_counter()
                self._process_batch(batch)
                duration = time.perf_counter() - start

                BATCH_PROCESSING_TIME.observe(duration)
                CONSUMER_UPTIME.set(time.time() - self._start_time)

                # Commit offsets after successful processing
                self._consumer.commit(asynchronous=False)

                self._total_consumed += len(batch)
                MESSAGES_CONSUMED.labels(topic=KAFKA_TOPIC).inc(len(batch))

                if self._total_consumed % 100 == 0:
                    logger.info(
                        f"Consumed {self._total_consumed} messages | "
                        f"Stored {self._total_stored} | "
                        f"Batch processed in {duration:.3f}s"
                    )

            except KafkaException as e:
                logger.error(f"Kafka error in consume loop: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error in consume loop: {e}")
                time.sleep(1)

        self._shutdown()

    def _process_batch(self, messages: list[Any]) -> None:
        """
        Process a batch of Kafka messages.

        1. Deserialize and validate each message
        2. Batch insert valid entries into PostgreSQL
        3. Send invalid entries to the dead letter queue
        """
        raw_values = []
        dlq_messages = []

        for msg in messages:
            try:
                raw_values.append(msg.value())
            except Exception as e:
                logger.warning(f"Failed to read message value: {e}")

        # Process through the LogProcessor
        valid_entries = self._processor.process_batch(raw_values)

        # Identify failed messages for DLQ
        valid_count = len(valid_entries)
        failed_count = len(raw_values) - valid_count

        # Store valid entries in PostgreSQL
        if valid_entries:
            stored = self._db.insert_batch(valid_entries)
            self._total_stored += stored
            MESSAGES_STORED.inc(stored)

        # Send failed messages to dead letter queue
        if failed_count > 0:
            for raw in raw_values:
                try:
                    parsed = json.loads(raw)
                    if not self._processor._validate(parsed):
                        self._send_to_dlq(raw)
                except Exception:
                    self._send_to_dlq(raw)

    def _send_to_dlq(self, raw_message: bytes) -> None:
        """Send a failed message to the dead letter queue topic."""
        try:
            self._dlq_producer.produce(
                topic=KAFKA_DLQ_TOPIC,
                value=raw_message,
            )
            self._dlq_producer.poll(0)
            MESSAGES_DLQ.inc()
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")

    def _handle_kafka_error(self, error: KafkaError) -> None:
        """Handle Kafka-specific errors."""
        if error.code() == KafkaError._PARTITION_EOF:
            # End of partition — not an error
            logger.debug("Reached end of partition")
        elif error.code() == KafkaError._ALL_BROKERS_DOWN:
            logger.critical("All Kafka brokers are down!")
            time.sleep(5)
        else:
            logger.error(f"Kafka error: {error}")

    def _on_assign(self, consumer: Consumer, partitions: list) -> None:
        """Callback when partitions are assigned to this consumer."""
        logger.info(
            f"Partitions assigned: "
            f"{[(p.topic, p.partition) for p in partitions]}"
        )

    def _on_revoke(self, consumer: Consumer, partitions: list) -> None:
        """Callback when partitions are revoked from this consumer."""
        logger.info(
            f"Partitions revoked: "
            f"{[(p.topic, p.partition) for p in partitions]}"
        )
        # Commit current offsets before rebalance
        try:
            consumer.commit(asynchronous=False)
        except Exception as e:
            logger.warning(f"Failed to commit offsets on revoke: {e}")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._running = False

    def _shutdown(self) -> None:
        """Clean shutdown: commit offsets, close connections."""
        CONSUMER_STATUS.set(0)

        # Final offset commit
        if self._consumer:
            try:
                self._consumer.commit(asynchronous=False)
                logger.info("Final offsets committed")
            except Exception as e:
                logger.warning(f"Failed to commit final offsets: {e}")
            self._consumer.close()
            logger.info("Consumer closed")

        # Flush DLQ producer
        if self._dlq_producer:
            self._dlq_producer.flush(timeout=10)

        # Close database
        self._db.close()

        logger.info(
            f"Consumer shutdown complete | "
            f"total_consumed={self._total_consumed} | "
            f"total_stored={self._total_stored} | "
            f"uptime={time.time() - self._start_time:.1f}s"
        )


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    consumer = LogConsumer()
    consumer.start()
