"""JSON Schema validation and range checks."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import structlog

from telemetry.config import SensorsYamlConfig, ValidationConfig
from telemetry.models import EnrichedEvent, SensorEvent

logger = structlog.get_logger(__name__)


class SchemaValidator:
    def __init__(
        self,
        validation_config: ValidationConfig,
        sensors_config: SensorsYamlConfig,
    ) -> None:
        self._config = validation_config
        self._sensors = sensors_config
        schema_path = Path(validation_config.schema_path)
        with schema_path.open() as f:
            self._schema = json.load(f)
        self._validator = jsonschema.Draft202012Validator(self._schema)
        self._recent_keys: dict[str, datetime] = {}
        self._dedup_hits = 0

    def validate(self, event: SensorEvent, ingested_at: datetime | None = None) -> EnrichedEvent:
        now = ingested_at or datetime.now(timezone.utc)
        errors: list[str] = []

        payload = event.model_dump(mode="json", exclude_none=True)
        schema_errors = sorted(self._validator.iter_errors(payload), key=lambda e: e.path)
        for err in schema_errors:
            errors.append(f"schema: {err.message}")

        sensor_def = self._sensors.sensor_types.get(event.sensor_type)
        if sensor_def is None:
            errors.append(f"unknown sensor_type: {event.sensor_type}")
        else:
            for field_name, value in event.metrics.items():
                field_def = sensor_def.fields.get(field_name)
                if field_def is None:
                    errors.append(f"unknown metric field: {field_name}")
                    continue
                if value < field_def.min or value > field_def.max:
                    errors.append(
                        f"range: {field_name}={value} outside [{field_def.min}, {field_def.max}]"
                    )

        ingest_latency_ms = (now - event.timestamp).total_seconds() * 1000

        enriched = EnrichedEvent(
            **event.model_dump(),
            ingested_at=now,
            ingest_latency_ms=ingest_latency_ms,
            validation_errors=errors,
        )

        if self._is_duplicate(enriched):
            self._dedup_hits += 1
            enriched.validation_errors.append("dedup: duplicate event within window")

        return enriched

    def _is_duplicate(self, event: EnrichedEvent) -> bool:
        key = self._dedup_key(event)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._config.dedup_window_seconds)
        self._recent_keys = {k: ts for k, ts in self._recent_keys.items() if ts >= cutoff}
        if key in self._recent_keys:
            return True
        self._recent_keys[key] = event.ingested_at
        return False

    @staticmethod
    def _dedup_key(event: EnrichedEvent) -> str:
        metrics_sig = ",".join(f"{k}={v}" for k, v in sorted(event.metrics.items()))
        return f"{event.device_id}|{event.timestamp.isoformat()}|{metrics_sig}"

    @property
    def dedup_count(self) -> int:
        return self._dedup_hits

    def is_valid(self, event: EnrichedEvent) -> bool:
        non_dedup_errors = [e for e in event.validation_errors if not e.startswith("dedup:")]
        return len(non_dedup_errors) == 0