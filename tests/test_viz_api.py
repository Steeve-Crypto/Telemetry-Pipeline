"""VizAPI and Prometheus endpoint tests."""

from datetime import datetime, timezone

import pytest
from aiohttp.test_utils import TestClient, TestServer

from telemetry.config import PrometheusConfig, TenancyConfig
from telemetry.models import AnomalyScore, EnrichedEvent, Severity
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


@pytest.mark.asyncio
async def test_config_endpoint():
    storage = MemoryStorage()
    await storage.connect()
    tenancy = TenancyConfig(enabled=True, default_tenant="default", tenant_api_keys={"acme": "k"})
    api = VizAPI(storage, tenancy_config=tenancy)
    server = TestServer(api.app)
    client = TestClient(server)
    await client.start_server()

    resp = await client.get("/api/config")
    assert resp.status == 200
    data = await resp.json()
    assert data["tenancy"]["enabled"] is True
    assert "acme" in data["tenancy"]["tenants"]

    await client.close()


@pytest.mark.asyncio
async def test_devices_and_filtered_events():
    storage = MemoryStorage()
    await storage.connect()
    now = datetime.now(timezone.utc)
    await storage.write_event(
        EnrichedEvent(
            device_id="industrial-device-001",
            sensor_type="industrial",
            timestamp=now,
            metrics={"temperature": 70.0},
            tenant_id="default",
        )
    )
    await storage.write_anomaly(
        AnomalyScore(
            device_id="industrial-device-001",
            sensor_type="industrial",
            timestamp=now,
            score=0.9,
            is_anomaly=True,
            severity=Severity.HIGH,
            message="test anomaly",
        )
    )

    api = VizAPI(storage)
    server = TestServer(api.app)
    client = TestClient(server)
    await client.start_server()

    devices = await (await client.get("/api/devices")).json()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "industrial-device-001"

    events = await (await client.get("/api/events?device_id=industrial-device-001")).json()
    assert len(events) == 1

    anomalies = await (
        await client.get("/api/anomalies?device_id=industrial-device-001")
    ).json()
    assert len(anomalies) == 1

    await client.close()