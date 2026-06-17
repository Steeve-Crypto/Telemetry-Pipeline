"""Lightweight HTTP API for dashboard data and Prometheus metrics."""

from __future__ import annotations

from aiohttp import web

from telemetry.config import VizConfig
from telemetry.prometheus import PrometheusExporter
from telemetry.storage.timescale import StorageBackend
from telemetry.viz.middleware import build_security_middleware


class VizAPI:
    def __init__(
        self,
        storage: StorageBackend,
        prometheus: PrometheusExporter | None = None,
        viz_config: VizConfig | None = None,
    ) -> None:
        self._storage = storage
        self._prometheus = prometheus
        self.app = web.Application(middlewares=[build_security_middleware(
            (viz_config or VizConfig()).security
        )])
        self.app.router.add_get("/health", self.health)
        self.app.router.add_get("/api/events", self.events)
        self.app.router.add_get("/api/anomalies", self.anomalies)
        self.app.router.add_get("/api/metrics", self.metrics)
        self.app.router.add_get("/metrics", self.prometheus_metrics)
        self._pipeline_metrics: dict = {}
        self._runner: web.AppRunner | None = None

    def set_pipeline_metrics(self, metrics: dict) -> None:
        self._pipeline_metrics = metrics

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def events(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "100")), 1000)
        events = await self._storage.recent_events(limit)
        payload = [e.model_dump(mode="json") for e in events]
        return web.json_response(payload)

    async def anomalies(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "50")), 500)
        anomalies = await self._storage.recent_anomalies(limit)
        payload = [a.model_dump(mode="json") for a in anomalies]
        return web.json_response(payload)

    async def metrics(self, _request: web.Request) -> web.Response:
        return web.json_response(self._pipeline_metrics)

    async def prometheus_metrics(self, _request: web.Request) -> web.Response:
        if self._prometheus is None:
            return web.Response(text="prometheus disabled", status=503)
        body, content_type = self._prometheus.render()
        return web.Response(body=body, content_type=content_type.split(";")[0])

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host, port)
        await site.start()
        return self._runner

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None