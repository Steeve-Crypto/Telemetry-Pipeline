"""Anomaly detection tests."""

from datetime import datetime, timezone

from telemetry.anomaly.detector import AnomalyDetector
from telemetry.anomaly.drift import DriftDetector
from telemetry.anomaly.statistical import StatisticalDetector
from telemetry.config import DriftConfig, StatisticalAnomalyConfig
from telemetry.models import EnrichedEvent, SensorEvent
from telemetry.validation.schema_validator import SchemaValidator


def test_statistical_detects_spike():
    det = StatisticalDetector(StatisticalAnomalyConfig(min_samples=5, z_score_threshold=3.0))
    for v in [65, 66, 64, 65, 66, 65, 64]:
        score, _ = det.score("dev1", {"temperature": float(v)})
    score, fields = det.score("dev1", {"temperature": 150.0})
    assert score > 0.5
    assert fields["temperature"] > 0.5


def test_rule_based_critical_temperature(pipeline_config, sensors_config):
    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    event = EnrichedEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 115.0, "pressure": 4.5, "vibration": 3.2},
    )
    result = detector.detect(event)
    assert result is not None
    assert result.is_anomaly
    assert result.methods["rule_based"] >= 0.6


def test_ensemble_detects_injected_anomaly(pipeline_config, sensors_config, simulator):
    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    validator = SchemaValidator(pipeline_config.validation, sensors_config)
    normal = simulator.generate_event("industrial-device-000", inject_anomaly=False)
    anomalous = simulator.generate_event("industrial-device-000", inject_anomaly=False)
    anomalous.metrics["temperature"] = 115.0

    for _ in range(30):
        e = validator.validate(normal)
        detector.detect(EnrichedEvent(**e.model_dump()))

    anom_enriched = EnrichedEvent(**validator.validate(anomalous).model_dump())
    result = detector.detect(anom_enriched)
    assert result is not None
    assert result.is_anomaly


def test_drift_detector_flags_shift():
    drift = DriftDetector(DriftConfig(enabled=True, adwin_delta=0.01, check_interval_seconds=0))
    for v in [1.0] * 100:
        drift.update("dev1", v)
    drifted = False
    for v in [10.0] * 100:
        if drift.update("dev1", v):
            drifted = True
            break
    assert drifted or drift.is_drift("dev1")