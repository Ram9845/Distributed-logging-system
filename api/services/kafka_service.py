"""
Kafka producer service.

Wraps the confluent-kafka producer with batching, compression,
retry logic, and Prometheus metrics. Provides an async-friendly
interface for the FastAPI application.
"""

import json
import asyncio
from typing import Any
from confluent_kafka import Producer, KafkaError, KafkaException
from prometheus_client import Counter, Histogram, Gauge
import structlog

from api.config import Settings

logger = structlog.get_logger(__name__)

# =============================================================================
# Prometheus Metrics for Kafka Producer
# =============================================================================

KAFKA_MESSAGES_PRODUCED = Counter(
    "kafka_messages_produced_total",
    "Total messages produced to Kafka",
    ["topic", "status"],
)

KAFKA_PRODUCE_LATENCY = Histogram(
    "kafka_produce_latency_seconds",
    "Time taken to produce a message to Kafka",
    ["topic"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

KAFKA_PRODUCER_QUEUE_SIZE = Gauge(
    "kafka_producer_queue_size",
    "Current number of messages in the producer queue",
)

KAFKA_PRODUCE_ERRORS = Counter(
    "kafka_produce_errors_total",
    "Total Kafka produce errors",
    ["topic", "error_type"],
)


class KafkaService:
    """
    Kafka producer service with batching, compression, and retries.

    Manages the lifecycle of a confluent-kafka Producer instance,
    providing methods to send single messages or batches to topics.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: Producer | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize the Kafka producer with optimized settings."""
        try:
            config = {
                "bootstrap.servers": self._settings.kafka_bootstrap_servers,
                "client.id": "fastapi-log-producer",
                "acks": "all",
                # Batching for throughput
                "batch.size": self._settings.kafka_batch_size,
                "linger.ms": self._settings.kafka_linger_ms,
                # Compression
                "compression.type": self._settings.kafka_compression_type,
                # Retries
                "retries": self._settings.kafka_max_retries,
                "retry.backoff.ms": 100,
                # Idempotence for exactly-once semantics
                "enable.idempotence": True,
                # Buffer memory
                "queue.buffering.max.messages": 100000,
                "queue.buffering.max.kbytes": 1048576,  # 1 GB
            }

            self._producer = Producer(config)
            self._running = True
            logger.info(
                "Kafka producer started",
                bootstrap_servers=self._settings.kafka_bootstrap_servers,
            )
        except KafkaException as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise

    async def stop(self) -> None:
        """Flush pending messages and shut down the producer."""
        if self._producer is not None:
            self._running = False
            # Flush remaining messages (wait up to 10 seconds)
            remaining = self._producer.flush(timeout=10)
            if remaining > 0:
                logger.warning(
                    "Kafka producer shutdown with unflushed messages",
                    remaining=remaining,
                )
            self._producer = None
            logger.info("Kafka producer stopped")

    def _delivery_callback(self, err: KafkaError | None, msg: Any) -> None:
        """Callback invoked on message delivery (success or failure)."""
        topic = msg.topic() if msg else "unknown"
        if err is not None:
            KAFKA_MESSAGES_PRODUCED.labels(topic=topic, status="error").inc()
            KAFKA_PRODUCE_ERRORS.labels(
                topic=topic, error_type=str(err.code())
            ).inc()
            logger.error(
                "Kafka message delivery failed",
                topic=topic,
                error=str(err),
            )
        else:
            KAFKA_MESSAGES_PRODUCED.labels(topic=topic, status="success").inc()

    async def produce(
        self,
        topic: str,
        value: dict[str, Any],
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Produce a single message to a Kafka topic.

        Args:
            topic: Kafka topic name.
            value: Message payload (will be JSON-serialized).
            key: Optional partition key.
            headers: Optional message headers.
        """
        if not self._producer or not self._running:
            logger.warning("Kafka producer not running, message dropped")
            return

        try:
            serialized_value = json.dumps(value, default=str).encode("utf-8")
            serialized_key = key.encode("utf-8") if key else None

            kafka_headers = None
            if headers:
                kafka_headers = [
                    (k, v.encode("utf-8")) for k, v in headers.items()
                ]

            with KAFKA_PRODUCE_LATENCY.labels(topic=topic).time():
                self._producer.produce(
                    topic=topic,
                    value=serialized_value,
                    key=serialized_key,
                    headers=kafka_headers,
                    callback=self._delivery_callback,
                )

            # Trigger delivery callbacks without blocking
            self._producer.poll(0)

            # Update queue size metric
            queue_size = len(self._producer)
            KAFKA_PRODUCER_QUEUE_SIZE.set(queue_size)

        except BufferError:
            logger.warning("Kafka producer buffer full, flushing...")
            await asyncio.to_thread(self._producer.flush, 5)
            # Retry once after flush
            self._producer.produce(
                topic=topic,
                value=serialized_value,
                key=serialized_key,
                callback=self._delivery_callback,
            )
        except KafkaException as e:
            KAFKA_PRODUCE_ERRORS.labels(
                topic=topic, error_type="produce_exception"
            ).inc()
            logger.error("Kafka produce error", topic=topic, error=str(e))
            raise

    async def produce_batch(
        self,
        topic: str,
        messages: list[dict[str, Any]],
        key_field: str | None = "service",
    ) -> int:
        """
        Produce a batch of messages to a Kafka topic.

        Args:
            topic: Kafka topic name.
            messages: List of message payloads.
            key_field: Field in each message to use as partition key.

        Returns:
            Number of messages successfully queued.
        """
        produced = 0
        for msg in messages:
            key = msg.get(key_field) if key_field else None
            try:
                await self.produce(topic, msg, key=key)
                produced += 1
            except Exception as e:
                logger.error(
                    "Failed to produce message in batch",
                    error=str(e),
                    message_index=produced,
                )

        # Flush the batch
        if self._producer:
            await asyncio.to_thread(self._producer.flush, 10)

        logger.info(
            "Batch produce completed",
            topic=topic,
            total=len(messages),
            produced=produced,
        )
        return produced

    async def health_check(self) -> bool:
        """Check if the Kafka producer is connected and operational."""
        if not self._producer or not self._running:
            return False
        try:
            # List topics to verify connectivity
            metadata = await asyncio.to_thread(
                self._producer.list_topics, timeout=5
            )
            return metadata is not None
        except Exception:
            return False
