"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from telemetry.config import load_pipeline_config, load_sensors_config
from telemetry.pipeline import InMemoryPipeline
from telemetry.simulator.generator import SensorSimulator


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def pipeline_config(project_root: Path):
    return load_pipeline_config(project_root / "config" / "pipeline.yaml")


@pytest.fixture
def sensors_config(project_root: Path):
    return load_sensors_config(project_root / "config" / "sensors.yaml")


@pytest.fixture
async def memory_pipeline(pipeline_config, sensors_config):
    pipeline_config.storage.backend = "memory"
    pipeline, queue = InMemoryPipeline.create(pipeline_config, sensors_config)
    await pipeline.start()
    yield pipeline, queue
    await pipeline.stop()


@pytest.fixture
def simulator(pipeline_config, sensors_config):
    return SensorSimulator(pipeline_config, sensors_config, seed=42)