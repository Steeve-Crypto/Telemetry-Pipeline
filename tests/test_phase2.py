"""Phase 2 feature tests."""

import pytest

from telemetry.config import KafkaConfig, PipelineYamlConfig, TimescaleConfig
from telemetry.validation.config_validator import validate_config


def test_kafka_replay_mode_offset(pipeline_config, sensors_config):
    pipeline_config.ingestion.transport = "kafka"
    pipeline_config.ingestion.kafka.replay_mode = True
    assert pipeline_config.kafka_offset_reset == "earliest"


def test_kafka_latest_when_not_replay(pipeline_config):
    pipeline_config.ingestion.kafka.replay_mode = False
    pipeline_config.ingestion.kafka.auto_offset_reset = "latest"
    assert pipeline_config.kafka_offset_reset == "latest"


def test_retention_config_valid(pipeline_config, sensors_config):
    pipeline_config.storage.timescale = TimescaleConfig(
        retention_days=30,
        compression_after_days=3,
        enable_retention_policy=True,
    )
    errors = validate_config(pipeline_config, sensors_config)
    assert errors == []


@pytest.mark.asyncio
async def test_graceful_shutdown_flushes_memory(pipeline_config, sensors_config):
    from telemetry.pipeline import InMemoryPipeline
    from telemetry.simulator.generator import SensorSimulator

    pipeline, queue = InMemoryPipeline.create(pipeline_config, sensors_config)
    sim = SensorSimulator(pipeline_config, sensors_config)
    await pipeline.start()
    await queue.put(sim.generate_event("industrial-device-000"))
    await pipeline.process_event(await queue.get())
    await pipeline.stop()
    assert pipeline.metrics.events_valid >= 1


def test_json_logging_setup(pipeline_config):
    from telemetry.logging_setup import configure_logging

    pipeline_config.logging.format = "json"
    configure_logging(pipeline_config.logging)


def test_clickhouse_storage_factory(pipeline_config):
    from telemetry.storage.timescale import create_storage

    pipeline_config.storage.backend = "clickhouse"
    storage = create_storage(pipeline_config)
    assert storage.__class__.__name__ == "ClickHouseStorage"


def test_otel_tracer_disabled(pipeline_config):
    from telemetry.otel import TelemetryTracer

    pipeline_config.opentelemetry.enabled = False
    tracer = TelemetryTracer(pipeline_config.opentelemetry)
    assert not tracer.enabled


def test_kafka_manual_commit_defaults(pipeline_config):
    assert pipeline_config.ingestion.kafka.enable_auto_commit is False
    assert pipeline_config.ingestion.kafka.commit_interval_seconds == 5.0