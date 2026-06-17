"""Base ingestion interface and factory."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from telemetry.config import IngestionConfig, PipelineYamlConfig
from telemetry.models import SensorEvent


class IngestionSource(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def events(self) -> AsyncIterator[SensorEvent]: ...

    @staticmethod
    def parse_payload(payload: str | bytes | dict[str, Any]) -> SensorEvent:
        if isinstance(payload, (str, bytes)):
            data = json.loads(payload)
        else:
            data = payload
        return SensorEvent.model_validate(data)


class MemoryIngestionSource(IngestionSource):
    """In-process queue for tests and embedded pipeline runs."""

    def __init__(self, queue: Any) -> None:
        self._queue = queue
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def events(self) -> AsyncIterator[SensorEvent]:
        while self._connected:
            item = await self._queue.get()
            if item is None:
                break
            yield item


def create_ingestion_source(
    config: PipelineYamlConfig,
    memory_queue: Any | None = None,
) -> IngestionSource:
    transport = config.ingestion.transport
    if memory_queue is not None:
        return MemoryIngestionSource(memory_queue)

    if transport == "mqtt":
        from telemetry.ingestion.mqtt import MqttIngestionSource

        return MqttIngestionSource(config.ingestion)
    if transport == "kafka":
        from telemetry.ingestion.kafka_consumer import KafkaIngestionSource

        return KafkaIngestionSource(config.ingestion)
    if transport == "websocket":
        from telemetry.ingestion.websocket import WebSocketIngestionSource

        return WebSocketIngestionSource(config.ingestion)

    raise ValueError(f"Unknown ingestion transport: {transport}")