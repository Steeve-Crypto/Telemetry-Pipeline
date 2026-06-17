"""Validation and enrichment tests."""

from datetime import datetime, timezone

from telemetry.models import SensorEvent
from telemetry.validation.enricher import EventEnricher
from telemetry.validation.schema_validator import SchemaValidator


def test_schema_validation_passes(pipeline_config, sensors_config):
    validator = SchemaValidator(pipeline_config.validation, sensors_config)
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0, "pressure": 4.5, "vibration": 3.2},
    )
    enriched = validator.validate(event)
    assert validator.is_valid(enriched)
    assert enriched.validation_errors == []


def test_range_validation_fails(pipeline_config, sensors_config):
    validator = SchemaValidator(pipeline_config.validation, sensors_config)
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 200.0, "pressure": 4.5, "vibration": 3.2},
    )
    enriched = validator.validate(event)
    assert not validator.is_valid(enriched)
    assert any("range" in e for e in enriched.validation_errors)


def test_dedup_detects_duplicates(pipeline_config, sensors_config):
    validator = SchemaValidator(pipeline_config.validation, sensors_config)
    ts = datetime.now(timezone.utc)
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=ts,
        metrics={"temperature": 65.0, "pressure": 4.5, "vibration": 3.2},
    )
    first = validator.validate(event)
    second = validator.validate(event)
    assert validator.is_valid(first)
    assert any(e.startswith("dedup:") for e in second.validation_errors)


def test_enricher_adds_tags(pipeline_config, sensors_config):
    enricher = EventEnricher(sensors_config, environment="test")
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0, "pressure": 4.5, "vibration": 3.2},
    )
    validator = SchemaValidator(pipeline_config.validation, sensors_config)
    enriched = enricher.enrich(validator.validate(event))
    assert enriched.enriched_tags["environment"] == "test"
    assert "temperature_unit" in enriched.enriched_tags