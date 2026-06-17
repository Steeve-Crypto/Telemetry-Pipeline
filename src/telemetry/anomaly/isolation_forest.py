"""Online streaming anomaly detection via river HalfSpaceTrees."""

from __future__ import annotations

from collections import deque

from river import anomaly

from telemetry.config import IsolationForestConfig, SensorsYamlConfig


class OnlineIsolationForest:
    def __init__(
        self,
        config: IsolationForestConfig,
        sensors_config: SensorsYamlConfig,
    ) -> None:
        self._config = config
        self._sensors = sensors_config
        self._models: dict[str, anomaly.HalfSpaceTrees] = {}
        self._buffers: dict[str, deque[dict[str, float]]] = {}
        self._field_order: dict[str, list[str]] = {}

    def _get_model(self, key: str, sensor_type: str) -> anomaly.HalfSpaceTrees:
        if key not in self._models:
            self._models[key] = anomaly.HalfSpaceTrees(
                n_trees=self._config.n_trees,
                seed=self._config.seed,
            )
            sensor_def = self._sensors.sensor_types.get(sensor_type)
            self._field_order[key] = list(sensor_def.fields.keys()) if sensor_def else []
            self._buffers[key] = deque(maxlen=self._config.window_size)
        return self._models[key]

    def score(
        self,
        device_id: str,
        sensor_type: str,
        metrics: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        key = f"{device_id}:{sensor_type}"
        model = self._get_model(key, sensor_type)
        fields = self._field_order[key]
        vector = {f: metrics.get(f, 0.0) for f in fields} if fields else metrics

        raw_score = model.score_one(vector)
        model.learn_one(vector)

        normalized = min(1.0, max(0.0, (raw_score + 0.5)))
        return normalized, {"isolation_forest": normalized}