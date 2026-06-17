"""OpenTelemetry tracing for pipeline events."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator

import structlog

if TYPE_CHECKING:
    from telemetry.config import OpenTelemetryConfig

logger = structlog.get_logger(__name__)


class TelemetryTracer:
    def __init__(self, config: OpenTelemetryConfig) -> None:
        self._config = config
        self._tracer = None
        self._enabled = False

        if not config.enabled:
            return

        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": config.service_name})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=f"{config.endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(config.service_name)
            self._enabled = True
            logger.info("opentelemetry_enabled", endpoint=config.endpoint)
        except ImportError:
            logger.warning("opentelemetry_not_installed", hint="pip install -e '.[otel]'")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Generator[None, None, None]:
        if not self._enabled or self._tracer is None:
            yield
            return

        with self._tracer.start_as_current_span(name) as otel_span:
            if attributes:
                for key, value in attributes.items():
                    otel_span.set_attribute(key, value)
            yield