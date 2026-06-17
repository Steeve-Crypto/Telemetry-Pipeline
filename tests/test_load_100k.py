"""Load test harness tests (100k+ eps target tooling)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from telemetry.config import load_pipeline_config
from telemetry.load_test import (
    FastEventGenerator,
    LoadTestReport,
    apply_load_profile,
    run_direct_load,
    run_load_test,
)
from telemetry.storage.timescale import MemoryStorage


def test_apply_load_profile_strips_expensive_features(pipeline_config):
    apply_load_profile(pipeline_config)
    assert pipeline_config.storage.backend == "memory"
    assert pipeline_config.storage.memory.count_only is True
    assert pipeline_config.anomaly.enabled is False
    assert pipeline_config.prometheus.enabled is False
    assert pipeline_config.validation.dedup_window_seconds == 0


def test_fast_event_generator(project_root, sensors_config):
    gen = FastEventGenerator(sensors_config, device_count=5)
    events = gen.generate(100)
    assert len(events) == 100
    assert events[0].sensor_type == "industrial"
    assert events[0].tags["source"] == "load-test"


def test_memory_storage_count_only():
    storage = MemoryStorage()
    storage._cfg.count_only = True

    class _Event:
        tenant_id = "default"

    import asyncio

    asyncio.run(storage.write_event(_Event()))  # type: ignore[arg-type]
    assert storage.event_count == 1
    assert storage.events == []


@pytest.mark.asyncio
async def test_direct_load_smoke(project_root, tmp_path):
    config_path = project_root / "config" / "pipeline.load.yaml"
    sensors_path = project_root / "config" / "sensors.yaml"
    report_path = tmp_path / "load.json"

    report = await run_direct_load(
        events=2000,
        warmup=100,
        target_eps=500.0,
        workers=1,
        batch_size=500,
        latency_sample_rate=500,
        config_path=str(config_path),
        sensors_path=str(sensors_path),
    )

    assert report.mode == "direct"
    assert report.events_consumed == 2000
    assert report.events_valid >= 1900
    assert report.consumer_eps > 500


@pytest.mark.asyncio
async def test_load_test_report_written(project_root, tmp_path):
    report_path = tmp_path / "report.json"
    report = await run_load_test(
        mode="direct",
        events=2000,
        duration_seconds=10.0,
        warmup=100,
        target_eps=500.0,
        workers=1,
        batch_size=200,
        latency_sample_rate=200,
        report_path=str(report_path),
        config_path=str(project_root / "config" / "pipeline.load.yaml"),
        sensors_path=str(project_root / "config" / "sensors.yaml"),
    )

    assert isinstance(report, LoadTestReport)
    data = json.loads(report_path.read_text())
    assert data["events_consumed"] == 2000


def test_load_config_in_pipeline_yaml(project_root):
    cfg = load_pipeline_config(project_root / "config" / "pipeline.load.yaml")
    assert cfg.load_test.target_eps == 100_000
    assert cfg.storage.memory.count_only is True


@pytest.mark.asyncio
async def test_direct_load_multiprocess(project_root):
    report = await run_direct_load(
        events=20_000,
        warmup=0,
        target_eps=20_000.0,
        workers=4,
        batch_size=1000,
        latency_sample_rate=1000,
        config_path=str(project_root / "config" / "pipeline.load.yaml"),
        sensors_path=str(project_root / "config" / "sensors.yaml"),
    )
    assert report.events_consumed == 20_000
    assert report.events_valid >= 19_900
    assert report.consumer_eps > 5_000


@pytest.mark.slow
@pytest.mark.skipif(os.getenv("RUN_SLOW_LOAD") != "1", reason="set RUN_SLOW_LOAD=1 to run")
@pytest.mark.asyncio
async def test_direct_load_100k_events(project_root):
    report = await run_direct_load(
        events=100_000,
        warmup=0,
        target_eps=50_000.0,
        workers=8,
        batch_size=1000,
        latency_sample_rate=2000,
        config_path=str(project_root / "config" / "pipeline.load.yaml"),
        sensors_path=str(project_root / "config" / "sensors.yaml"),
    )
    assert report.events_consumed == 100_000
    assert report.consumer_eps > 20_000