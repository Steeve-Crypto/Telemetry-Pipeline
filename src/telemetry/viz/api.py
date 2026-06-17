"""Lightweight HTTP API for dashboard data."""

from __future__ import annotations

import json
from aiohttp import web

from telemetry.storage.timescale import MemoryStorage, StorageBackend


class VizAPI:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self.app = web.Application()
        self.app.router.add_get("/health", self.health)
        self.app.router.add_get("/api/events", self.events)
        self.app.router.add_get("/api/anomalies", self.anomalies)
        self.app.router.add_get("/api/metrics", self.metrics)
        self._pipeline_metrics: dict = {}

    def set_pipeline_metrics(self, metrics: dict) -> None:
        self._pipeline_metrics = metrics

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def events(self, request: web.Request) -> web.Response:
        limit = int(request.query.get("limit", "100"))
        events = await self._storage.recent_events(limit)
        payload = [e.model_dump(mode="json") for e in events]
        return web.json_response(payload)

    async def anomalies(self, request: web.Request) -> web.Response:
        limit = int(request.query.get("limit", "50"))
        anomalies = await self._storage.recent_anomalies(limit)
        payload = [a.model_dump(mode="json") for a in anomalies]
        return web.json_response(payload)

    async def metrics(self, _request: web.Request) -> web.Response:
        return web.json_response(self._pipeline_metrics)

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        return runner