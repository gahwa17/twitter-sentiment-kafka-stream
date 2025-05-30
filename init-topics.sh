#!/bin/bash

set -e

# Topic 名稱與設定
TOPIC_NAME="tweets_raw"
PARTITIONS=3
REPLICATION_FACTOR=3
BROKER="kafka1:9092"

echo "Creating topic [$TOPIC_NAME] with $PARTITIONS partitions and $REPLICATION_FACTOR replication factor..."

docker-compose exec kafka1 kafka-topics \
  --create \
  --if-not-exists \
  --topic "$TOPIC_NAME" \
  --bootstrap-server "$BROKER" \
  --replication-factor "$REPLICATION_FACTOR" \
  --partitions "$PARTITIONS"

echo "✅ Topic [$TOPIC_NAME] created (if not exists)."
