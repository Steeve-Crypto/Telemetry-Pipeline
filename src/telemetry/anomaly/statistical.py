"""Statistical anomaly detection with EWMA and z-score."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from telemetry.config import StatisticalAnomalyConfig


@dataclass
class FieldState:
    values: deque[float] = field(default_factory=lambda: deque(maxlen=512))
    ewma: float | None = None
    ewma_var: float = 0.0


class StatisticalDetector:
    def __init__(self, config: StatisticalAnomalyConfig) -> None:
        self._config = config
        self._states: dict[str, FieldState] = {}

    def score(self, device_id: str, metrics: dict[str, float]) -> tuple[float, dict[str, float]]:
        per_field: dict[str, float] = {}
        for field_name, value in metrics.items():
            key = f"{device_id}:{field_name}"
            state = self._states.setdefault(key, FieldState())
            state.values.append(value)

            if state.ewma is None:
                state.ewma = value
                per_field[field_name] = 0.0
                continue

            alpha = self._config.ewma_alpha
            diff = value - state.ewma
            state.ewma = alpha * value + (1 - alpha) * state.ewma
            state.ewma_var = alpha * (diff**2) + (1 - alpha) * state.ewma_var

            if len(state.values) < self._config.min_samples:
                per_field[field_name] = 0.0
                continue

            std = math.sqrt(max(state.ewma_var, 1e-9))
            z = abs(value - state.ewma) / std
            per_field[field_name] = min(1.0, z / self._config.z_score_threshold)

        if not per_field:
            return 0.0, per_field
        return max(per_field.values()), per_field