"""CLI to export per-sensor-type ONNX autoencoder models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import structlog

from telemetry.anomaly.autoencoder import export_sensor_models
from telemetry.config import load_sensors_config

logger = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ONNX autoencoder models per sensor type")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    parser.add_argument("--output-dir", default="models")
    parser.add_argument("--hidden-dim", type=int, default=8)
    parser.add_argument("--manifest", default=None, help="Write models_per_sensor JSON manifest")
    args = parser.parse_args()

    sensors_config = load_sensors_config(args.sensors)
    paths = export_sensor_models(
        sensors_config,
        output_dir=args.output_dir,
        hidden_dim=args.hidden_dim,
    )

    print("\n=== ONNX Model Export ===")
    for sensor_type, path in sorted(paths.items()):
        print(f"  {sensor_type}: {path}")
    print("=========================\n")

    if args.manifest:
        manifest = {sensor: str(path) for sensor, path in paths.items()}
        Path(args.manifest).write_text(json.dumps(manifest, indent=2))
        logger.info("onnx_manifest_written", path=args.manifest)


if __name__ == "__main__":
    main()