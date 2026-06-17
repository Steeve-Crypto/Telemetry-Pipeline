"""Startup configuration validation."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from telemetry.alerting import AlertDispatcher
from telemetry.config import PipelineYamlConfig, SensorsYamlConfig
from telemetry.models import Severity

logger = structlog.get_logger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_config(
    pipeline_config: PipelineYamlConfig,
    sensors_config: SensorsYamlConfig,
) -> list[str]:
    errors: list[str] = []

    _validate_ingestion(pipeline_config, errors)
    _validate_validation(pipeline_config, errors)
    _validate_processing(pipeline_config, errors)
    _validate_storage(pipeline_config, errors)
    _validate_anomaly(pipeline_config, errors)
    _validate_alerting(pipeline_config, errors)
    _validate_viz(pipeline_config, errors)
    _validate_sensor_alignment(pipeline_config, sensors_config, errors)

    return errors


def _validate_ingestion(config: PipelineYamlConfig, errors: list[str]) -> None:
    transport = config.ingestion.transport
    if transport == "kafka" and not config.ingestion.kafka.bootstrap_servers:
        errors.append("ingestion.kafka.bootstrap_servers is required for kafka transport")
    if transport == "mqtt" and not config.ingestion.mqtt.host:
        errors.append("ingestion.mqtt.host is required for mqtt transport")


def _validate_validation(config: PipelineYamlConfig, errors: list[str]) -> None:
    schema_path = Path(config.validation.schema_path)
    if not schema_path.exists():
        errors.append(f"validation.schema_path not found: {schema_path}")


def _validate_processing(config: PipelineYamlConfig, errors: list[str]) -> None:
    if config.processing.window_size_seconds <= 0:
        errors.append("processing.window_size_seconds must be > 0")
    if config.processing.slide_interval_seconds <= 0:
        errors.append("processing.slide_interval_seconds must be > 0")
    if config.processing.slide_interval_seconds > config.processing.window_size_seconds:
        errors.append("processing.slide_interval_seconds cannot exceed window_size_seconds")


def _validate_storage(config: PipelineYamlConfig, errors: list[str]) -> None:
    if config.storage.backend == "timescale" and not config.storage.timescale.dsn:
        errors.append("storage.timescale.dsn is required when backend=timescale")
    if config.storage.timescale.batch_size <= 0:
        errors.append("storage.timescale.batch_size must be > 0")


def _validate_anomaly(config: PipelineYamlConfig, errors: list[str]) -> None:
    if not config.anomaly.enabled:
        return

    if not 0.0 <= config.anomaly.alert_threshold <= 1.0:
        errors.append("anomaly.alert_threshold must be between 0 and 1")

    weights = config.anomaly.ensemble_weights
    total = sum(weights.values())
    if not 0.95 <= total <= 1.05:
        errors.append(f"anomaly.ensemble_weights must sum to ~1.0 (got {total:.3f})")

    ae = config.anomaly.autoencoder
    if ae.enabled and ae.backend not in ("numpy", "torch", "onnx"):
        errors.append(f"anomaly.autoencoder.backend invalid: {ae.backend}")

    if ae.enabled and ae.backend == "onnx" and not Path(ae.model_path).exists():
        logger.warning("onnx_model_missing_at_startup", path=ae.model_path)


def _validate_alerting(config: PipelineYamlConfig, errors: list[str]) -> None:
    alerting = AlertDispatcher._apply_env_overrides(config.alerting)
    try:
        Severity(alerting.min_severity)
    except ValueError:
        errors.append(
            f"alerting.min_severity invalid: {alerting.min_severity} "
            f"(expected low|medium|high|critical)"
        )

    if alerting.enabled and not alerting.slack_webhook_url:
        errors.append("alerting.enabled=true but slack_webhook_url is empty")

    if alerting.cooldown_seconds < 0:
        errors.append("alerting.cooldown_seconds must be >= 0")


def _validate_viz(config: PipelineYamlConfig, errors: list[str]) -> None:
    if config.viz.enabled and not (1 <= config.viz.port <= 65535):
        errors.append(f"viz.port out of range: {config.viz.port}")


def _validate_sensor_alignment(
    pipeline_config: PipelineYamlConfig,
    sensors_config: SensorsYamlConfig,
    errors: list[str],
) -> None:
    schema_path = Path(pipeline_config.validation.schema_path)
    if not schema_path.exists():
        return

    with schema_path.open() as f:
        schema = json.load(f)

    schema_enums = set(
        schema.get("properties", {})
        .get("sensor_type", {})
        .get("enum", [])
    )
    configured_types = set(sensors_config.sensor_types.keys())

    missing_in_schema = configured_types - schema_enums
    if missing_in_schema:
        errors.append(
            f"sensor_types missing from JSON schema enum: {sorted(missing_in_schema)}"
        )

    orphan_schema_types = schema_enums - configured_types
    if orphan_schema_types:
        logger.warning(
            "schema_sensor_types_without_config",
            types=sorted(orphan_schema_types),
        )


async def validate_connectivity(pipeline_config: PipelineYamlConfig) -> list[str]:
    """Ping external dependencies. Returns non-fatal warnings."""
    warnings: list[str] = []

    if pipeline_config.storage.backend != "timescale":
        return warnings

    try:
        import asyncpg

        conn = await asyncpg.connect(
            pipeline_config.storage.timescale.dsn,
            timeout=5,
        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        logger.info("config_db_connectivity_ok")
    except Exception as exc:
        warnings.append(f"storage.timescale.dsn unreachable: {exc}")

    return warnings


def validate_or_raise(
    pipeline_config: PipelineYamlConfig,
    sensors_config: SensorsYamlConfig,
) -> None:
    errors = validate_config(pipeline_config, sensors_config)
    if errors:
        raise ConfigValidationError(errors)


async def validate_startup(
    pipeline_config: PipelineYamlConfig,
    sensors_config: SensorsYamlConfig,
    *,
    strict_connectivity: bool = False,
) -> None:
    validate_or_raise(pipeline_config, sensors_config)
    logger.info("config_validation_passed")

    warnings = await validate_connectivity(pipeline_config)
    for warning in warnings:
        logger.warning("config_connectivity_warning", detail=warning)

    if strict_connectivity and warnings:
        raise ConfigValidationError(warnings)