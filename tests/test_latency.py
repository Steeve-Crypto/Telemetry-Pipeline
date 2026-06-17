"""Latency measurement tests."""

import time

import pytest

from telemetry.metrics import LatencyTracker
from telemetry.simulator.generator import SensorSimulator


def test_latency_tracker_percentiles():
    tracker = LatencyTracker()
    for v in range(1, 101):
        tracker.record(float(v))
    assert tracker.mean == pytest.approx(50.5, rel=0.01)
    assert tracker.percentile(95) >= 95
    hist = tracker.histogram([10, 50, 100])
    assert hist["<=50"] > 0


@pytest.mark.asyncio
async def test_pipeline_ingest_latency(memory_pipeline, pipeline_config, sensors_config):
    pipeline, queue = memory_pipeline
    sim = SensorSimulator(pipeline_config, sensors_config)

    for _ in range(20):
        await queue.put(sim.generate_event("industrial-device-000"))
    await queue.put(None)

    async for event in pipeline._ingestion.events():
        t0 = time.perf_counter()
        await pipeline.process_event(event)
        latency_ms = (time.perf_counter() - t0) * 1000
        assert latency_ms < 100, f"Processing latency {latency_ms:.1f}ms exceeds 100ms budget"

    assert pipeline.metrics.avg_ingest_latency_ms >= 0