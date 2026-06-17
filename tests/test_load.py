"""Load testing for pipeline throughput."""

import pytest

from telemetry.load_test import run_direct_load


@pytest.mark.asyncio
async def test_load_1000_events(project_root):
    report = await run_direct_load(
        events=1000,
        warmup=50,
        target_eps=100.0,
        workers=1,
        batch_size=100,
        latency_sample_rate=100,
        config_path=str(project_root / "config" / "pipeline.load.yaml"),
        sensors_path=str(project_root / "config" / "sensors.yaml"),
    )

    assert report.events_consumed == 1000
    assert report.events_valid >= 990
    assert report.consumer_eps > 500, f"Throughput too low: {report.consumer_eps:.0f} eps"