"""Ensemble anomaly detector combining statistical, ML, and rule-based methods."""

from __future__ import annotations

import structlog

from telemetry.anomaly.autoencoder import OnlineAutoencoder
from telemetry.anomaly.drift import DriftDetector
from telemetry.anomaly.isolation_forest import OnlineIsolationForest
from telemetry.anomaly.statistical import StatisticalDetector
from telemetry.config import AnomalyConfig, SensorsYamlConfig
from telemetry.models import AnomalyScore, EnrichedEvent, Severity

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    def __init__(self, config: AnomalyConfig, sensors_config: SensorsYamlConfig) -> None:
        self._config = config
        self._sensors = sensors_config
        self._statistical = StatisticalDetector(config.statistical)
        self._isolation_forest = OnlineIsolationForest(config.isolation_forest, sensors_config)
        self._autoencoder = OnlineAutoencoder(config.autoencoder, sensors_config)
        self._drift = DriftDetector(config.drift)

    def detect(self, event: EnrichedEvent) -> AnomalyScore | None:
        if not self._config.enabled:
            return None

        methods: dict[str, float] = {}

        stat_score, stat_fields = self._statistical.score(event.device_id, event.metrics)
        methods["statistical"] = stat_score

        if_score, if_detail = self._isolation_forest.score(
            event.device_id, event.sensor_type, event.metrics
        )
        methods["isolation_forest"] = if_score
        methods.update({f"if_{k}": v for k, v in if_detail.items() if k != "isolation_forest"})

        ae_score, ae_detail = self._autoencoder.score(
            event.device_id, event.sensor_type, event.metrics
        )
        methods["autoencoder"] = ae_score
        methods.update({f"ae_{k}": v for k, v in ae_detail.items() if k != "autoencoder"})

        rule_score, rule_detail = self._rule_based_score(event)
        methods["rule_based"] = rule_score
        methods.update({f"rule_{k}": v for k, v in rule_detail.items()})

        weights = self._config.ensemble_weights
        ensemble = (
            weights.get("statistical", 0.0) * stat_score
            + weights.get("isolation_forest", 0.0) * if_score
            + weights.get("autoencoder", 0.0) * ae_score
            + weights.get("rule_based", 0.0) * rule_score
        )
        ensemble = min(1.0, max(0.0, ensemble))

        drift_detected = False
        if event.metrics:
            primary_value = next(iter(event.metrics.values()))
            drift_detected = self._drift.update(event.device_id, primary_value)

        rule_critical = rule_score >= 1.0
        is_anomaly = ensemble >= self._config.alert_threshold or rule_critical
        severity = self._severity(max(ensemble, rule_score), drift_detected)

        if is_anomaly or drift_detected or rule_score >= 0.6:
            message_parts = []
            if is_anomaly:
                top = max(
                    [(k, v) for k, v in methods.items() if k in weights],
                    key=lambda x: x[1],
                )
                message_parts.append(f"ensemble={ensemble:.2f}, top={top[0]}={top[1]:.2f}")
            if drift_detected:
                message_parts.append("concept drift detected")
            return AnomalyScore(
                device_id=event.device_id,
                sensor_type=event.sensor_type,
                timestamp=event.timestamp,
                score=ensemble,
                is_anomaly=is_anomaly,
                severity=severity,
                methods=methods,
                drift_detected=drift_detected,
                message="; ".join(message_parts),
            )
        return None

    def _rule_based_score(self, event: EnrichedEvent) -> tuple[float, dict[str, float]]:
        rules = self._sensors.rules
        per_field: dict[str, float] = {}
        for field_name, value in event.metrics.items():
            field_rules = rules.get(field_name, {})
            score = 0.0
            if "critical_above" in field_rules and value >= field_rules["critical_above"]:
                score = 1.0
            elif "warn_above" in field_rules and value >= field_rules["warn_above"]:
                score = 0.6
            if "critical_below" in field_rules and value <= field_rules["critical_below"]:
                score = max(score, 1.0)
            elif "warn_below" in field_rules and value <= field_rules["warn_below"]:
                score = max(score, 0.6)
            per_field[field_name] = score
        if not per_field:
            return 0.0, per_field
        return max(per_field.values()), per_field

    @staticmethod
    def _severity(score: float, drift: bool) -> Severity:
        if drift and score >= 0.5:
            return Severity.CRITICAL
        if score >= 0.9:
            return Severity.CRITICAL
        if score >= 0.75:
            return Severity.HIGH
        if score >= 0.65:
            return Severity.MEDIUM
        return Severity.LOW