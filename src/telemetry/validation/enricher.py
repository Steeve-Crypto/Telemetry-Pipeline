"""Event enrichment with metadata and derived fields."""

from __future__ import annotations

from datetime import datetime, timezone

from telemetry.config import SensorsYamlConfig
from telemetry.models import EnrichedEvent


class EventEnricher:
    def __init__(self, sensors_config: SensorsYamlConfig, environment: str = "local") -> None:
        self._sensors = sensors_config
        self._environment = environment

    def enrich(self, event: EnrichedEvent) -> EnrichedEvent:
        sensor_def = self._sensors.sensor_types.get(event.sensor_type)
        tags = {
            "environment": self._environment,
            "sensor_type": event.sensor_type,
            "ingest_hour": str(event.ingested_at.hour),
        }
        if sensor_def:
            tags["sensor_description"] = sensor_def.description

        for field_name, value in event.metrics.items():
            field_def = sensor_def.fields.get(field_name) if sensor_def else None
            if field_def:
                tags[f"{field_name}_unit"] = field_def.unit
                deviation = abs(value - field_def.baseline) / max(field_def.noise_std, 1e-6)
                tags[f"{field_name}_deviation_sigma"] = f"{deviation:.2f}"

        event.enriched_tags = {**event.tags, **tags}
        event.tags = event.enriched_tags
        return event

    @staticmethod
    def compute_ingest_latency(event: EnrichedEvent) -> float:
        now = datetime.now(timezone.utc)
        return (now - event.timestamp).total_seconds() * 1000