"""Prometheus metrics exporter for pipeline observability."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from telemetry.config import PrometheusConfig
from telemetry.models import PipelineMetrics


class PrometheusExporter:
    def __init__(self, config: PrometheusConfig, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()
        ns = config.namespace
        self._events_ingested = Counter(
            f"{ns}_events_ingested_total", "Total events ingested", registry=self._registry
        )
        self._events_valid = Counter(
            f"{ns}_events_valid_total", "Total valid events", registry=self._registry
        )
        self._events_invalid = Counter(
            f"{ns}_events_invalid_total", "Total invalid events", registry=self._registry
        )
        self._events_deduped = Counter(
            f"{ns}_events_deduped_total", "Total deduplicated events", registry=self._registry
        )
        self._anomalies = Counter(
            f"{ns}_anomalies_detected_total", "Total anomalies detected", registry=self._registry
        )
        self._throughput = Gauge(
            f"{ns}_throughput_eps", "Current events per second", registry=self._registry
        )
        self._ingest_latency = Gauge(
            f"{ns}_ingest_latency_avg_ms", "Average ingest latency (ms)", registry=self._registry
        )
        self._ingest_p95 = Gauge(
            f"{ns}_ingest_latency_p95_ms", "P95 ingest latency (ms)", registry=self._registry
        )
        self._processing_latency = Gauge(
            f"{ns}_processing_latency_avg_ms",
            "Average processing latency (ms)",
            registry=self._registry,
        )
        self._processing_p95 = Gauge(
            f"{ns}_processing_latency_p95_ms",
            "P95 processing latency (ms)",
            registry=self._registry,
        )
        self._processing_p99 = Gauge(
            f"{ns}_processing_latency_p99_ms",
            "P99 processing latency (ms)",
            registry=self._registry,
        )
        self._processing_histogram = Histogram(
            f"{ns}_processing_latency_seconds",
            "End-to-end per-event processing latency",
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self._registry,
        )
        self._last_ingested = 0
        self._last_valid = 0
        self._last_invalid = 0
        self._last_deduped = 0
        self._last_anomalies = 0

    def update(self, metrics: PipelineMetrics, processing_latency_ms: float | None = None) -> None:
        self._increment(self._events_ingested, metrics.events_ingested, "_last_ingested")
        self._increment(self._events_valid, metrics.events_valid, "_last_valid")
        self._increment(self._events_invalid, metrics.events_invalid, "_last_invalid")
        self._increment(self._events_deduped, metrics.events_deduped, "_last_deduped")
        self._increment(self._anomalies, metrics.anomalies_detected, "_last_anomalies")

        self._throughput.set(metrics.processing_rate_eps)
        self._ingest_latency.set(metrics.avg_ingest_latency_ms)
        self._ingest_p95.set(metrics.p95_ingest_latency_ms)
        self._processing_latency.set(metrics.avg_processing_latency_ms)
        self._processing_p95.set(metrics.p95_processing_latency_ms)
        self._processing_p99.set(metrics.p99_processing_latency_ms)

        if processing_latency_ms is not None:
            self._processing_histogram.observe(processing_latency_ms / 1000.0)

    def _increment(self, counter: Counter, current: int, attr: str) -> None:
        last = getattr(self, attr)
        delta = current - last
        if delta > 0:
            counter.inc(delta)
            setattr(self, attr, current)

    def render(self) -> tuple[bytes, str]:
        return generate_latest(self._registry), CONTENT_TYPE_LATEST