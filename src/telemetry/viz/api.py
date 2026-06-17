"""Lightweight HTTP API for dashboard data and Prometheus metrics."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web

from telemetry.config import TenancyConfig, VizConfig
from telemetry.prometheus import PrometheusExporter
from telemetry.storage.timescale import StorageBackend
from telemetry.ingestion.kafka_topics import known_tenant_ids
from telemetry.viz.middleware import TENANT_ID_KEY, build_security_middleware


class VizAPI:
    def __init__(
        self,
        storage: StorageBackend,
        prometheus: PrometheusExporter | None = None,
        viz_config: VizConfig | None = None,
        tenancy_config: TenancyConfig | None = None,
    ) -> None:
        viz = viz_config or VizConfig()
        self._storage = storage
        self._prometheus = prometheus
        self._tenancy = tenancy_config or TenancyConfig()
        self.app = web.Application(middlewares=[
            build_security_middleware(viz.security, self._tenancy)
        ])
        self.app.router.add_get("/health", self.health)
        self.app.router.add_get("/api/config", self.config)
        self.app.router.add_get("/api/devices", self.devices)
        self.app.router.add_get("/api/events", self.events)
        self.app.router.add_get("/api/anomalies", self.anomalies)
        self.app.router.add_get("/api/window-stats", self.window_stats)
        self.app.router.add_get("/api/metrics", self.metrics)
        self.app.router.add_get("/api/stream", self.stream)
        self.app.router.add_get("/metrics", self.prometheus_metrics)
        self._pipeline_metrics: dict = {}
        self._runner: web.AppRunner | None = None

    def set_pipeline_metrics(self, metrics: dict) -> None:
        self._pipeline_metrics = metrics

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    def _tenant_filter(self, request: web.Request) -> str | None:
        if not self._tenancy.enabled:
            return None
        return request.get(TENANT_ID_KEY) or self._tenancy.default_tenant

    async def config(self, _request: web.Request) -> web.Response:
        tenants = known_tenant_ids(self._tenancy) if self._tenancy.enabled else []
        if self._tenancy.enabled and self._tenancy.default_tenant not in tenants:
            tenants = [self._tenancy.default_tenant, *tenants]
        return web.json_response(
            {
                "tenancy": {
                    "enabled": self._tenancy.enabled,
                    "default_tenant": self._tenancy.default_tenant,
                    "tenants": tenants,
                }
            }
        )

    async def devices(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "200")), 500)
        devices = await self._storage.list_devices(
            tenant_id=self._tenant_filter(request),
            limit=limit,
        )
        return web.json_response([d.model_dump(mode="json") for d in devices])

    async def events(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "100")), 1000)
        device_id = request.query.get("device_id")
        events = await self._storage.recent_events(
            limit,
            tenant_id=self._tenant_filter(request),
            device_id=device_id,
        )
        payload = [e.model_dump(mode="json") for e in events]
        return web.json_response(payload)

    async def anomalies(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "50")), 500)
        device_id = request.query.get("device_id")
        anomalies = await self._storage.recent_anomalies(
            limit,
            tenant_id=self._tenant_filter(request),
            device_id=device_id,
        )
        payload = [a.model_dump(mode="json") for a in anomalies]
        return web.json_response(payload)

    async def window_stats(self, request: web.Request) -> web.Response:
        limit = min(int(request.query.get("limit", "100")), 500)
        device_id = request.query.get("device_id")
        stats = await self._storage.recent_window_stats(
            limit,
            tenant_id=self._tenant_filter(request),
            device_id=device_id,
        )
        return web.json_response([s.model_dump(mode="json") for s in stats])

    async def metrics(self, _request: web.Request) -> web.Response:
        return web.json_response(self._pipeline_metrics)

    async def _dashboard_snapshot(self, request: web.Request) -> dict:
        tenant_id = self._tenant_filter(request)
        events = await self._storage.recent_events(
            200,
            tenant_id=tenant_id,
        )
        anomalies = await self._storage.recent_anomalies(
            50,
            tenant_id=tenant_id,
        )
        return {
            "metrics": self._pipeline_metrics,
            "events": [event.model_dump(mode="json") for event in events],
            "anomalies": [anomaly.model_dump(mode="json") for anomaly in anomalies],
        }

    async def stream(self, request: web.Request) -> web.StreamResponse:
        interval = max(
            float(request.query.get("interval", "1.5")),
            0.5,
        )
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        try:
            while True:
                if request.transport is not None and request.transport.is_closing():
                    break

                payload = json.dumps(await self._dashboard_snapshot(request))
                await response.write(f"data: {payload}\n\n".encode())

                if await request.is_disconnected():
                    break

                await asyncio.sleep(interval)
        except (asyncio.CancelledError, ConnectionResetError):
            pass

        return response

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