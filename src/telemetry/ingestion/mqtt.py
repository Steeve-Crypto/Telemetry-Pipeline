"""MQTT ingestion source."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import structlog

from telemetry.config import IngestionConfig
from telemetry.ingestion.base import IngestionSource
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class MqttIngestionSource(IngestionSource):
    def __init__(self, config: IngestionConfig) -> None:
        self._cfg = config.mqtt
        self._client = None
        self._queue: asyncio.Queue[SensorEvent | None] = asyncio.Queue()
        self._connected = False

    async def connect(self) -> None:
        try:
            import aiomqtt
        except ImportError as exc:
            raise RuntimeError("aiomqtt is required for MQTT ingestion") from exc

        self._client = aiomqtt.Client(hostname=self._cfg.host, port=self._cfg.port)
        await self._client.__aenter__()
        self._connected = True
        asyncio.create_task(self._consume())
        logger.info("mqtt_connected", host=self._cfg.host, topic=self._cfg.topic)

    async def disconnect(self) -> None:
        self._connected = False
        await self._queue.put(None)
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def _consume(self) -> None:
        assert self._client is not None
        async with self._client.messages() as messages:
            await self._client.subscribe(self._cfg.topic, qos=self._cfg.qos)
            async for message in messages:
                if not self._connected:
                    break
                try:
                    payload = json.loads(message.payload.decode())
                    event = SensorEvent.model_validate(payload)
                    await self._queue.put(event)
                except Exception as exc:
                    logger.warning("mqtt_parse_error", error=str(exc))

    async def events(self) -> AsyncIterator[SensorEvent]:
        while self._connected or not self._queue.empty():
            event = await self._queue.get()
            if event is None:
                break
            yield event