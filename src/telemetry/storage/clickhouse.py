"""ClickHouse storage backend."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

import httpx
import structlog

from telemetry.config import ClickHouseConfig
from telemetry.models import AnomalyScore, EnrichedEvent, WindowStats
from telemetry.storage.timescale import StorageBackend

logger = structlog.get_logger(__name__)

SCHEMA_DDL = """
CREATE DATABASE IF NOT EXISTS {database};

CREATE TABLE IF NOT EXISTS {database}.telemetry_events (
    event_id String,
    tenant_id String DEFAULT 'default',
    device_id String,
    sensor_type String,
    timestamp DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC'),
    ingest_latency_ms Nullable(Float64),
    metrics String,
    tags String,
    is_anomaly UInt8 DEFAULT 0,
    anomaly_label Nullable(String)
) ENGINE = MergeTree()
ORDER BY (tenant_id, sensor_type, device_id, timestamp);

CREATE TABLE IF NOT EXISTS {database}.window_stats (
    tenant_id String DEFAULT 'default',
    device_id String,
    sensor_type String,
    window_start DateTime64(3, 'UTC'),
    window_end DateTime64(3, 'UTC'),
    field String,
    count UInt32,
    mean Float64,
    min Float64,
    max Float64,
    std Float64
) ENGINE = MergeTree()
ORDER BY (device_id, window_start);

CREATE TABLE IF NOT EXISTS {database}.anomaly_scores (
    tenant_id String DEFAULT 'default',
    device_id String,
    sensor_type String,
    timestamp DateTime64(3, 'UTC'),
    score Float64,
    is_anomaly UInt8,
    severity String,
    methods String,
    drift_detected UInt8 DEFAULT 0,
    message String
) ENGINE = MergeTree()
ORDER BY (device_id, timestamp);
"""


class ClickHouseStorage(StorageBackend):
    def __init__(self, config: ClickHouseConfig) -> None:
        self._cfg = config
        self._client: httpx.AsyncClient | None = None
        self._buffer: list[EnrichedEvent] = []
        self._flush_task: asyncio.Task | None = None
        self._base_url = f"http://{config.host}:{config.port}"

    async def connect(self) -> None:
        auth = (self._cfg.user, self._cfg.password) if self._cfg.password else None
        self._client = httpx.AsyncClient(base_url=self._base_url, auth=auth, timeout=30.0)
        ddl = SCHEMA_DDL.format(database=self._cfg.database)
        for statement in ddl.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                await self._execute(stmt)
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("clickhouse_connected", host=self._cfg.host, database=self._cfg.database)

    async def disconnect(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        if self._client:
            await self._client.aclose()
            self._client = None

    async def flush(self) -> None:
        if not self._buffer or self._client is None:
            return
        batch = self._buffer
        self._buffer = []
        rows = [
            [
                e.event_id,
                e.tenant_id,
                e.device_id,
                e.sensor_type,
                _fmt_ts(e.timestamp),
                _fmt_ts(e.ingested_at),
                e.ingest_latency_ms,
                json.dumps(e.metrics),
                json.dumps(e.tags),
                1 if e.is_anomaly else 0,
                e.anomaly_label,
            ]
            for e in batch
        ]
        await self._insert(
            f"INSERT INTO {self._cfg.database}.telemetry_events FORMAT JSONEachRow",
            rows,
            columns=[
                "event_id", "tenant_id", "device_id", "sensor_type", "timestamp", "ingested_at",
                "ingest_latency_ms", "metrics", "tags", "is_anomaly", "anomaly_label",
            ],
        )

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(self._cfg.flush_interval_seconds)
            await self.flush()

    async def _execute(self, query: str) -> None:
        assert self._client is not None
        resp = await self._client.post("/", params={"query": query})
        resp.raise_for_status()

    async def _insert(self, header: str, rows: list, columns: list[str]) -> None:
        assert self._client is not None
        payload = "\n".join(
            json.dumps(dict(zip(columns, row, strict=True))) for row in rows
        )
        query = header
        resp = await self._client.post("/", params={"query": query}, content=payload)
        resp.raise_for_status()

    async def write_event(self, event: EnrichedEvent) -> None:
        self._buffer.append(event)
        if len(self._buffer) >= self._cfg.batch_size:
            await self.flush()

    async def write_window_stats(self, stats: list[WindowStats]) -> None:
        if not stats or self._client is None:
            return
        rows = [
            [
                s.tenant_id, s.device_id, s.sensor_type, _fmt_ts(s.window_start), _fmt_ts(s.window_end),
                s.field, s.count, s.mean, s.min, s.max, s.std,
            ]
            for s in stats
        ]
        await self._insert(
            f"INSERT INTO {self._cfg.database}.window_stats FORMAT JSONEachRow",
            rows,
            columns=[
                "tenant_id", "device_id", "sensor_type", "window_start", "window_end",
                "field", "count", "mean", "min", "max", "std",
            ],
        )

    async def write_anomaly(self, score: AnomalyScore) -> None:
        if self._client is None:
            return
        await self._insert(
            f"INSERT INTO {self._cfg.database}.anomaly_scores FORMAT JSONEachRow",
            [[
                score.tenant_id, score.device_id, score.sensor_type, _fmt_ts(score.timestamp),
                score.score, 1 if score.is_anomaly else 0, score.severity.value,
                json.dumps(score.methods), 1 if score.drift_detected else 0, score.message,
            ]],
            columns=[
                "tenant_id", "device_id", "sensor_type", "timestamp", "score", "is_anomaly",
                "severity", "methods", "drift_detected", "message",
            ],
        )

    async def recent_events(self, limit: int = 100, tenant_id: str | None = None) -> list[EnrichedEvent]:
        if self._client is None:
            return []
        tenant_filter = f"WHERE tenant_id = '{tenant_id}'" if tenant_id else ""
        query = f"""
            SELECT event_id, tenant_id, device_id, sensor_type, timestamp, ingested_at,
                   ingest_latency_ms, metrics, tags, is_anomaly, anomaly_label
            FROM {self._cfg.database}.telemetry_events
            {tenant_filter}
            ORDER BY timestamp DESC LIMIT {limit}
            FORMAT JSON
        """
        resp = await self._client.post("/", params={"query": query})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        events: list[EnrichedEvent] = []
        for row in data:
            events.append(
                EnrichedEvent(
                    event_id=row["event_id"],
                    tenant_id=row.get("tenant_id", "default"),
                    device_id=row["device_id"],
                    sensor_type=row["sensor_type"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    ingested_at=datetime.fromisoformat(row["ingested_at"]),
                    ingest_latency_ms=row.get("ingest_latency_ms"),
                    metrics=json.loads(row["metrics"]),
                    tags=json.loads(row.get("tags") or "{}"),
                    is_anomaly=bool(row.get("is_anomaly")),
                    anomaly_label=row.get("anomaly_label"),
                )
            )
        return events

    async def recent_anomalies(self, limit: int = 50, tenant_id: str | None = None) -> list[AnomalyScore]:
        if self._client is None:
            return []
        from telemetry.models import Severity

        tenant_filter = f"WHERE tenant_id = '{tenant_id}'" if tenant_id else ""
        query = f"""
            SELECT tenant_id, device_id, sensor_type, timestamp, score, is_anomaly,
                   severity, methods, drift_detected, message
            FROM {self._cfg.database}.anomaly_scores
            {tenant_filter}
            ORDER BY timestamp DESC LIMIT {limit}
            FORMAT JSON
        """
        resp = await self._client.post("/", params={"query": query})
        resp.raise_for_status()
        return [
            AnomalyScore(
                tenant_id=r.get("tenant_id", "default"),
                device_id=r["device_id"],
                sensor_type=r["sensor_type"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                score=r["score"],
                is_anomaly=bool(r["is_anomaly"]),
                severity=Severity(r["severity"]),
                methods=json.loads(r.get("methods") or "{}"),
                drift_detected=bool(r.get("drift_detected")),
                message=r.get("message") or "",
            )
            for r in resp.json().get("data", [])
        ]


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]