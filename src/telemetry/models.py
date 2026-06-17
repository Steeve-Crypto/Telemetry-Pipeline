"""Pydantic models for telemetry events and pipeline artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensorEvent(BaseModel):
    device_id: str
    sensor_type: str
    timestamp: datetime
    metrics: dict[str, float]
    sequence: int | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    is_anomaly: bool | None = None
    anomaly_label: str | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        raise ValueError(f"Unsupported timestamp: {value!r}")

    def metric_vector(self, fields: list[str]) -> list[float]:
        return [self.metrics.get(f, 0.0) for f in fields]


class EnrichedEvent(SensorEvent):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ingest_latency_ms: float | None = None
    validation_errors: list[str] = Field(default_factory=list)
    enriched_tags: dict[str, str] = Field(default_factory=dict)


class WindowStats(BaseModel):
    device_id: str
    sensor_type: str
    window_start: datetime
    window_end: datetime
    field: str
    count: int
    mean: float
    min: float
    max: float
    std: float


class AnomalyScore(BaseModel):
    device_id: str
    sensor_type: str
    timestamp: datetime
    score: float = Field(ge=0.0, le=1.0)
    is_anomaly: bool
    severity: Severity
    methods: dict[str, float] = Field(default_factory=dict)
    drift_detected: bool = False
    message: str = ""


class PipelineMetrics(BaseModel):
    events_ingested: int = 0
    events_valid: int = 0
    events_invalid: int = 0
    events_deduped: int = 0
    anomalies_detected: int = 0
    avg_ingest_latency_ms: float = 0.0
    p95_ingest_latency_ms: float = 0.0
    avg_processing_latency_ms: float = 0.0
    p95_processing_latency_ms: float = 0.0
    p99_processing_latency_ms: float = 0.0
    processing_rate_eps: float = 0.0
    latency_histogram: dict[str, int] = Field(default_factory=dict)

    def to_api_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")