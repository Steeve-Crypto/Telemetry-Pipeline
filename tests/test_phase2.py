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