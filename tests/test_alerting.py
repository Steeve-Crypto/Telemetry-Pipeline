"""Slack alerting tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from telemetry.alerting import AlertDispatcher
from telemetry.config import AlertingConfig
from telemetry.models import AnomalyScore, Severity


def _score(severity: Severity = Severity.HIGH, device: str = "industrial-device-001") -> AnomalyScore:
    return AnomalyScore(
        device_id=device,
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        score=0.85,
        is_anomaly=True,
        severity=severity,
        methods={"statistical": 0.7, "rule_based": 1.0},
        drift_detected=False,
        message="ensemble=0.85, top=rule_based=1.00",
    )


@pytest.mark.asyncio
async def test_dispatch_disabled():
    dispatcher = AlertDispatcher(AlertingConfig(enabled=False))
    assert await dispatcher.dispatch(_score()) is False


@pytest.mark.asyncio
async def test_dispatch_skips_low_severity():
    config = AlertingConfig(
        enabled=True,
        slack_webhook_url="https://hooks.slack.com/test",
        min_severity="high",
    )
    dispatcher = AlertDispatcher(config)
    assert await dispatcher.dispatch(_score(severity=Severity.MEDIUM)) is False


@pytest.mark.asyncio
async def test_dispatch_requires_webhook():
    dispatcher = AlertDispatcher(AlertingConfig(enabled=True))
    assert await dispatcher.dispatch(_score()) is False


@pytest.mark.asyncio
async def test_dispatch_sends_slack_message():
    config = AlertingConfig(
        enabled=True,
        slack_webhook_url="https://hooks.slack.com/services/TEST",
        min_severity="medium",
        cooldown_seconds=0,
    )
    dispatcher = AlertDispatcher(config)

    mock_response = httpx.Response(200, request=httpx.Request("POST", config.slack_webhook_url))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await dispatcher.dispatch(_score())

    assert result is True
    assert dispatcher.alerts_sent == 1
    mock_post.assert_called_once()
    body = mock_post.call_args.kwargs.get("content") or mock_post.call_args[1].get("content")
    payload = __import__("json").loads(body)
    assert "attachments" in payload
    assert payload["attachments"][0]["title"].startswith("Telemetry Anomaly")


@pytest.mark.asyncio
async def test_dispatch_cooldown_dedupes():
    config = AlertingConfig(
        enabled=True,
        slack_webhook_url="https://hooks.slack.com/services/TEST",
        cooldown_seconds=300,
    )
    dispatcher = AlertDispatcher(config)
    mock_response = httpx.Response(200, request=httpx.Request("POST", config.slack_webhook_url))

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        assert await dispatcher.dispatch(_score()) is True
        assert await dispatcher.dispatch(_score()) is False

    assert dispatcher.alerts_sent == 1


@pytest.mark.asyncio
async def test_env_override_enables_alerting(monkeypatch):
    monkeypatch.setenv("TELEMETRY_ALERTING_ENABLED", "true")
    monkeypatch.setenv("TELEMETRY_SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/ENV")
    dispatcher = AlertDispatcher(AlertingConfig(enabled=False))
    assert dispatcher._config.enabled is True
    assert dispatcher._config.slack_webhook_url.endswith("/ENV")