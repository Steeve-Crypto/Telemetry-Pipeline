"""CLI for ML evaluation of anomaly detection."""

from __future__ import annotations

import argparse
from pathlib import Path

import structlog

from telemetry.anomaly.evaluator import evaluate_from_csv, write_eval_report
from telemetry.config import load_pipeline_config, load_sensors_config
from telemetry.logging_setup import configure_logging
from telemetry.prometheus_ml import MlMetricsExporter

logger = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate anomaly detection on labeled CSV data")
    parser.add_argument("--csv", required=True, help="Labeled CSV with is_anomaly column")
    parser.add_argument("--config", default="config/pipeline.yaml")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    parser.add_argument("--device-id", default="eval-device-001")
    parser.add_argument("--sensor-type", default="industrial")
    parser.add_argument("--label-col", default="is_anomaly")
    parser.add_argument("--warmup", type=int, default=None, help="Warmup events (overrides config)")
    parser.add_argument("--threshold", type=float, default=None, help="Alert threshold override")
    parser.add_argument("--report", default=None, help="JSON report output path")
    parser.add_argument(
        "--prometheus-file",
        default=None,
        help="Write OpenMetrics text file with ML quality gauges",
    )
    args = parser.parse_args()

    pipeline_config = load_pipeline_config(args.config)
    sensors_config = load_sensors_config(args.sensors)
    configure_logging(pipeline_config.logging)

    if args.warmup is not None:
        pipeline_config.eval.warmup_events = args.warmup
    if args.threshold is not None:
        pipeline_config.eval.threshold = args.threshold

    report_path = args.report or pipeline_config.eval.report_path
    report = evaluate_from_csv(
        Path(args.csv),
        pipeline_config,
        sensors_config,
        pipeline_config.eval,
        device_id=args.device_id,
        sensor_type=args.sensor_type,
        label_col=args.label_col,
    )
    write_eval_report(report, report_path)
    report.print_summary()

    if args.prometheus_file:
        exporter = MlMetricsExporter(pipeline_config.prometheus)
        exporter.set_eval_metrics(report)
        Path(args.prometheus_file).write_bytes(exporter.render()[0])
        logger.info("ml_prometheus_metrics_written", path=args.prometheus_file)


if __name__ == "__main__":
    main()