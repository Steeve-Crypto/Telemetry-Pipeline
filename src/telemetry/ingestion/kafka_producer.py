"""Kafka producer with optional per-tenant topic routing."""

from __future__ import annotations

import json

import structlog
from aiokafka import AIOKafkaProducer

from telemetry.config import KafkaConfig, TenancyConfig
from telemetry.ingestion.kafka_admin import ensure_kafka_topics
from telemetry.ingestion.kafka_topics import is_topic_per_tenant, topic_for_tenant
from telemetry.models import SensorEvent
from telemetry.tenancy import resolve_event_tenant

logger = structlog.get_logger(__name__)


class KafkaEventProducer:
    def __init__(
        self,
        config: KafkaConfig,
        tenancy: TenancyConfig | None = None,
    ) -> None:
        self._cfg = config
        self._tenancy = tenancy or TenancyConfig()
        self._producer: AIOKafkaProducer | None = None
        self._topics: list[str] = []

    async def connect(self) -> None:
        self._topics = await ensure_kafka_topics(self._cfg, self._tenancy)
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._cfg.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()
        logger.info(
            "kafka_producer_connected",
            servers=self._cfg.bootstrap_servers,
            topics=self._topics,
            topic_per_tenant=is_topic_per_tenant(self._cfg, self._tenancy),
        )

    async def disconnect(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    def resolve_topic(self, event: SensorEvent) -> str:
        if not is_topic_per_tenant(self._cfg, self._tenancy):
            return self._cfg.topic
        tenant_id = resolve_event_tenant(event, self._tenancy)
        return topic_for_tenant(tenant_id, self._cfg)

    async def publish(self, event: SensorEvent) -> str:
        if self._producer is None:
            raise RuntimeError("Kafka producer not connected")
        topic = self.resolve_topic(event)
        payload = json.loads(event.model_dump_json())
        await self._producer.send_and_wait(topic, payload)
        return topic