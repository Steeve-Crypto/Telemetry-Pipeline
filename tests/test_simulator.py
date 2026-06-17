"""Simulator and replay tests."""

from pathlib import Path

from telemetry.simulator.generator import SensorSimulator
from telemetry.simulator.replay import DatasetReplay


def test_simulator_generates_valid_events(simulator):
    event = simulator.generate_event("industrial-device-000")
    assert event.device_id == "industrial-device-000"
    assert event.sensor_type == "industrial"
    assert "temperature" in event.metrics
    assert event.sequence == 0


def test_simulator_injects_anomalies(simulator):
    event = simulator.generate_event("industrial-device-000", inject_anomaly=True)
    assert event.is_anomaly is True
    assert event.anomaly_label is not None


def test_replay_loads_nab_sample(project_root):
    csv_path = project_root / "data" / "sample" / "nab_sample.csv"
    replay = DatasetReplay(csv_path, value_cols=["value"])
    events = replay.to_events()
    assert len(events) == 500
    labeled = [e for e in events if e.is_anomaly]
    assert len(labeled) == 3


def test_replay_loads_pump_sample(project_root):
    csv_path = project_root / "data" / "sample" / "pump_sample.csv"
    replay = DatasetReplay(
        csv_path,
        value_cols=["temperature", "pressure", "vibration"],
    )
    events = replay.to_events()
    assert len(events) == 300
    assert all("temperature" in e.metrics for e in events)