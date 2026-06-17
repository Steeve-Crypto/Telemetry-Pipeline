"""Kafka ingestion source with offset management and replay support."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import structlog
from aiokafka import AIOKafkaConsumer

from telemetry.config import IngestionConfig, PipelineYamlConfig
from telemetry.ingestion.base import IngestionSource
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class KafkaIngestionSource(IngestionSource):
    def __init__(self, config: IngestionConfig, offset_reset: str = "latest") -> None:
        self._cfg = config.kafka
        self._offset_reset = offset_reset
        self._consumer: AIOKafkaConsumer | None = None
        self._commit_task: asyncio.Task | None = None

    @classmethod
    def from_pipeline(cls, pipeline_config: PipelineYamlConfig) -> KafkaIngestionSource:
        return cls(
            pipeline_config.ingestion,
            offset_reset=pipeline_config.kafka_offset_reset,
        )

    async def connect(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._cfg.topic,
            bootstrap_servers=self._cfg.bootstrap_servers,
            group_id=self._cfg.group_id,
            auto_offset_reset=self._offset_reset,
            enable_auto_commit=self._cfg.enable_auto_commit,
        )
        await self._consumer.start()

        if not self._cfg.enable_auto_commit:
            self._commit_task = asyncio.create_task(self._periodic_commit())

        logger.info(
            "kafka_connected",
            servers=self._cfg.bootstrap_servers,
            topic=self._cfg.topic,
            offset_reset=self._offset_reset,
            auto_commit=self._cfg.enable_auto_commit,
            replay_mode=self._cfg.replay_mode,
        )

    async def disconnect(self) -> None:
        if self._commit_task:
            self._commit_task.cancel()
            try:
                await self._commit_task
            except asyncio.CancelledError:
                pass
        if self._consumer is not None:
            if not self._cfg.enable_auto_commit:
                await self._consumer.commit()
                logger.info("kafka_offsets_committed")
            await self._consumer.stop()
            self._consumer = None

    async def _periodic_commit(self) -> None:
        while True:
            await asyncio.sleep(self._cfg.commit_interval_seconds)
            if self._consumer is not None:
                await self._consumer.commit()

    async def events(self) -> AsyncIterator[SensorEvent]:
        if self._consumer is None:
            raise RuntimeError("Kafka consumer not connected")
        async for msg in self._consumer:
            try:
                payload = json.loads(msg.value.decode())
                yield SensorEvent.model_validate(payload)
            except Exception as exc:
                logger.warning("kafka_parse_error", error=str(exc))