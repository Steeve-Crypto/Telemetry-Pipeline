"""Kafka topic provisioning for per-tenant partitioning."""

from __future__ import annotations

import structlog

from telemetry.config import KafkaConfig, TenancyConfig
from telemetry.ingestion.kafka_topics import consumer_topics

logger = structlog.get_logger(__name__)


async def ensure_kafka_topics(kafka: KafkaConfig, tenancy: TenancyConfig) -> list[str]:
    """Create missing Kafka topics required by the current config."""
    topics = consumer_topics(kafka, tenancy)
    if not kafka.auto_create_topics:
        return topics

    try:
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    except ImportError:
        logger.warning("aiokafka_admin_unavailable", hint="upgrade aiokafka")
        return topics

    admin = AIOKafkaAdminClient(bootstrap_servers=kafka.bootstrap_servers)
    await admin.start()
    try:
        existing = set(await admin.list_topics())
        to_create = [
            NewTopic(
                name=topic,
                num_partitions=kafka.partitions_per_topic,
                replication_factor=kafka.replication_factor,
            )
            for topic in topics
            if topic not in existing
        ]
        if to_create:
            await admin.create_topics(to_create)
            logger.info(
                "kafka_topics_created",
                topics=[topic.name for topic in to_create],
                partitions=kafka.partitions_per_topic,
            )
    except Exception as exc:
        logger.warning("kafka_topic_create_failed", error=str(exc))
    finally:
        await admin.stop()

    return topics