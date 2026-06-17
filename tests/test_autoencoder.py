"""Autoencoder anomaly detection tests."""

from datetime import datetime, timezone

from telemetry.anomaly.autoencoder import OnlineAutoencoder
from telemetry.config import AutoencoderConfig
from telemetry.models import EnrichedEvent


def test_autoencoder_learns_normal_pattern(sensors_config):
    config = AutoencoderConfig(enabled=True, min_samples=10, error_threshold=0.5)
    ae = OnlineAutoencoder(config, sensors_config)

    for i in range(50):
        score, _ = ae.score(
            "industrial-device-000",
            "industrial",
            {"temperature": 65.0 + i * 0.01, "pressure": 4.5, "vibration": 3.2},
        )

    normal_score, normal_details = ae.score(
        "industrial-device-000",
        "industrial",
        {"temperature": 65.5, "pressure": 4.5, "vibration": 3.2},
    )
    anomaly_score, anomaly_details = ae.score(
        "industrial-device-000",
        "industrial",
        {"temperature": 115.0, "pressure": 4.5, "vibration": 3.2},
    )

    assert anomaly_details.get("recon_mse", 0) > normal_details.get("recon_mse", 0)
    assert anomaly_score >= normal_score


def test_autoencoder_in_ensemble(pipeline_config, sensors_config):
    from telemetry.anomaly.detector import AnomalyDetector
    from telemetry.validation.schema_validator import SchemaValidator

    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    validator = SchemaValidator(pipeline_config.validation, sensors_config)

    normal = EnrichedEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0, "pressure": 4.5, "vibration": 3.2},
    )
    for _ in range(40):
        detector.detect(normal)

    result = detector.detect(normal)
    assert result is None or "autoencoder" in result.methods