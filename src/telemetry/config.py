"""Configuration loader for pipeline YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class MqttConfig(BaseModel):
    host: str = "localhost"
    port: int = 1883
    topic: str = "sensors/+/telemetry"
    qos: int = 1


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "localhost:9092"
    topic: str = "telemetry.events"
    group_id: str = "telemetry-pipeline"
    auto_offset_reset: str = "latest"


class WebSocketConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8765


class IngestionConfig(BaseModel):
    transport: Literal["mqtt", "kafka", "websocket"] = "websocket"
    mqtt: MqttConfig = Field(default_factory=MqttConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)


class ValidationConfig(BaseModel):
    schema_path: str = "config/schemas/sensor_event.json"
    dedup_window_seconds: int = 5
    drop_invalid: bool = True


class ProcessingConfig(BaseModel):
    window_size_seconds: int = 10
    slide_interval_seconds: int = 2
    aggregations: list[str] = Field(default_factory=lambda: ["mean", "min", "max", "std", "count"])


class TimescaleConfig(BaseModel):
    dsn: str = "postgresql://telemetry:telemetry@localhost:5432/telemetry"
    batch_size: int = 100
    flush_interval_seconds: float = 1.0


class StorageConfig(BaseModel):
    backend: Literal["timescale", "memory"] = "timescale"
    timescale: TimescaleConfig = Field(default_factory=TimescaleConfig)


class StatisticalAnomalyConfig(BaseModel):
    z_score_threshold: float = 3.5
    ewma_alpha: float = 0.1
    min_samples: int = 20


class IsolationForestConfig(BaseModel):
    n_trees: int = 10
    window_size: int = 256
    seed: int = 42


class DriftConfig(BaseModel):
    enabled: bool = True
    adwin_delta: float = 0.002
    check_interval_seconds: int = 30


class AnomalyConfig(BaseModel):
    enabled: bool = True
    ensemble_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "statistical": 0.35,
            "isolation_forest": 0.45,
            "rule_based": 0.20,
        }
    )
    statistical: StatisticalAnomalyConfig = Field(default_factory=StatisticalAnomalyConfig)
    isolation_forest: IsolationForestConfig = Field(default_factory=IsolationForestConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)
    alert_threshold: float = 0.65


class AlertingConfig(BaseModel):
    enabled: bool = False
    slack_webhook_url: str = ""
    min_severity: str = "medium"


class SimulatorConfig(BaseModel):
    devices: int = 5
    interval_ms: int = 100
    anomaly_rate: float = 0.02
    burst_mode: bool = False


class MetricsConfig(BaseModel):
    latency_histogram_buckets_ms: list[int] = Field(
        default_factory=lambda: [1, 5, 10, 25, 50, 100, 250, 500, 1000]
    )


class PipelineYamlConfig(BaseModel):
    pipeline: dict[str, str] = Field(default_factory=dict)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    alerting: AlertingConfig = Field(default_factory=AlertingConfig)
    simulator: SimulatorConfig = Field(default_factory=SimulatorConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)


class SensorFieldDef(BaseModel):
    unit: str
    min: float
    max: float
    baseline: float
    noise_std: float


class AnomalyPattern(BaseModel):
    type: str
    field: str
    multiplier: float | None = None
    slope: float | None = None


class SensorTypeDef(BaseModel):
    description: str
    fields: dict[str, SensorFieldDef]
    anomaly_patterns: list[AnomalyPattern] = Field(default_factory=list)


class SensorsYamlConfig(BaseModel):
    sensor_types: dict[str, SensorTypeDef]
    rules: dict[str, dict[str, float]] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = {"env_prefix": "TELEMETRY_"}

    config_dir: Path = Path("config")
    pipeline_config_path: Path = Path("config/pipeline.yaml")
    sensors_config_path: Path = Path("config/sensors.yaml")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_pipeline_config(path: Path | None = None) -> PipelineYamlConfig:
    settings = Settings()
    config_path = path or settings.pipeline_config_path
    data = load_yaml(config_path)
    return PipelineYamlConfig.model_validate(data)


def load_sensors_config(path: Path | None = None) -> SensorsYamlConfig:
    settings = Settings()
    config_path = path or settings.sensors_config_path
    data = load_yaml(config_path)
    return SensorsYamlConfig.model_validate(data)