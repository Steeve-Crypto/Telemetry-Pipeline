"""TimescaleDB and in-memory storage backends."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import structlog

from telemetry.config import PipelineYamlConfig, StorageConfig
from telemetry.models import AnomalyScore, EnrichedEvent, WindowStats

logger = structlog.get_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    ingest_latency_ms DOUBLE PRECISION,
    metrics JSONB NOT NULL,
    tags JSONB,
    is_anomaly BOOLEAN DEFAULT FALSE,
    anomaly_label TEXT,
    PRIMARY KEY (event_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_events_device_time ON telemetry_events (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_sensor_time ON telemetry_events (sensor_type, timestamp DESC);

CREATE TABLE IF NOT EXISTS window_stats (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    field TEXT NOT NULL,
    count INT NOT NULL,
    mean DOUBLE PRECISION NOT NULL,
    min DOUBLE PRECISION NOT NULL,
    max DOUBLE PRECISION NOT NULL,
    std DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_window_stats_device ON window_stats (device_id, window_start DESC);

CREATE TABLE IF NOT EXISTS anomaly_scores (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL,
    severity TEXT NOT NULL,
    methods JSONB,
    drift_detected BOOLEAN DEFAULT FALSE,
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_anomaly_device_time ON anomaly_scores (device_id, timestamp DESC);
"""


class StorageBackend(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    async def flush(self) -> None:
        """Flush buffered writes. Override where buffering is used."""

    @abstractmethod
    async def write_event(self, event: EnrichedEvent) -> None: ...

    @abstractmethod
    async def write_window_stats(self, stats: list[WindowStats]) -> None: ...

    @abstractmethod
    async def write_anomaly(self, score: AnomalyScore) -> None: ...

    @abstractmethod
    async def recent_events(self, limit: int = 100) -> list[EnrichedEvent]: ...

    @abstractmethod
    async def recent_anomalies(self, limit: int = 50) -> list[AnomalyScore]: ...


class MemoryStorage(StorageBackend):
    def __init__(self) -> None:
        self.events: list[EnrichedEvent] = []
        self.window_stats: list[WindowStats] = []
        self.anomalies: list[AnomalyScore] = []

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def write_event(self, event: EnrichedEvent) -> None:
        self.events.append(event)

    async def write_window_stats(self, stats: list[WindowStats]) -> None:
        self.window_stats.extend(stats)

    async def write_anomaly(self, score: AnomalyScore) -> None:
        self.anomalies.append(score)

    async def recent_events(self, limit: int = 100) -> list[EnrichedEvent]:
        return self.events[-limit:]

    async def recent_anomalies(self, limit: int = 50) -> list[AnomalyScore]:
        return self.anomalies[-limit:]


class TimescaleStorage(StorageBackend):
    def __init__(self, config: StorageConfig) -> None:
        self._cfg = config.timescale
        self._pool = None
        self._buffer: list[EnrichedEvent] = []
        self._flush_task: asyncio.Task | None = None

    async def connect(self) -> None:
        import asyncpg

        self._pool = await asyncpg.create_pool(self._cfg.dsn, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
            try:
                await conn.execute(
                    "SELECT create_hypertable('telemetry_events', 'timestamp', if_not_exists => TRUE)"
                )
            except Exception:
                logger.debug("hypertable_already_exists_or_extension_missing")
            await self._apply_retention_policies(conn)
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("timescale_connected")

    async def _apply_retention_policies(self, conn: object) -> None:
        cfg = self._cfg
        if not cfg.enable_retention_policy:
            return
        try:
            await conn.execute(
                f"""
                SELECT add_compression_policy('telemetry_events', INTERVAL '{cfg.compression_after_days} days',
                    if_not_exists => TRUE)
                """
            )
            await conn.execute(
                f"""
                SELECT add_retention_policy('telemetry_events', INTERVAL '{cfg.retention_days} days',
                    if_not_exists => TRUE)
                """
            )
            logger.info(
                "timescale_retention_applied",
                retention_days=cfg.retention_days,
                compression_after_days=cfg.compression_after_days,
            )
        except Exception as exc:
            logger.warning("timescale_retention_policy_skipped", error=str(exc))

    async def disconnect(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(self._cfg.flush_interval_seconds)
            await self.flush()

    async def write_event(self, event: EnrichedEvent) -> None:
        self._buffer.append(event)
        if len(self._buffer) >= self._cfg.batch_size:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer or self._pool is None:
            return
        batch = self._buffer
        self._buffer = []
        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO telemetry_events
                (event_id, device_id, sensor_type, timestamp, ingested_at,
                 ingest_latency_ms, metrics, tags, is_anomaly, anomaly_label)
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10)
                ON CONFLICT (event_id, timestamp) DO NOTHING
                """,
                [
                    (
                        e.event_id,
                        e.device_id,
                        e.sensor_type,
                        e.timestamp,
                        e.ingested_at,
                        e.ingest_latency_ms,
                        __import__("json").dumps(e.metrics),
                        __import__("json").dumps(e.tags),
                        e.is_anomaly,
                        e.anomaly_label,
                    )
                    for e in batch
                ],
            )

    async def write_window_stats(self, stats: list[WindowStats]) -> None:
        if not stats or self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO window_stats
                (device_id, sensor_type, window_start, window_end, field, count, mean, min, max, std)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                [
                    (
                        s.device_id,
                        s.sensor_type,
                        s.window_start,
                        s.window_end,
                        s.field,
                        s.count,
                        s.mean,
                        s.min,
                        s.max,
                        s.std,
                    )
                    for s in stats
                ],
            )

    async def write_anomaly(self, score: AnomalyScore) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO anomaly_scores
                (device_id, sensor_type, timestamp, score, is_anomaly, severity, methods, drift_detected, message)
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9)
                """,
                score.device_id,
                score.sensor_type,
                score.timestamp,
                score.score,
                score.is_anomaly,
                score.severity.value,
                __import__("json").dumps(score.methods),
                score.drift_detected,
                score.message,
            )

    async def recent_events(self, limit: int = 100) -> list[EnrichedEvent]:
        if self._pool is None:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_id, device_id, sensor_type, timestamp, ingested_at,
                       ingest_latency_ms, metrics, tags, is_anomaly, anomaly_label
                FROM telemetry_events
                ORDER BY timestamp DESC
                LIMIT $1
                """,
                limit,
            )
        return [_row_to_event(r) for r in rows]

    async def recent_anomalies(self, limit: int = 50) -> list[AnomalyScore]:
        if self._pool is None:
            return []
        from telemetry.models import Severity

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT device_id, sensor_type, timestamp, score, is_anomaly,
                       severity, methods, drift_detected, message
                FROM anomaly_scores
                ORDER BY timestamp DESC
                LIMIT $1
                """,
                limit,
            )
        return [
            AnomalyScore(
                device_id=r["device_id"],
                sensor_type=r["sensor_type"],
                timestamp=r["timestamp"],
                score=r["score"],
                is_anomaly=r["is_anomaly"],
                severity=Severity(r["severity"]),
                methods=__import__("json").loads(r["methods"] or "{}"),
                drift_detected=r["drift_detected"],
                message=r["message"] or "",
            )
            for r in rows
        ]


def _row_to_event(row: object) -> EnrichedEvent:
    import json

    r = dict(row)  # type: ignore[arg-type]
    return EnrichedEvent(
        event_id=r["event_id"],
        device_id=r["device_id"],
        sensor_type=r["sensor_type"],
        timestamp=r["timestamp"],
        ingested_at=r["ingested_at"],
        ingest_latency_ms=r["ingest_latency_ms"],
        metrics=json.loads(r["metrics"]),
        tags=json.loads(r["tags"] or "{}"),
        is_anomaly=r["is_anomaly"],
        anomaly_label=r["anomaly_label"],
    )


def create_storage(config: PipelineYamlConfig) -> StorageBackend:
    if config.storage.backend == "memory":
        return MemoryStorage()
    if config.storage.backend == "clickhouse":
        from telemetry.storage.clickhouse import ClickHouseStorage

        return ClickHouseStorage(config.storage.clickhouse)
    return TimescaleStorage(config.storage)