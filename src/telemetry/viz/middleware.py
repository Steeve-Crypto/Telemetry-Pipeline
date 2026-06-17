"""API authentication, rate limiting, and tenant scoping middleware."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from aiohttp import web

from telemetry.config import ApiSecurityConfig, TenancyConfig

TENANT_ID_KEY = web.RequestKey("tenant_id", str)
from telemetry.tenancy import load_tenant_api_keys, resolve_request_tenant, tenant_for_api_key


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self._rpm = max(requests_per_minute, 1)
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._windows[key]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self._rpm:
            return False
        window.append(now)
        return True


def build_security_middleware(
    config: ApiSecurityConfig,
    tenancy: TenancyConfig | None = None,
) -> web.Middleware:
    tenancy = tenancy or TenancyConfig()
    global_api_key = config.api_key or os.environ.get("TELEMETRY_API_KEY", "")
    if os.environ.get("TELEMETRY_API_KEY"):
        global_api_key = os.environ["TELEMETRY_API_KEY"]

    tenant_keys = load_tenant_api_keys(tenancy) if tenancy.enabled else {}
    limiter = RateLimiter(config.rate_limit_rpm) if config.rate_limit_enabled else None
    public_paths = {"/health", "/metrics"}

    @web.middleware
    async def security_middleware(request: web.Request, handler: web.Handler) -> web.StreamResponse:
        path = request.path

        if path not in public_paths:
            provided = request.headers.get("X-API-Key") or request.query.get("api_key", "")

            if tenant_keys:
                mapped_tenant = tenant_for_api_key(provided, tenant_keys) if provided else None
                if not mapped_tenant:
                    return web.json_response({"error": "unauthorized"}, status=401)
                request[TENANT_ID_KEY] = mapped_tenant
            elif global_api_key:
                if provided != global_api_key:
                    return web.json_response({"error": "unauthorized"}, status=401)

            if tenancy.enabled and TENANT_ID_KEY not in request:
                tenant_id = resolve_request_tenant(request, tenancy)
                if tenant_id is None:
                    return web.json_response({"error": "tenant required"}, status=400)
                request[TENANT_ID_KEY] = tenant_id

        if limiter is not None and path.startswith("/api"):
            rate_key = request.get(TENANT_ID_KEY) or request.remote or "unknown"
            if not limiter.allow(rate_key):
                return web.json_response({"error": "rate limit exceeded"}, status=429)

        return await handler(request)

    return security_middleware