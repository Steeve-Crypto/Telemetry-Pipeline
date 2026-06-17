"""Benchmark harness tests."""

import asyncio
from pathlib import Path

import pytest

from telemetry.benchmark import run_benchmark


@pytest.mark.asyncio
async def test_benchmark_generates_report(project_root, tmp_path):
    report_path = tmp_path / "bench.json"
    report = await run_benchmark(
        events=500,
        warmup=50,
        anomaly_rate=0.02,
        report_path=str(report_path),
        config_path=str(project_root / "config" / "pipeline.yaml"),
        sensors_path=str(project_root / "config" / "sensors.yaml"),
    )

    assert report.events_total == 500
    assert report.throughput_eps > 50
    assert report.avg_processing_latency_ms < 100
    assert Path(report_path).exists()