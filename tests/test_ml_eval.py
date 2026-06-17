"""ML evaluation and ONNX per-sensor tests."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from telemetry.anomaly.autoencoder import OnlineAutoencoder
from telemetry.anomaly.detector import AnomalyDetector
from telemetry.anomaly.evaluator import ConfusionCounts, evaluate_detector
from telemetry.config import AutoencoderConfig, EvalConfig
from telemetry.models import EnrichedEvent, SensorEvent
from telemetry.prometheus_ml import MlMetricsExporter
from telemetry.simulator.generator import SensorSimulator


def _labeled_events(sim: SensorSimulator, normal: int = 80, anomalous: int = 20) -> list[SensorEvent]:
    events: list[SensorEvent] = []
    for _ in range(normal):
        e = sim.generate_event("industrial-device-001", inject_anomaly=False)
        e.is_anomaly = False
        events.append(e)
    for _ in range(anomalous):
        e = sim.generate_event("industrial-device-001", inject_anomaly=True)
        e.is_anomaly = True
        events.append(e)
    return events


def test_confusion_metrics():
    counts = ConfusionCounts(tp=8, fp=2, tn=70, fn=5)
    assert counts.precision == pytest.approx(0.8)
    assert counts.recall == pytest.approx(8 / 13)
    assert counts.f1 > 0
    assert counts.accuracy == pytest.approx(78 / 85)


def test_evaluate_detector_on_synthetic_labels(pipeline_config, sensors_config, simulator):
    pipeline_config.anomaly.autoencoder.min_samples = 10
    pipeline_config.anomaly.statistical.min_samples = 5
    eval_config = EvalConfig(warmup_events=30, threshold=0.5)

    events = _labeled_events(simulator)
    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    report = evaluate_detector(
        events,
        detector,
        pipeline_config.anomaly,
        eval_config,
        dataset_name="synthetic",
    )

    assert report.labeled_events == 100
    assert report.confusion.tp + report.confusion.fn >= 1
    assert "statistical" in report.per_method
    assert "autoencoder" in report.per_method
    assert len(report.threshold_sweep) == len(eval_config.threshold_sweep)
    assert report.f1 >= 0.0


def test_evaluate_from_pump_csv(pipeline_config, sensors_config, project_root: Path):
    csv_path = project_root / "data" / "sample" / "pump_sample.csv"
    from telemetry.anomaly.evaluator import evaluate_from_csv

    pipeline_config.eval.warmup_events = 20
    report = evaluate_from_csv(
        csv_path,
        pipeline_config,
        sensors_config,
        pipeline_config.eval,
        sensor_type="industrial",
    )
    assert report.total_events == 300
    assert report.labeled_events == 300


def test_ml_prometheus_exporter(pipeline_config, sensors_config, simulator):
    pipeline_config.anomaly.autoencoder.min_samples = 10
    eval_config = EvalConfig(warmup_events=20, threshold=0.5)
    events = _labeled_events(simulator, normal=60, anomalous=15)
    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    report = evaluate_detector(events, detector, pipeline_config.anomaly, eval_config)

    exporter = MlMetricsExporter(pipeline_config.prometheus)
    exporter.set_eval_metrics(report)
    body, _ = exporter.render()
    text = body.decode()
    assert "telemetry_ml_f1" in text
    assert 'method="ensemble"' in text


def test_onnx_models_per_sensor_config(pipeline_config, sensors_config):
    config = AutoencoderConfig(
        enabled=True,
        backend="onnx",
        models_per_sensor={
            "industrial": "models/industrial.onnx",
            "vehicle": "models/vehicle.onnx",
        },
        min_samples=5,
    )
    ae = OnlineAutoencoder(config, sensors_config)
    assert config.backend == "onnx"
    assert "industrial" in config.models_per_sensor

    for _ in range(15):
        ae.score("dev-1", "industrial", {"temperature": 65.0, "pressure": 4.5, "vibration": 3.2})

    score, _ = ae.score(
        "dev-1",
        "industrial",
        {"temperature": 120.0, "pressure": 4.5, "vibration": 3.2},
    )
    assert score >= 0.0


@pytest.mark.skipif(
    not Path("models/industrial.onnx").exists(),
    reason="Run telemetry-export-onnx to generate models",
)
def test_onnx_per_sensor_scoring_when_models_exist(pipeline_config, sensors_config):
    config = AutoencoderConfig(
        enabled=True,
        backend="onnx",
        models_per_sensor={"industrial": "models/industrial.onnx"},
        min_samples=5,
    )
    ae = OnlineAutoencoder(config, sensors_config)
    assert "industrial" in ae._onnx_sessions