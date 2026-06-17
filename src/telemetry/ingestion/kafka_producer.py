"""Kafka producer for simulator and replay tools."""

from __future__ import annotations

import json

import structlog
from aiokafka import AIOKafkaProducer

from telemetry.config import KafkaConfig
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class KafkaEventProducer:
    def __init__(self, config: KafkaConfig) -> None:
        self._cfg = config
        self._producer: AIOKafkaProducer | None = None

    async def connect(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._cfg.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()
        logger.info(
            "kafka_producer_connected",
            servers=self._cfg.bootstrap_servers,
            topic=self._cfg.topic,
        )

    async def disconnect(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, event: SensorEvent) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer not connected")
        payload = json.loads(event.model_dump_json())
        await self._producer.send_and_wait(self._cfg.topic, payload)