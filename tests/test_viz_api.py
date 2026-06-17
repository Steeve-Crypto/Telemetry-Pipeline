"""VizAPI and Prometheus endpoint tests."""

import pytest
from aiohttp.test_utils import TestClient, TestServer

from telemetry.config import PrometheusConfig
from telemetry.prometheus import PrometheusExporter
from telemetry.storage.timescale import MemoryStorage
from telemetry.viz.api import VizAPI


@pytest.fixture
async def viz_client():
    storage = MemoryStorage()
    await storage.connect()
    api = VizAPI(storage, PrometheusExporter(PrometheusConfig(namespace="telemetry_test")))
    api.set_pipeline_metrics({"events_ingested": 42, "processing_rate_eps": 100.0})
    server = TestServer(api.app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_health_endpoint(viz_client):
    resp = await viz_client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics_api_endpoint(viz_client):
    resp = await viz_client.get("/api/metrics")
    assert resp.status == 200
    data = await resp.json()
    assert data["events_ingested"] == 42


@pytest.mark.asyncio
async def test_prometheus_endpoint(viz_client):
    resp = await viz_client.get("/metrics")
    assert resp.status == 200
    body = await resp.text()
    assert "telemetry_test" in body