"""Core pipeline orchestrator."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

import structlog

from telemetry.alerting import AlertDispatcher
from telemetry.anomaly.detector import AnomalyDetector
from telemetry.config import PipelineYamlConfig, SensorsYamlConfig
from telemetry.ingestion.base import IngestionSource, create_ingestion_source
from telemetry.metrics import LatencyTracker, ThroughputTracker
from telemetry.models import PipelineMetrics
from telemetry.otel import TelemetryTracer
from telemetry.processor.aggregator import WindowAggregator
from telemetry.processor.windows import TumblingWindow
from telemetry.prometheus import PrometheusExporter, TenantMetricSnapshot
from telemetry.tenancy import resolve_event_tenant
from telemetry.storage.timescale import StorageBackend, create_storage
from telemetry.validation.enricher import EventEnricher
from telemetry.validation.schema_validator import SchemaValidator
from telemetry.viz.api import VizAPI

logger = structlog.get_logger(__name__)


class TelemetryPipeline:
    def __init__(
        self,
        pipeline_config: PipelineYamlConfig,
        sensors_config: SensorsYamlConfig,
        ingestion: IngestionSource | None = None,
        storage: StorageBackend | None = None,
    ) -> None:
        self._config = pipeline_config
        self._sensors = sensors_config
        self._ingestion = ingestion or create_ingestion_source(pipeline_config)
        self._storage = storage or create_storage(pipeline_config)
        self._validator = SchemaValidator(pipeline_config.validation, sensors_config)
        self._enricher = EventEnricher(
            sensors_config,
            environment=pipeline_config.pipeline.get("environment", "local"),
            tenancy=pipeline_config.tenancy,
        )
        self._window = TumblingWindow(
            pipeline_config.processing.window_size_seconds,
            pipeline_config.processing.slide_interval_seconds,
        )
        self._aggregator = WindowAggregator()
        self._anomaly = AnomalyDetector(pipeline_config.anomaly, sensors_config)
        self._alerts = AlertDispatcher(pipeline_config.alerting)
        self._ingest_latency = LatencyTracker()
        self._processing_latency = LatencyTracker()
        self._throughput = ThroughputTracker()
        self._tenant_ingest_latency: dict[str, LatencyTracker] = defaultdict(LatencyTracker)
        self._tenant_processing_latency: dict[str, LatencyTracker] = defaultdict(LatencyTracker)
        self._tenant_throughput: dict[str, ThroughputTracker] = defaultdict(ThroughputTracker)
        self._running = False
        self._shutting_down = False
        self._inflight = 0
        self._inflight_lock = asyncio.Lock()
        self._metrics = PipelineMetrics()
        self._prometheus = (
            PrometheusExporter(pipeline_config.prometheus)
            if pipeline_config.prometheus.enabled
            else None
        )
        self._tracer = TelemetryTracer(pipeline_config.opentelemetry)
        self._viz: VizAPI | None = None
        self._viz_task: asyncio.Task | None = None
        self._viz_runner = None

    @property
    def metrics(self) -> PipelineMetrics:
        return self._metrics

    @property
    def storage(self) -> StorageBackend:
        return self._storage

    @property
    def viz(self) -> VizAPI | None:
        return self._viz

    def metrics_dict(self) -> dict[str, object]:
        self._metrics.latency_histogram = self._processing_latency.histogram(
            self._config.metrics.latency_histogram_buckets_ms
        )
        return self._metrics.to_api_dict()

    async def start(self) -> None:
        await self._ingestion.connect()
        await self._storage.connect()
        self._running = True

        if self._config.viz.enabled:
            self._viz = VizAPI(
                self._storage,
                self._prometheus,
                self._config.viz,
                self._config.tenancy,
            )
            self._viz_runner = await self._viz.start(
                host=self._config.viz.host,
                port=self._config.viz.port,
            )
            self._viz_task = asyncio.create_task(self._refresh_viz_metrics())
            logger.info("viz_api_started", port=self._config.viz.port)

        logger.info("pipeline_started", transport=self._config.ingestion.transport)

    async def stop(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._running = False

        deadline = time.monotonic() + self._config.shutdown.drain_timeout_seconds
        while self._inflight > 0 and time.monotonic() < deadline:
            await asyncio.sleep(0.05)

        if self._inflight > 0:
            logger.warning("shutdown_drain_timeout", inflight=self._inflight)

        if self._viz_task:
            self._viz_task.cancel()
            try:
                await self._viz_task
            except asyncio.CancelledError:
                pass
        if self._viz:
            await self._viz.stop()

        await self._storage.flush()
        await self._ingestion.disconnect()
        await self._storage.disconnect()
        logger.info("pipeline_stopped", events_processed=self._metrics.events_ingested)

    async def _refresh_viz_metrics(self) -> None:
        interval = self._config.viz.metrics_refresh_seconds
        while self._running:
            if self._viz:
                self._viz.set_pipeline_metrics(self.metrics_dict())
            await asyncio.sleep(interval)

    async def run(self) -> None:
        await self.start()
        try:
            async for raw_event in self._ingestion.events():
                if not self._running:
                    break
                await self.process_event(raw_event)
        finally:
            await self.stop()

    async def process_event(self, raw_event: object) -> None:
        from telemetry.models import SensorEvent

        async with self._inflight_lock:
            self._inflight += 1

        try:
            with self._tracer.span(
                "process_event",
                attributes={"transport": self._config.ingestion.transport},
            ):
                t0 = time.perf_counter()
                event = (
                    raw_event
                    if isinstance(raw_event, SensorEvent)
                    else SensorEvent.model_validate(raw_event)
                )
                tenant_id = resolve_event_tenant(event, self._config.tenancy)
                self._metrics.events_ingested += 1
                self._throughput.record()
                self._tenant_throughput[tenant_id].record()

                ingest_id = f"ingest-{self._metrics.events_ingested}"
                self._ingest_latency.start(ingest_id)
                self._tenant_ingest_latency[tenant_id].start(ingest_id)

                enriched = self._validator.validate(event)
                if not self._validator.is_valid(enriched):
                    self._metrics.events_invalid += 1
                    if self._config.validation.drop_invalid:
                        processing_ms = self._record_processing_latency(t0, tenant_id)
                        self._export_prometheus(
                            tenant_id,
                            ingested=1,
                            invalid=1,
                            processing_ms=processing_ms,
                        )
                        return

                if any(e.startswith("dedup:") for e in enriched.validation_errors):
                    self._metrics.events_deduped += 1
                    processing_ms = self._record_processing_latency(t0, tenant_id)
                    self._export_prometheus(
                        tenant_id,
                        ingested=1,
                        deduped=1,
                        processing_ms=processing_ms,
                    )
                    return

                self._metrics.events_valid += 1
                enriched = self._enricher.enrich(enriched)
                tenant_id = enriched.tenant_id

                self._ingest_latency.end(ingest_id)
                self._tenant_ingest_latency[tenant_id].end(ingest_id)
                self._metrics.avg_ingest_latency_ms = self._ingest_latency.mean
                self._metrics.p95_ingest_latency_ms = self._ingest_latency.percentile(95)

                await self._storage.write_event(enriched)

                for _key, window_events in self._window.add(enriched):
                    stats = self._aggregator.aggregate(_key, window_events)
                    await self._storage.write_window_stats(stats)

                anomaly_detected = 0
                anomaly_score = self._anomaly.detect(enriched)
                if anomaly_score:
                    anomaly_detected = 1
                    self._metrics.anomalies_detected += 1
                    await self._storage.write_anomaly(anomaly_score)
                    await self._alerts.dispatch(anomaly_score)

                self._metrics.processing_rate_eps = self._throughput.events_per_second
                processing_ms = self._record_processing_latency(t0, tenant_id)
                self._export_prometheus(
                    tenant_id,
                    ingested=1,
                    valid=1,
                    anomaly=anomaly_detected,
                    processing_ms=processing_ms,
                )
        finally:
            async with self._inflight_lock:
                self._inflight -= 1

    def _record_processing_latency(self, t0: float, tenant_id: str = "default") -> float:
        processing_ms = (time.perf_counter() - t0) * 1000
        self._processing_latency.record(processing_ms)
        self._tenant_processing_latency[tenant_id].record(processing_ms)
        self._metrics.avg_processing_latency_ms = self._processing_latency.mean
        self._metrics.p95_processing_latency_ms = self._processing_latency.percentile(95)
        self._metrics.p99_processing_latency_ms = self._processing_latency.percentile(99)
        return processing_ms

    def _export_prometheus(
        self,
        tenant_id: str,
        *,
        ingested: int = 0,
        valid: int = 0,
        invalid: int = 0,
        deduped: int = 0,
        anomaly: int = 0,
        processing_ms: float | None = None,
    ) -> None:
        if not self._prometheus:
            return

        tenant_proc = self._tenant_processing_latency[tenant_id]
        tenant_ingest = self._tenant_ingest_latency[tenant_id]
        tenant_tput = self._tenant_throughput[tenant_id]

        if self._prometheus.per_tenant_labels:
            self._prometheus.record_event(
                TenantMetricSnapshot(
                    tenant_id=tenant_id,
                    ingested=ingested,
                    valid=valid,
                    invalid=invalid,
                    deduped=deduped,
                    anomaly=anomaly,
                    throughput_eps=tenant_tput.events_per_second,
                    avg_ingest_latency_ms=tenant_ingest.mean,
                    p95_ingest_latency_ms=tenant_ingest.percentile(95),
                    avg_processing_latency_ms=tenant_proc.mean,
                    p95_processing_latency_ms=tenant_proc.percentile(95),
                    p99_processing_latency_ms=tenant_proc.percentile(99),
                    processing_latency_ms=processing_ms,
                )
            )
        else:
            self._prometheus.update(self._metrics, processing_latency_ms=processing_ms)

    async def process_event_minimal(self, raw_event: object) -> None:
        """Fast ingest path for load testing (validation/windows/anomaly skipped)."""
        from datetime import datetime, timezone

        from telemetry.models import EnrichedEvent, SensorEvent

        event = (
            raw_event
            if isinstance(raw_event, SensorEvent)
            else SensorEvent.model_validate(raw_event)
        )
        self._metrics.events_ingested += 1
        self._metrics.events_valid += 1
        self._throughput.record()
        enriched = EnrichedEvent(
            **event.model_dump(),
            ingested_at=datetime.now(timezone.utc),
            validation_errors=[],
        )
        await self._storage.write_event(enriched)
        self._metrics.processing_rate_eps = self._throughput.events_per_second

    async def process_batch(self, events: list) -> None:
        for event in events:
            await self.process_event(event)


class InMemoryPipeline(TelemetryPipeline):
    """Pipeline wired to an asyncio queue for testing."""

    @classmethod
    def create(
        cls,
        pipeline_config: PipelineYamlConfig,
        sensors_config: SensorsYamlConfig,
    ) -> tuple["InMemoryPipeline", asyncio.Queue]:
        queue: asyncio.Queue = asyncio.Queue()
        pipeline_config.storage.backend = "memory"
        pipeline_config.viz.enabled = False
        pipeline_config.prometheus.enabled = False
        pipeline_config.opentelemetry.enabled = False
        ingestion = create_ingestion_source(pipeline_config, memory_queue=queue)
        storage = create_storage(pipeline_config)
        instance = cls(pipeline_config, sensors_config, ingestion=ingestion, storage=storage)
        return instance, queue