"""Kafka ingestion source."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import structlog
from aiokafka import AIOKafkaConsumer

from telemetry.config import IngestionConfig
from telemetry.ingestion.base import IngestionSource
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class KafkaIngestionSource(IngestionSource):
    def __init__(self, config: IngestionConfig) -> None:
        self._cfg = config.kafka
        self._consumer: AIOKafkaConsumer | None = None

    async def connect(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._cfg.topic,
            bootstrap_servers=self._cfg.bootstrap_servers,
            group_id=self._cfg.group_id,
            auto_offset_reset=self._cfg.auto_offset_reset,
            enable_auto_commit=True,
        )
        await self._consumer.start()
        logger.info(
            "kafka_connected",
            servers=self._cfg.bootstrap_servers,
            topic=self._cfg.topic,
        )

    async def disconnect(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def events(self) -> AsyncIterator[SensorEvent]:
        if self._consumer is None:
            raise RuntimeError("Kafka consumer not connected")
        async for msg in self._consumer:
            try:
                payload = json.loads(msg.value.decode())
                yield SensorEvent.model_validate(payload)
            except Exception as exc:
                logger.warning("kafka_parse_error", error=str(exc))