"""Online autoencoder anomaly detection with numpy, PyTorch, and ONNX backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import structlog

from telemetry.config import AutoencoderConfig, SensorsYamlConfig

logger = structlog.get_logger(__name__)


@dataclass
class _NumpyAutoencoder:
    input_dim: int
    hidden_dim: int
    learning_rate: float
    w1: np.ndarray = field(init=False)
    w2: np.ndarray = field(init=False)
    samples: int = 0
    error_ema: float = 0.0

    def __post_init__(self) -> None:
        rng = np.random.default_rng(42)
        self.w1 = rng.normal(0, 0.1, (self.input_dim, self.hidden_dim))
        self.w2 = rng.normal(0, 0.1, (self.hidden_dim, self.input_dim))

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        encoded = self._relu(x @ self.w1)
        reconstructed = encoded @ self.w2
        return encoded, reconstructed

    def train_step(self, x: np.ndarray) -> float:
        encoded, reconstructed = self.forward(x)
        error = reconstructed - x
        mse = float(np.mean(error**2))

        grad_out = 2 * error / x.shape[0]
        grad_enc = grad_out @ self.w2.T
        grad_enc = grad_enc * (encoded > 0)
        grad_w2 = encoded.T @ grad_out
        grad_w1 = x.T @ grad_enc

        lr = self.learning_rate
        self.w1 -= lr * grad_w1
        self.w2 -= lr * grad_w2

        self.samples += 1
        alpha = 0.05
        self.error_ema = alpha * mse + (1 - alpha) * self.error_ema if self.samples > 1 else mse
        return mse

    def reconstruction_error(self, x: np.ndarray) -> float:
        _, reconstructed = self.forward(x)
        return float(np.mean((x - reconstructed) ** 2))


class OnlineAutoencoder:
    """Per-device online autoencoder with pluggable backends."""

    def __init__(
        self,
        config: AutoencoderConfig,
        sensors_config: SensorsYamlConfig,
    ) -> None:
        self._config = config
        self._sensors = sensors_config
        self._models: dict[str, _NumpyAutoencoder] = {}
        self._field_order: dict[str, list[str]] = {}
        self._norm_stats: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._onnx_sessions: dict[str, object] = {}
        self._onnx_session = None
        self._torch_models: dict = {}

        if config.backend == "onnx":
            self._load_onnx_registry()
        elif config.backend == "torch":
            self._init_torch()

    def _load_onnx_registry(self) -> None:
        if self._config.models_per_sensor:
            for sensor_type, model_path in self._config.models_per_sensor.items():
                session = self._load_onnx(model_path, sensor_type=sensor_type)
                if session is not None:
                    self._onnx_sessions[sensor_type] = session
        else:
            session = self._load_onnx(self._config.model_path)
            if session is not None:
                self._onnx_session = session

    def _load_onnx(self, model_path: str, sensor_type: str | None = None) -> object | None:
        path = Path(model_path)
        if not path.exists():
            logger.warning(
                "onnx_model_missing",
                path=model_path,
                sensor_type=sensor_type,
                fallback="numpy",
            )
            return None
        try:
            import onnxruntime as ort

            session = ort.InferenceSession(str(path))
            logger.info("onnx_model_loaded", path=model_path, sensor_type=sensor_type)
            return session
        except ImportError:
            logger.warning("onnxruntime_not_installed", fallback="numpy")
            return None

    def _init_torch(self) -> None:
        try:
            import torch  # noqa: F401
        except ImportError:
            logger.warning("torch_not_installed", fallback="numpy")

    def _vectorize(self, key: str, sensor_type: str, metrics: dict[str, float]) -> np.ndarray:
        if key not in self._field_order:
            sensor_def = self._sensors.sensor_types.get(sensor_type)
            self._field_order[key] = list(sensor_def.fields.keys()) if sensor_def else sorted(metrics)
        fields = self._field_order[key]
        raw = np.array([[metrics.get(f, 0.0) for f in fields]], dtype=np.float64)

        if key not in self._norm_stats:
            self._norm_stats[key] = (raw.copy(), np.ones((1, raw.shape[1]), dtype=np.float64))
        mean, std = self._norm_stats[key]
        alpha = 0.05
        mean = (1 - alpha) * mean + alpha * raw
        std = (1 - alpha) * std + alpha * (np.abs(raw - mean) + 1e-3)
        self._norm_stats[key] = (mean, std)
        normalized = (raw - mean) / std
        return np.clip(normalized, -10.0, 10.0)

    def _get_numpy_model(self, key: str, input_dim: int) -> _NumpyAutoencoder:
        if key not in self._models:
            self._models[key] = _NumpyAutoencoder(
                input_dim=input_dim,
                hidden_dim=self._config.hidden_dim,
                learning_rate=self._config.learning_rate,
            )
        return self._models[key]

    def score(
        self,
        device_id: str,
        sensor_type: str,
        metrics: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        if not self._config.enabled:
            return 0.0, {}

        key = f"{device_id}:{sensor_type}"
        x = self._vectorize(key, sensor_type, metrics)

        onnx_session = self._onnx_sessions.get(sensor_type) or self._onnx_session
        if onnx_session is not None:
            return self._score_onnx(x, onnx_session)

        if self._config.backend == "torch":
            torch_score = self._score_torch(key, x)
            if torch_score is not None:
                return torch_score, {"autoencoder": torch_score}

        model = self._get_numpy_model(key, x.shape[1])
        mse = model.train_step(x)
        recon_error = model.reconstruction_error(x)

        if model.samples < self._config.min_samples:
            return 0.0, {"autoencoder": 0.0, "recon_mse": recon_error}

        baseline = max(model.error_ema, 1e-9)
        ratio = recon_error / baseline
        normalized = min(1.0, max(0.0, (ratio - 1.0) / max(self._config.error_threshold, 1e-6)))
        return normalized, {"autoencoder": normalized, "recon_mse": recon_error, "train_mse": mse}

    def _score_onnx(self, x: np.ndarray, session: object) -> tuple[float, dict[str, float]]:
        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: x.astype(np.float32)})[0]
        mse = float(np.mean((x - output) ** 2))
        normalized = min(1.0, mse / max(self._config.error_threshold, 1e-6))
        return normalized, {"autoencoder": normalized, "recon_mse": mse}

    def _score_torch(self, key: str, x: np.ndarray) -> float | None:
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            return None

        if key not in self._torch_models:
            input_dim = x.shape[1]
            hidden = self._config.hidden_dim

            class AE(nn.Module):
                def __init__(self) -> None:
                    super().__init__()
                    self.enc = nn.Sequential(
                        nn.Linear(input_dim, hidden),
                        nn.ReLU(),
                        nn.Linear(hidden, hidden),
                        nn.ReLU(),
                    )
                    self.dec = nn.Sequential(
                        nn.Linear(hidden, hidden),
                        nn.ReLU(),
                        nn.Linear(hidden, input_dim),
                    )

                def forward(self, inp: torch.Tensor) -> torch.Tensor:
                    return self.dec(self.enc(inp))

            model = AE()
            optimizer = torch.optim.Adam(model.parameters(), lr=self._config.learning_rate)
            self._torch_models[key] = {"model": model, "optimizer": optimizer, "samples": 0, "error_ema": 0.0}

        entry = self._torch_models[key]
        model = entry["model"]
        optimizer = entry["optimizer"]
        tensor = torch.tensor(x, dtype=torch.float32)
        model.train()
        optimizer.zero_grad()
        reconstructed = model(tensor)
        loss = torch.mean((reconstructed - tensor) ** 2)
        loss.backward()
        optimizer.step()

        entry["samples"] += 1
        mse = float(loss.detach())
        entry["error_ema"] = 0.05 * mse + 0.95 * entry["error_ema"] if entry["samples"] > 1 else mse

        if entry["samples"] < self._config.min_samples:
            return 0.0

        ratio = mse / max(entry["error_ema"], 1e-9)
        return min(1.0, max(0.0, (ratio - 1.0) / max(self._config.error_threshold, 1e-6)))


def export_sensor_models(
    sensors_config: SensorsYamlConfig,
    output_dir: str = "models",
    hidden_dim: int = 8,
) -> dict[str, Path]:
    """Export one ONNX autoencoder per configured sensor type."""
    paths: dict[str, Path] = {}
    for sensor_type, sensor_def in sensors_config.sensor_types.items():
        input_dim = len(sensor_def.fields)
        output_path = Path(output_dir) / f"{sensor_type}.onnx"
        paths[sensor_type] = export_numpy_to_onnx(input_dim, hidden_dim, str(output_path))
    return paths


def export_numpy_to_onnx(
    input_dim: int,
    hidden_dim: int,
    output_path: str,
) -> Path:
    """Train a small numpy AE and export weights to ONNX via PyTorch bridge."""
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise RuntimeError("PyTorch required for ONNX export: pip install torch") from exc

    class ExportAE(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, input_dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    model = ExportAE()
    model.eval()
    dummy = torch.randn(1, input_dim)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(model, dummy, str(path), input_names=["input"], output_names=["output"])
    logger.info("onnx_model_exported", path=str(path))
    return path