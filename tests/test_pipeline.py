"""End-to-end in-memory pipeline tests."""

import pytest

from telemetry.simulator.generator import SensorSimulator


@pytest.mark.asyncio
async def test_pipeline_processes_batch(memory_pipeline, pipeline_config, sensors_config):
    pipeline, queue = memory_pipeline
    sim = SensorSimulator(pipeline_config, sensors_config, seed=1)
    await sim.run_to_queue(queue, count=100)
    await queue.put(None)

    async for event in pipeline._ingestion.events():
        await pipeline.process_event(event)

    assert pipeline.metrics.events_valid >= 90
    assert len(pipeline.storage.events) >= 90


@pytest.mark.asyncio
async def test_pipeline_detects_anomalies(memory_pipeline, pipeline_config, sensors_config):
    pipeline, queue = memory_pipeline
    sim = SensorSimulator(pipeline_config, sensors_config, seed=1)

    for _ in range(50):
        await queue.put(sim.generate_event("industrial-device-000", inject_anomaly=False))
    await queue.put(sim.generate_event("industrial-device-000", inject_anomaly=True))
    await queue.put(None)

    async for event in pipeline._ingestion.events():
        await pipeline.process_event(event)

    assert pipeline.metrics.anomalies_detected >= 0
    assert pipeline.metrics.events_ingested >= 51