"""Startup configuration validation tests."""

from pathlib import Path

import pytest

from telemetry.config import (
    AlertingConfig,
    AnomalyConfig,
    PipelineYamlConfig,
    load_pipeline_config,
    load_sensors_config,
)
from telemetry.validation.config_validator import (
    ConfigValidationError,
    validate_config,
    validate_or_raise,
)


def test_valid_config_passes(pipeline_config, sensors_config):
    errors = validate_config(pipeline_config, sensors_config)
    assert errors == []


def test_invalid_ensemble_weights(pipeline_config, sensors_config):
    pipeline_config.anomaly.ensemble_weights = {
        "statistical": 0.5,
        "isolation_forest": 0.5,
        "rule_based": 0.5,
        "autoencoder": 0.5,
    }
    errors = validate_config(pipeline_config, sensors_config)
    assert any("ensemble_weights" in e for e in errors)


def test_alerting_enabled_without_webhook(pipeline_config, sensors_config):
    pipeline_config.alerting = AlertingConfig(enabled=True, slack_webhook_url="")
    errors = validate_config(pipeline_config, sensors_config)
    assert any("slack_webhook_url" in e for e in errors)


def test_missing_schema_file(pipeline_config, sensors_config):
    pipeline_config.validation.schema_path = "config/schemas/does_not_exist.json"
    errors = validate_config(pipeline_config, sensors_config)
    assert any("schema_path not found" in e for e in errors)


def test_invalid_window_config(pipeline_config, sensors_config):
    pipeline_config.processing.slide_interval_seconds = 30
    pipeline_config.processing.window_size_seconds = 10
    errors = validate_config(pipeline_config, sensors_config)
    assert any("slide_interval_seconds" in e for e in errors)


def test_validate_or_raise_raises(pipeline_config, sensors_config):
    pipeline_config.anomaly.alert_threshold = 2.0
    with pytest.raises(ConfigValidationError) as exc:
        validate_or_raise(pipeline_config, sensors_config)
    assert any("alert_threshold" in e for e in exc.value.errors)


def test_sensor_schema_alignment(project_root):
    pipeline = load_pipeline_config(project_root / "config" / "pipeline.yaml")
    sensors = load_sensors_config(project_root / "config" / "sensors.yaml")
    errors = validate_config(pipeline, sensors)
    assert errors == []