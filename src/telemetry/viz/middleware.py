"""API authentication and rate limiting middleware."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from aiohttp import web

from telemetry.config import ApiSecurityConfig


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


def build_security_middleware(config: ApiSecurityConfig) -> web.Middleware:
    api_key = config.api_key or os.environ.get("TELEMETRY_API_KEY", "")
    if os.environ.get("TELEMETRY_API_KEY"):
        api_key = os.environ["TELEMETRY_API_KEY"]

    limiter = RateLimiter(config.rate_limit_rpm) if config.rate_limit_enabled else None
    public_paths = {"/health", "/metrics"}

    @web.middleware
    async def security_middleware(request: web.Request, handler: web.Handler) -> web.StreamResponse:
        path = request.path

        if path not in public_paths and api_key:
            provided = request.headers.get("X-API-Key") or request.query.get("api_key", "")
            if provided != api_key:
                return web.json_response({"error": "unauthorized"}, status=401)

        if limiter is not None and path.startswith("/api"):
            client = request.remote or "unknown"
            if not limiter.allow(client):
                return web.json_response({"error": "rate limit exceeded"}, status=429)

        return await handler(request)

    return security_middleware