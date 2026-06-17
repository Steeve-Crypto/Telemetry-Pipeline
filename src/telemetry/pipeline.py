"""Core pipeline orchestrator."""

from __future__ import annotations

import asyncio
import time

import structlog

from telemetry.alerting import AlertDispatcher
from telemetry.anomaly.detector import AnomalyDetector
from telemetry.config import PipelineYamlConfig, SensorsYamlConfig
from telemetry.ingestion.base import IngestionSource, create_ingestion_source
from telemetry.metrics import LatencyTracker, ThroughputTracker
from telemetry.models import PipelineMetrics
from telemetry.processor.aggregator import WindowAggregator
from telemetry.processor.windows import TumblingWindow
from telemetry.storage.timescale import StorageBackend, create_storage
from telemetry.validation.enricher import EventEnricher
from telemetry.validation.schema_validator import SchemaValidator

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
        )
        self._window = TumblingWindow(
            pipeline_config.processing.window_size_seconds,
            pipeline_config.processing.slide_interval_seconds,
        )
        self._aggregator = WindowAggregator()
        self._anomaly = AnomalyDetector(pipeline_config.anomaly, sensors_config)
        self._alerts = AlertDispatcher(pipeline_config.alerting)
        self._latency = LatencyTracker()
        self._throughput = ThroughputTracker()
        self._running = False
        self._metrics = PipelineMetrics()

    @property
    def metrics(self) -> PipelineMetrics:
        return self._metrics

    @property
    def storage(self) -> StorageBackend:
        return self._storage

    async def start(self) -> None:
        await self._ingestion.connect()
        await self._storage.connect()
        self._running = True
        logger.info("pipeline_started", transport=self._config.ingestion.transport)

    async def stop(self) -> None:
        self._running = False
        await self._ingestion.disconnect()
        await self._storage.disconnect()
        logger.info("pipeline_stopped")

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

        event = raw_event if isinstance(raw_event, SensorEvent) else SensorEvent.model_validate(raw_event)
        self._metrics.events_ingested += 1
        self._throughput.record()

        start_id = f"evt-{self._metrics.events_ingested}"
        self._latency.start(start_id)

        enriched = self._validator.validate(event)
        if not self._validator.is_valid(enriched):
            self._metrics.events_invalid += 1
            if self._config.validation.drop_invalid:
                return

        if any(e.startswith("dedup:") for e in enriched.validation_errors):
            self._metrics.events_deduped += 1
            return

        self._metrics.events_valid += 1
        enriched = self._enricher.enrich(enriched)

        latency_ms = self._latency.end(start_id)
        if latency_ms is not None:
            self._metrics.avg_ingest_latency_ms = self._latency.mean
            self._metrics.p95_ingest_latency_ms = self._latency.percentile(95)

        await self._storage.write_event(enriched)

        for _key, window_events in self._window.add(enriched):
            stats = self._aggregator.aggregate(_key, window_events)
            await self._storage.write_window_stats(stats)

        anomaly_score = self._anomaly.detect(enriched)
        if anomaly_score:
            self._metrics.anomalies_detected += 1
            await self._storage.write_anomaly(anomaly_score)
            await self._alerts.dispatch(anomaly_score)

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
        ingestion = create_ingestion_source(pipeline_config, memory_queue=queue)
        storage = create_storage(pipeline_config)
        instance = cls(pipeline_config, sensors_config, ingestion=ingestion, storage=storage)
        return instance, queue