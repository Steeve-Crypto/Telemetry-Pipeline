"""Alert dispatch (Slack webhook)."""

from __future__ import annotations

import json

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


class AlertDispatcher:
    def __init__(self, config: AlertingConfig) -> None:
        self._config = config
        self._min_severity = Severity(config.min_severity)

    async def dispatch(self, score: AnomalyScore) -> bool:
        if not self._config.enabled:
            return False
        if SEVERITY_ORDER[score.severity] < SEVERITY_ORDER[self._min_severity]:
            return False
        if not self._config.slack_webhook_url:
            logger.warning("alert_skipped_no_webhook", device=score.device_id)
            return False

        payload = {
            "text": (
                f"[{score.severity.value.upper()}] Anomaly on {score.device_id} "
                f"({score.sensor_type}): score={score.score:.2f} — {score.message}"
            )
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self._config.slack_webhook_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        logger.info("alert_sent", device=score.device_id, severity=score.severity.value)
        return True