"""Concept drift detection using ADWIN."""

from __future__ import annotations

import time

from river import drift

from telemetry.config import DriftConfig


class DriftDetector:
    def __init__(self, config: DriftConfig) -> None:
        self._config = config
        self._detectors: dict[str, drift.ADWIN] = {}
        self._last_check: dict[str, float] = {}
        self._drift_flags: dict[str, bool] = {}

    def update(self, device_id: str, value: float) -> bool:
        if not self._config.enabled:
            return False

        detector = self._detectors.setdefault(device_id, drift.ADWIN(delta=self._config.adwin_delta))
        detector.update(value)

        now = time.monotonic()
        last = self._last_check.get(device_id, 0.0)
        if now - last < self._config.check_interval_seconds:
            return self._drift_flags.get(device_id, False)

        self._last_check[device_id] = now
        drifted = detector.drift_detected
        self._drift_flags[device_id] = drifted
        return drifted

    def is_drift(self, device_id: str) -> bool:
        return self._drift_flags.get(device_id, False)