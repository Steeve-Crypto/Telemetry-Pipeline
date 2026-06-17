"""WebSocket ingestion server."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import structlog
import websockets
from websockets.server import WebSocketServerProtocol

from telemetry.config import IngestionConfig
from telemetry.ingestion.base import IngestionSource
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class WebSocketIngestionSource(IngestionSource):
    def __init__(self, config: IngestionConfig) -> None:
        self._cfg = config.websocket
        self._queue: asyncio.Queue[SensorEvent | None] = asyncio.Queue()
        self._server = None
        self._connected = False

    async def connect(self) -> None:
        self._connected = True
        self._server = await websockets.serve(
            self._handler,
            self._cfg.host,
            self._cfg.port,
        )
        logger.info("websocket_listening", host=self._cfg.host, port=self._cfg.port)

    async def disconnect(self) -> None:
        self._connected = False
        await self._queue.put(None)
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        async for message in websocket:
            try:
                payload = json.loads(message)
                event = SensorEvent.model_validate(payload)
                await self._queue.put(event)
            except Exception as exc:
                logger.warning("websocket_parse_error", error=str(exc))
                await websocket.send(json.dumps({"error": str(exc)}))

    async def events(self) -> AsyncIterator[SensorEvent]:
        while self._connected or not self._queue.empty():
            event = await self._queue.get()
            if event is None:
                break
            yield event