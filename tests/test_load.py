"""Load testing for pipeline throughput."""

import asyncio
import time

import pytest

from telemetry.simulator.generator import SensorSimulator


@pytest.mark.asyncio
async def test_load_1000_events(memory_pipeline, pipeline_config, sensors_config):
    pipeline, queue = memory_pipeline
    sim = SensorSimulator(pipeline_config, sensors_config, seed=99)

    start = time.perf_counter()
    await sim.run_to_queue(queue, count=1000)
    await queue.put(None)

    count = 0
    async for event in pipeline._ingestion.events():
        await pipeline.process_event(event)
        count += 1

    elapsed = time.perf_counter() - start
    eps = count / max(elapsed, 1e-6)

    assert count == 1000
    assert pipeline.metrics.events_valid >= 980
    assert eps > 100, f"Throughput too low: {eps:.0f} eps"