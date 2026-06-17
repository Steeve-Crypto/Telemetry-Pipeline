"""Prometheus-compatible metrics exporter with optional per-tenant labels."""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from telemetry.config import PrometheusConfig
from telemetry.models import PipelineMetrics


@dataclass
class TenantMetricSnapshot:
    tenant_id: str = "default"
    ingested: int = 0
    valid: int = 0
    invalid: int = 0
    deduped: int = 0
    anomaly: int = 0
    throughput_eps: float = 0.0
    avg_ingest_latency_ms: float = 0.0
    p95_ingest_latency_ms: float = 0.0
    avg_processing_latency_ms: float = 0.0
    p95_processing_latency_ms: float = 0.0
    p99_processing_latency_ms: float = 0.0
    processing_latency_ms: float | None = None


class PrometheusExporter:
    def __init__(self, config: PrometheusConfig, registry: CollectorRegistry | None = None) -> None:
        self._config = config
        self._registry = registry or CollectorRegistry()
        self._per_tenant = config.per_tenant_labels
        ns = config.namespace
        labels = ["tenant_id"] if self._per_tenant else []

        self._events_ingested = Counter(
            f"{ns}_events_ingested_total",
            "Total events ingested",
            labelnames=labels,
            registry=self._registry,
        )
        self._events_valid = Counter(
            f"{ns}_events_valid_total",
            "Total valid events",
            labelnames=labels,
            registry=self._registry,
        )
        self._events_invalid = Counter(
            f"{ns}_events_invalid_total",
            "Total invalid events",
            labelnames=labels,
            registry=self._registry,
        )
        self._events_deduped = Counter(
            f"{ns}_events_deduped_total",
            "Total deduplicated events",
            labelnames=labels,
            registry=self._registry,
        )
        self._anomalies = Counter(
            f"{ns}_anomalies_detected_total",
            "Total anomalies detected",
            labelnames=labels,
            registry=self._registry,
        )
        self._throughput = Gauge(
            f"{ns}_throughput_eps",
            "Current events per second",
            labelnames=labels,
            registry=self._registry,
        )
        self._ingest_latency = Gauge(
            f"{ns}_ingest_latency_avg_ms",
            "Average ingest latency (ms)",
            labelnames=labels,
            registry=self._registry,
        )
        self._ingest_p95 = Gauge(
            f"{ns}_ingest_latency_p95_ms",
            "P95 ingest latency (ms)",
            labelnames=labels,
            registry=self._registry,
        )
        self._processing_latency = Gauge(
            f"{ns}_processing_latency_avg_ms",
            "Average processing latency (ms)",
            labelnames=labels,
            registry=self._registry,
        )
        self._processing_p95 = Gauge(
            f"{ns}_processing_latency_p95_ms",
            "P95 processing latency (ms)",
            labelnames=labels,
            registry=self._registry,
        )
        self._processing_p99 = Gauge(
            f"{ns}_processing_latency_p99_ms",
            "P99 processing latency (ms)",
            labelnames=labels,
            registry=self._registry,
        )
        self._processing_histogram = Histogram(
            f"{ns}_processing_latency_seconds",
            "End-to-end per-event processing latency",
            labelnames=labels,
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self._registry,
        )
        self._last_global = {
            "ingested": 0,
            "valid": 0,
            "invalid": 0,
            "deduped": 0,
            "anomalies": 0,
        }

    @property
    def per_tenant_labels(self) -> bool:
        return self._per_tenant

    def record_event(self, snapshot: TenantMetricSnapshot) -> None:
        tenant_id = snapshot.tenant_id or "default"
        if self._per_tenant:
            labels = {"tenant_id": tenant_id}
            self._inc(self._events_ingested, snapshot.ingested, labels)
            self._inc(self._events_valid, snapshot.valid, labels)
            self._inc(self._events_invalid, snapshot.invalid, labels)
            self._inc(self._events_deduped, snapshot.deduped, labels)
            self._inc(self._anomalies, snapshot.anomaly, labels)
            self._throughput.labels(**labels).set(snapshot.throughput_eps)
            self._ingest_latency.labels(**labels).set(snapshot.avg_ingest_latency_ms)
            self._ingest_p95.labels(**labels).set(snapshot.p95_ingest_latency_ms)
            self._processing_latency.labels(**labels).set(snapshot.avg_processing_latency_ms)
            self._processing_p95.labels(**labels).set(snapshot.p95_processing_latency_ms)
            self._processing_p99.labels(**labels).set(snapshot.p99_processing_latency_ms)
            if snapshot.processing_latency_ms is not None:
                self._processing_histogram.labels(**labels).observe(
                    snapshot.processing_latency_ms / 1000.0
                )
            return

        self._inc(self._events_ingested, snapshot.ingested)
        self._inc(self._events_valid, snapshot.valid)
        self._inc(self._events_invalid, snapshot.invalid)
        self._inc(self._events_deduped, snapshot.deduped)
        self._inc(self._anomalies, snapshot.anomaly)
        self._throughput.set(snapshot.throughput_eps)
        self._ingest_latency.set(snapshot.avg_ingest_latency_ms)
        self._ingest_p95.set(snapshot.p95_ingest_latency_ms)
        self._processing_latency.set(snapshot.avg_processing_latency_ms)
        self._processing_p95.set(snapshot.p95_processing_latency_ms)
        self._processing_p99.set(snapshot.p99_processing_latency_ms)
        if snapshot.processing_latency_ms is not None:
            self._processing_histogram.observe(snapshot.processing_latency_ms / 1000.0)

    def update(
        self,
        metrics: PipelineMetrics,
        *,
        tenant_id: str = "default",
        processing_latency_ms: float | None = None,
    ) -> None:
        """Backward-compatible batch update (benchmark harness)."""
        self.record_event(
            TenantMetricSnapshot(
                tenant_id=tenant_id,
                ingested=metrics.events_ingested - self._last_global["ingested"],
                valid=metrics.events_valid - self._last_global["valid"],
                invalid=metrics.events_invalid - self._last_global["invalid"],
                deduped=metrics.events_deduped - self._last_global["deduped"],
                anomaly=metrics.anomalies_detected - self._last_global["anomalies"],
                throughput_eps=metrics.processing_rate_eps,
                avg_ingest_latency_ms=metrics.avg_ingest_latency_ms,
                p95_ingest_latency_ms=metrics.p95_ingest_latency_ms,
                avg_processing_latency_ms=metrics.avg_processing_latency_ms,
                p95_processing_latency_ms=metrics.p95_processing_latency_ms,
                p99_processing_latency_ms=metrics.p99_processing_latency_ms,
                processing_latency_ms=processing_latency_ms,
            )
        )
        self._last_global = {
            "ingested": metrics.events_ingested,
            "valid": metrics.events_valid,
            "invalid": metrics.events_invalid,
            "deduped": metrics.events_deduped,
            "anomalies": metrics.anomalies_detected,
        }

    def _inc(self, counter: Counter, delta: int, labels: dict[str, str] | None = None) -> None:
        if delta <= 0:
            return
        if labels:
            counter.labels(**labels).inc(delta)
        else:
            counter.inc(delta)

    def render(self) -> tuple[bytes, str]:
        return generate_latest(self._registry), CONTENT_TYPE_LATEST