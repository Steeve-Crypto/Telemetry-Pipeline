"""API authentication and rate limiting tests."""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from telemetry.config import ApiSecurityConfig, VizConfig
from telemetry.storage.timescale import MemoryStorage
from telemetry.viz.api import VizAPI


@pytest.fixture
def secured_api():
    viz = VizConfig(
        security=ApiSecurityConfig(api_key="secret-key", rate_limit_enabled=False),
    )
    return VizAPI(MemoryStorage(), viz_config=viz)


@pytest.mark.asyncio
async def test_health_public_without_key(secured_api):
    async with TestClient(TestServer(secured_api.app)) as client:
        resp = await client.get("/health")
        assert resp.status == 200


@pytest.mark.asyncio
async def test_api_requires_key(secured_api):
    async with TestClient(TestServer(secured_api.app)) as client:
        resp = await client.get("/api/events")
        assert resp.status == 401


@pytest.mark.asyncio
async def test_api_accepts_header_key(secured_api):
    async with TestClient(TestServer(secured_api.app)) as client:
        resp = await client.get("/api/events", headers={"X-API-Key": "secret-key"})
        assert resp.status == 200


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess():
    viz = VizConfig(
        security=ApiSecurityConfig(api_key="", rate_limit_enabled=True, rate_limit_rpm=2),
    )
    api = VizAPI(MemoryStorage(), viz_config=viz)
    async with TestClient(TestServer(api.app)) as client:
        assert (await client.get("/api/events")).status == 200
        assert (await client.get("/api/events")).status == 200
        assert (await client.get("/api/events")).status == 429