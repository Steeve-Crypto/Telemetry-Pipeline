"""Alert dispatch (Slack webhook) with cooldown deduplication."""

from __future__ import annotations

import json
import os
import time

import httpx
import structlog

from telemetry.config import AlertingConfig
from telemetry.models import AnomalyScore, Severity

logger = structlog.get_logger(__name__)

SEVERITY_ORDER = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}

SEVERITY_COLORS = {
    Severity.LOW: "#36a64f",
    Severity.MEDIUM: "#daa038",
    Severity.HIGH: "#e01e5a",
    Severity.CRITICAL: "#8b0000",
}


class AlertDispatcher:
    def __init__(self, config: AlertingConfig) -> None:
        self._config = self._apply_env_overrides(config)
        self._min_severity = Severity(self._config.min_severity)
        self._last_alert: dict[str, float] = {}
        self._alerts_sent = 0

    @staticmethod
    def _apply_env_overrides(config: AlertingConfig) -> AlertingConfig:
        data = config.model_dump()
        enabled = os.environ.get("TELEMETRY_ALERTING_ENABLED")
        if enabled is not None and enabled.lower() in ("1", "true", "yes"):
            data["enabled"] = True
        elif enabled is not None and enabled.lower() in ("0", "false", "no"):
            data["enabled"] = False
        webhook = os.environ.get("TELEMETRY_SLACK_WEBHOOK_URL", "")
        if webhook:
            data["slack_webhook_url"] = webhook
        min_sev = os.environ.get("TELEMETRY_ALERTING_MIN_SEVERITY")
        if min_sev:
            data["min_severity"] = min_sev
        cooldown = os.environ.get("TELEMETRY_ALERTING_COOLDOWN_SECONDS")
        if cooldown:
            data["cooldown_seconds"] = int(cooldown)
        return AlertingConfig.model_validate(data)

    @property
    def alerts_sent(self) -> int:
        return self._alerts_sent

    def _in_cooldown(self, device_id: str) -> bool:
        last = self._last_alert.get(device_id)
        if last is None:
            return False
        return (time.monotonic() - last) < self._config.cooldown_seconds

    def _build_slack_payload(self, score: AnomalyScore) -> dict:
        color = SEVERITY_COLORS.get(score.severity, "#daa038")
        fields = [
            {"title": "Device", "value": score.device_id, "short": True},
            {"title": "Sensor Type", "value": score.sensor_type, "short": True},
            {"title": "Score", "value": f"{score.score:.2f}", "short": True},
            {"title": "Severity", "value": score.severity.value.upper(), "short": True},
        ]
        if score.drift_detected:
            fields.append({"title": "Drift", "value": "Detected", "short": True})
        if score.methods:
            top = max(score.methods.items(), key=lambda x: x[1])
            fields.append({"title": "Top Signal", "value": f"{top[0]}={top[1]:.2f}", "short": True})

        return {
            "attachments": [
                {
                    "color": color,
                    "title": f"Telemetry Anomaly — {score.device_id}",
                    "text": score.message or "Anomaly detected",
                    "fields": fields,
                    "footer": "telemetry-pipeline",
                    "ts": int(score.timestamp.timestamp()),
                }
            ]
        }

    async def dispatch(self, score: AnomalyScore) -> bool:
        if not self._config.enabled:
            return False
        if SEVERITY_ORDER[score.severity] < SEVERITY_ORDER[self._min_severity]:
            logger.debug(
                "alert_below_min_severity",
                device=score.device_id,
                severity=score.severity.value,
                min_severity=self._config.min_severity,
            )
            return False
        if not self._config.slack_webhook_url:
            logger.warning("alert_skipped_no_webhook", device=score.device_id)
            return False
        if self._in_cooldown(score.device_id):
            logger.debug("alert_cooldown", device=score.device_id)
            return False

        payload = self._build_slack_payload(score)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self._config.slack_webhook_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()

        self._last_alert[score.device_id] = time.monotonic()
        self._alerts_sent += 1
        logger.info(
            "alert_sent",
            device=score.device_id,
            severity=score.severity.value,
            score=round(score.score, 3),
        )
        return True