"""Multi-tenancy tests."""

from datetime import datetime, timezone

import pytest
from aiohttp.test_utils import TestClient, TestServer

from telemetry.config import ApiSecurityConfig, TenancyConfig, VizConfig
from telemetry.models import EnrichedEvent
from telemetry.storage.timescale import MemoryStorage
from telemetry.tenancy import resolve_event_tenant
from telemetry.validation.enricher import EventEnricher
from telemetry.viz.api import VizAPI


@pytest.mark.asyncio
async def test_enricher_sets_tenant_from_tags(sensors_config):
    tenancy = TenancyConfig(enabled=True, default_tenant="default")
    enricher = EventEnricher(sensors_config, tenancy=tenancy)
    event = EnrichedEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0, "pressure": 4.5, "vibration": 3.2},
        tags={"tenant_id": "acme"},
    )
    enriched = enricher.enrich(event)
    assert enriched.tenant_id == "acme"
    assert enriched.tags["tenant_id"] == "acme"


def test_resolve_event_tenant_default(sensors_config):
    tenancy = TenancyConfig(enabled=True, default_tenant="default")
    event = EnrichedEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0},
    )
    assert resolve_event_tenant(event, tenancy) == "default"


@pytest.mark.asyncio
async def test_memory_storage_tenant_filter():
    storage = MemoryStorage()
    await storage.connect()
    t1 = EnrichedEvent(
        tenant_id="acme",
        device_id="d1",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 1.0},
    )
    t2 = EnrichedEvent(
        tenant_id="globex",
        device_id="d2",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 2.0},
    )
    await storage.write_event(t1)
    await storage.write_event(t2)

    acme_events = await storage.recent_events(10, tenant_id="acme")
    assert len(acme_events) == 1
    assert acme_events[0].tenant_id == "acme"
    await storage.disconnect()


@pytest.mark.asyncio
async def test_tenant_api_key_scopes_events():
    storage = MemoryStorage()
    await storage.connect()
    await storage.write_event(
        EnrichedEvent(
            tenant_id="acme",
            device_id="d1",
            sensor_type="industrial",
            timestamp=datetime.now(timezone.utc),
            metrics={"temperature": 65.0},
        )
    )
    await storage.write_event(
        EnrichedEvent(
            tenant_id="globex",
            device_id="d2",
            sensor_type="industrial",
            timestamp=datetime.now(timezone.utc),
            metrics={"temperature": 70.0},
        )
    )

    viz = VizConfig(security=ApiSecurityConfig(api_key="", rate_limit_enabled=False))
    tenancy = TenancyConfig(
        enabled=True,
        tenant_api_keys={"acme": "key-acme", "globex": "key-globex"},
    )
    api = VizAPI(storage, viz_config=viz, tenancy_config=tenancy)

    async with TestClient(TestServer(api.app)) as client:
        acme = await client.get("/api/events", headers={"X-API-Key": "key-acme"})
        assert acme.status == 200
        assert len(await acme.json()) == 1

        globex = await client.get("/api/events", headers={"X-API-Key": "key-globex"})
        assert globex.status == 200
        assert len(await globex.json()) == 1

        denied = await client.get("/api/events")
        assert denied.status == 401

    await storage.disconnect()