"""Kafka topic naming and tenant partitioning helpers."""

from __future__ import annotations

import structlog

from telemetry.config import KafkaConfig, TenancyConfig

logger = structlog.get_logger(__name__)


def is_topic_per_tenant(kafka: KafkaConfig, tenancy: TenancyConfig) -> bool:
    return kafka.topic_per_tenant and tenancy.enabled


def known_tenant_ids(tenancy: TenancyConfig) -> list[str]:
    tenants = set(tenancy.tenant_api_keys.keys())
    tenants.add(tenancy.default_tenant)
    return sorted(tenants)


def topic_for_tenant(tenant_id: str, kafka: KafkaConfig) -> str:
    if tenant_id in kafka.tenant_topics:
        return kafka.tenant_topics[tenant_id]
    if "{tenant_id}" in kafka.topic_template:
        return kafka.topic_template.format(tenant_id=tenant_id)
    return kafka.topic


def consumer_topics(kafka: KafkaConfig, tenancy: TenancyConfig) -> list[str]:
    if not is_topic_per_tenant(kafka, tenancy):
        return [kafka.topic]

    tenant_ids = set(known_tenant_ids(tenancy))
    tenant_ids.update(kafka.tenant_topics.keys())
    return sorted({topic_for_tenant(tenant_id, kafka) for tenant_id in tenant_ids})


def parse_tenant_from_topic(topic: str, kafka: KafkaConfig) -> str | None:
    if "{tenant_id}" not in kafka.topic_template:
        return None
    prefix, suffix = kafka.topic_template.split("{tenant_id}", 1)
    if not topic.startswith(prefix):
        return None
    remainder = topic[len(prefix) :]
    if suffix:
        if not remainder.endswith(suffix):
            return None
        remainder = remainder[: -len(suffix)]
    return remainder or None


def stamp_event_tenant(event: object, topic: str, kafka: KafkaConfig) -> object:
    """Ensure tenant_id is set from the Kafka topic when using per-tenant topics."""
    from telemetry.models import SensorEvent

    if not isinstance(event, SensorEvent):
        return event

    topic_tenant = parse_tenant_from_topic(topic, kafka)
    if not topic_tenant:
        return event

    if event.tenant_id and event.tenant_id != topic_tenant:
        logger.warning(
            "kafka_tenant_topic_mismatch",
            event_tenant=event.tenant_id,
            topic_tenant=topic_tenant,
            topic=topic,
        )
        return event

    if event.tenant_id:
        return event

    tags = {**event.tags, "tenant_id": topic_tenant}
    return event.model_copy(update={"tenant_id": topic_tenant, "tags": tags})