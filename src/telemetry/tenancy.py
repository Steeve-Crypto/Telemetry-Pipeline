"""Multi-tenant resolution for ingestion and API access."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from aiohttp import web

    from telemetry.config import TenancyConfig
    from telemetry.models import EnrichedEvent, SensorEvent

logger = structlog.get_logger(__name__)


def load_tenant_api_keys(config: TenancyConfig) -> dict[str, str]:
    """Return tenant_id -> api_key mapping from config and environment."""
    keys = dict(config.tenant_api_keys)
    raw = os.environ.get("TELEMETRY_TENANT_KEYS", "")
    if raw:
        try:
            env_keys = json.loads(raw)
            if isinstance(env_keys, dict):
                keys.update({str(k): str(v) for k, v in env_keys.items()})
        except json.JSONDecodeError:
            logger.warning("tenant_keys_env_invalid_json")
    return keys


def tenant_for_api_key(api_key: str, tenant_keys: dict[str, str]) -> str | None:
    for tenant_id, key in tenant_keys.items():
        if key and api_key == key:
            return tenant_id
    return None


def resolve_event_tenant(
    event: SensorEvent | EnrichedEvent,
    config: TenancyConfig,
) -> str:
    if not config.enabled:
        return config.default_tenant
    tag_tenant = event.tags.get("tenant_id") or event.tags.get("tenant")
    if tag_tenant:
        return tag_tenant
    explicit = getattr(event, "tenant_id", None)
    if explicit and explicit != config.default_tenant:
        return explicit
    return config.default_tenant


def resolve_request_tenant(request: web.Request, config: TenancyConfig) -> str | None:
    header_tenant = request.headers.get("X-Tenant-ID") or request.query.get("tenant_id")
    tenant_keys = load_tenant_api_keys(config)

    if tenant_keys:
        api_key = request.headers.get("X-API-Key") or request.query.get("api_key", "")
        mapped = tenant_for_api_key(api_key, tenant_keys) if api_key else None
        if mapped:
            if header_tenant and header_tenant != mapped:
                return None
            return mapped
        if config.require_tenant_header:
            return None
        return header_tenant or config.default_tenant

    if header_tenant:
        return header_tenant
    if config.require_tenant_header:
        return None
    return config.default_tenant if config.enabled else None