#!/bin/bash
# =============================================================================
# Kafka Topic Creation Script
# =============================================================================
# Creates all required Kafka topics for the logging system.
# Run after Kafka broker is healthy.
# =============================================================================

set -e

KAFKA_BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"

echo "============================================"
echo "  Creating Kafka Topics"
echo "============================================"
echo "Bootstrap server: ${KAFKA_BOOTSTRAP_SERVER}"
echo ""

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while ! kafka-broker-api-versions --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]; then
        echo "ERROR: Kafka not ready after ${MAX_RETRIES} retries. Exiting."
        exit 1
    fi
    echo "  Attempt ${RETRY_COUNT}/${MAX_RETRIES} — waiting 2s..."
    sleep 2
done

echo "Kafka is ready!"
echo ""

# ---- Create Topics ----

echo "Creating topic: service-logs (3 partitions)"
kafka-topics --create \
    --if-not-exists \
    --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=604800000 \
    --config cleanup.policy=delete \
    --config max.message.bytes=1048576 \
    --topic service-logs

echo "Creating topic: alerts (1 partition)"
kafka-topics --create \
    --if-not-exists \
    --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=604800000 \
    --topic alerts

echo "Creating topic: dead-letter-logs (1 partition)"
kafka-topics --create \
    --if-not-exists \
    --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=2592000000 \
    --topic dead-letter-logs

echo ""
echo "============================================"
echo "  Topics Created Successfully"
echo "============================================"
echo ""

kafka-topics --list --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}"

echo ""
echo "Topic details:"
kafka-topics --describe --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}"
